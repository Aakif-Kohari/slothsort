"""Apply a plan and undo it. Files are only ever moved: never deleted, never overwritten."""

import json
import shutil
import time
from pathlib import Path

LOG_DIR = ".slothsort"


def apply_plan(plan, root):
    """Move files, write an undo log, return (log_path or None, errors)."""
    root = Path(root).expanduser().resolve()
    done, errors = [], []
    try:
        for m in plan:
            try:
                m.dst.parent.mkdir(parents=True, exist_ok=True)
                if m.dst.exists():
                    raise FileExistsError(m.dst)
                shutil.move(str(m.src), str(m.dst))
                done.append({"src": str(m.src), "dst": str(m.dst)})
            except OSError as exc:
                errors.append(f"{m.src.name}: {exc}")
    finally:
        log_path = None
        if done:
            log_dir = root / LOG_DIR
            log_dir.mkdir(exist_ok=True)
            log_path = log_dir / time.strftime("undo-%Y%m%d-%H%M%S.json")
            n = 2
            while log_path.exists():
                log_path = log_dir / time.strftime(f"undo-%Y%m%d-%H%M%S-{n}.json")
                n += 1
            log_path.write_text(json.dumps({"moves": done}, indent=2))
    return log_path, errors


def latest_log(root):
    logs = sorted((Path(root).expanduser().resolve() / LOG_DIR).glob("undo-*.json"))
    return logs[-1] if logs else None


def undo(log_path):
    """Move every file back where it came from. Returns (restored, skipped_messages)."""
    moves = json.loads(Path(log_path).read_text())["moves"]
    restored, skipped = 0, []
    for entry in reversed(moves):
        src, dst = Path(entry["src"]), Path(entry["dst"])
        if not dst.exists():
            skipped.append(f"{dst.name}: no longer at {dst.parent}")
        elif src.exists():
            skipped.append(f"{dst.name}: original path is occupied")
        else:
            src.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(dst), str(src))
            restored += 1
            parent = dst.parent
            for folder in (parent, parent.parent):  # remove folders we created, if now empty
                if folder is parent or folder.name == "Documents":
                    try:
                        folder.rmdir()
                    except OSError:
                        pass
    return restored, skipped
