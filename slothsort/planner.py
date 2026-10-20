"""Build a move plan. Planning never touches the disk beyond reading names and mtimes."""

import time
from dataclasses import dataclass
from pathlib import Path

from . import rules


@dataclass
class Move:
    src: Path
    dst: Path
    reason: str
    via: str  # "rule", "gemma" or "fallback"


def unique_path(dst: Path, taken: set) -> Path:
    """Never overwrite: add ' (2)', ' (3)'... before the extension."""
    candidate, n = dst, 2
    while candidate.exists() or candidate in taken:
        candidate = dst.with_name(f"{dst.stem} ({n}){dst.suffix}")
        n += 1
    return candidate


def read_snippet(path: Path, limit=400) -> str:
    if rules.ext(path) not in rules.PEEK_EXTS:
        return ""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read(limit)
    except OSError:
        return ""


def build_plan(root, classify=None, peek=False, min_age=300, now=None):
    """Plan moves for the top-level files in `root` (not recursive).

    classify(name, allowed, snippet) -> (folder, reason) | None
    """
    root = Path(root).expanduser().resolve()
    now = time.time() if now is None else now
    plan, taken = [], set()
    for p in sorted(root.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_file() or p.is_symlink() or p.name.startswith("."):
            continue
        if rules.ext(p) in rules.PARTIAL_EXTS:
            continue
        if now - p.stat().st_mtime < min_age:  # probably still downloading
            continue
        folder = rules.by_extension(p)
        via, reason = "rule", f"{rules.ext(p) or 'no extension'} -> {folder}"
        if folder is None and classify is not None:
            snippet = read_snippet(p) if peek else ""
            result = classify(p.name, rules.allowed_folders(p), snippet)
            if result:
                (folder, reason), via = result, "gemma"
        if folder is None:
            folder, via, reason = rules.fallback_folder(p), "fallback", "no confident match"
        dst = unique_path(root / folder / p.name, taken)
        taken.add(dst)
        plan.append(Move(p, dst, reason, via))
    return plan
