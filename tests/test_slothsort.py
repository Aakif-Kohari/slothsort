import json
import os
import time

from slothsort import mover, planner, rules
from slothsort.llm import OllamaClient


def touch(path, age=3600):
    path.write_text("x")
    t = time.time() - age
    os.utime(path, (t, t))
    return path


def fake_classify(name, allowed, snippet):
    return ("Documents/Receipts", "looks like an invoice") if "invoice" in name else None


def test_extension_rules():
    assert rules.by_extension(rules.Path("a.PNG")) == "Images"
    assert rules.by_extension(rules.Path("a.tar.gz")) == "Archives"
    assert rules.by_extension(rules.Path("a.pdf")) is None


def test_plan_uses_rules_then_model_then_fallback(tmp_path):
    touch(tmp_path / "pic.jpg")
    touch(tmp_path / "invoice_oct.pdf")
    touch(tmp_path / "mystery.pdf")
    plan = {m.src.name: m for m in planner.build_plan(tmp_path, classify=fake_classify, min_age=0)}
    assert plan["pic.jpg"].dst.parent.name == "Images" and plan["pic.jpg"].via == "rule"
    assert plan["invoice_oct.pdf"].dst.parent.name == "Receipts" and plan["invoice_oct.pdf"].via == "gemma"
    assert plan["mystery.pdf"].dst.parent.name == "Other" and plan["mystery.pdf"].via == "fallback"


def test_skips_hidden_partial_recent_and_dirs(tmp_path):
    touch(tmp_path / ".hidden.png")
    touch(tmp_path / "movie.mp4.crdownload")
    touch(tmp_path / "fresh.png", age=5)
    (tmp_path / "somedir").mkdir()
    assert planner.build_plan(tmp_path, min_age=300) == []


def test_collisions_never_overwrite(tmp_path):
    (tmp_path / "Images").mkdir()
    touch(tmp_path / "Images" / "a.png")
    touch(tmp_path / "a.png")
    plan = planner.build_plan(tmp_path, min_age=0)
    assert plan[0].dst.name == "a (2).png"


def test_apply_and_undo_roundtrip(tmp_path):
    touch(tmp_path / "a.png")
    touch(tmp_path / "b.zip")
    plan = planner.build_plan(tmp_path, min_age=0)
    log, errors = mover.apply_plan(plan, tmp_path)
    assert not errors and (tmp_path / "Images" / "a.png").exists() and not (tmp_path / "a.png").exists()
    assert json.loads(log.read_text())["moves"]
    restored, skipped = mover.undo(mover.latest_log(tmp_path))
    assert restored == 2 and not skipped
    assert (tmp_path / "a.png").exists() and not (tmp_path / "Images").exists()


def test_llm_rejects_answers_outside_allowed(monkeypatch):
    c = OllamaClient(model="m")
    monkeypatch.setattr(c, "_request", lambda *a, **k: {"message": {"content": json.dumps({"folder": "Hacked", "reason": "x"})}})
    assert c.classify("a.pdf", ["Documents/Study"]) is None
    monkeypatch.setattr(c, "_request", lambda *a, **k: {"message": {"content": json.dumps({"folder": "Documents/Study", "reason": "notes"})}})
    assert c.classify("a.pdf", ["Documents/Study"]) == ("Documents/Study", "notes")


def test_llm_survives_garbage_and_offline(monkeypatch):
    c = OllamaClient(model="m")
    monkeypatch.setattr(c, "_request", lambda *a, **k: {"message": {"content": "not json"}})
    assert c.classify("a.pdf", ["Documents/Study"]) is None
    c2 = OllamaClient(host="http://127.0.0.1:9", model="m", timeout=1)
    ok, msg = c2.check()
    assert not ok and "ollama serve" in msg
