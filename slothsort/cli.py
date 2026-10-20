import argparse
import sys
import time
from collections import defaultdict
from pathlib import Path

from . import __version__
from .llm import OllamaClient
from .mover import apply_plan, latest_log, undo
from .planner import build_plan

SECONDS_PER_FILE = 10  # rough guess at manual sorting time; only used for the 'lazy payoff' line


def _add_common(p):
    p.add_argument("path", nargs="?", default="~/Downloads", help="folder to tidy (default: ~/Downloads)")
    p.add_argument("--no-ai", action="store_true", help="rules only, never call the model")
    p.add_argument("--peek", action="store_true", help="let the local model read the first 400 chars of .txt/.md files")
    p.add_argument("--model", help="Ollama model tag (default: gemma4:e2b or $SLOTHSORT_MODEL)")
    p.add_argument("--min-age", type=int, default=300, help="skip files modified in the last N seconds (default 300)")


def _make_plan(args):
    classify = None
    if not args.no_ai:
        client = OllamaClient(model=args.model)
        ok, msg = client.check()
        if ok:
            print(msg)
            classify = client.classify
        else:
            print(f"[rules only] {msg}", file=sys.stderr)
    started = time.time()
    plan = build_plan(args.path, classify=classify, peek=args.peek, min_age=args.min_age)
    return plan, time.time() - started


def _print_plan(plan, root):
    if not plan:
        print("Nothing to tidy. Very sloth of you.")
        return
    groups = defaultdict(list)
    for m in plan:
        groups[m.dst.parent.relative_to(Path(root).expanduser().resolve())].append(m)
    for folder in sorted(groups, key=str):
        print(f"\n{folder}/")
        for m in groups[folder]:
            tag = {"rule": "rule", "gemma": "gemma", "fallback": "?"}[m.via]
            print(f"  {m.src.name}  [{tag}] {m.reason}")
    n = {v: sum(m.via == v for m in plan) for v in ("rule", "gemma", "fallback")}
    print(f"\n{len(plan)} file(s): {n['rule']} by rules, {n['gemma']} by the local model, {n['fallback']} unsure (filed under Other).")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="slothsort", description="Tidy a folder with a local open-weight model. Dry-run by default.")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    _add_common(sub.add_parser("plan", help="show what would move (touches nothing)"))
    ap = sub.add_parser("apply", help="move the files (asks first, writes an undo log)")
    _add_common(ap)
    ap.add_argument("--yes", "-y", action="store_true", help="skip the confirmation prompt")
    up = sub.add_parser("undo", help="put everything back")
    up.add_argument("path", nargs="?", default="~/Downloads")
    up.add_argument("--log", help="specific undo log (default: the latest one)")
    args = parser.parse_args(argv)

    if args.cmd == "undo":
        log = Path(args.log) if args.log else latest_log(args.path)
        if not log:
            print("No undo log found.")
            return 1
        restored, skipped = undo(log)
        print(f"Restored {restored} file(s) from {log.name}.")
        for s in skipped:
            print(f"  skipped {s}")
        return 0

    plan, secs = _make_plan(args)
    _print_plan(plan, args.path)
    if args.cmd == "plan" or not plan:
        if plan:
            print("\nDry run only. Use `slothsort apply` to move files.")
        return 0
    if not args.yes and input("\nMove these files? [y/N] ").strip().lower() != "y":
        print("Cancelled. Nothing was moved.")
        return 0
    log, errors = apply_plan(plan, args.path)
    for e in errors:
        print(f"  could not move {e}", file=sys.stderr)
    saved = len(plan) * SECONDS_PER_FILE / 60
    print(f"\nDone in {secs:.1f}s of planning. At ~{SECONDS_PER_FILE}s per file by hand, that is roughly {saved:.1f} min of sorting skipped (an estimate, not a measurement).")
    if log:
        print(f"Changed your mind? slothsort undo {args.path}")
    return 0
