# SlothSort 🦥

> The Downloads-folder tidier for people who would rather not tidy their Downloads folder.

SlothSort sorts the loose files in a folder (default `~/Downloads`) into sensible subfolders. Obvious files (`.png`, `.zip`, `.mp3`...) are handled by instant rules. The ambiguous ones, like a PDF that could be lecture notes or a receipt, are decided by an **open-weight model running on your own machine** (Gemma through [Ollama](https://ollama.com)). Nothing leaves your laptop, it works offline, and it costs nothing per run.

Built for the DEV x MLH [Hacktoberfest Open-Source AI Challenge: Week 3 ("Slow and Steady")](https://dev.to/challenges/hacktoberfest-week3-2026-10-19).

## Why it is safe to be lazy

- **Dry run by default.** `slothsort plan` shows every move and touches nothing.
- **Never deletes, never overwrites.** Files are only moved. Name clashes become `name (2).ext`.
- **One-command undo.** Every `apply` writes a log to `.slothsort/`; `slothsort undo` puts everything back.
- **The model cannot go rogue.** It must pick from a fixed list of folders (enforced with a JSON schema *and* re-validated in code). It never sees file contents unless you pass `--peek`, and then only the first 400 characters of `.txt`/`.md` files.
- **Skips what it should.** Hidden files, partial downloads (`.crdownload`, `.part`...), subfolders and anything modified in the last 5 minutes are left alone.

## Quick start

```bash
# 1. Install Ollama (https://ollama.com) and pull a small open-weight model
ollama pull gemma4:e2b

# 2. Get SlothSort (Python 3.9+, no dependencies)
git clone https://github.com/Aakif-Kohari/slothsort.git
cd slothsort
pip install -e .

# 3. Look before you leap
slothsort plan ~/Downloads

# 4. Do it (asks for confirmation; add --yes to skip)
slothsort apply ~/Downloads

# 5. Changed your mind?
slothsort undo ~/Downloads
```

No install? `python -m slothsort plan ~/Downloads` works from the repo folder too.

## Usage

```
slothsort plan  [PATH] [--no-ai] [--peek] [--model TAG] [--min-age SECONDS]
slothsort apply [PATH] [--no-ai] [--peek] [--model TAG] [--min-age SECONDS] [--yes]
slothsort undo  [PATH] [--log FILE]
```

| Flag | What it does |
|---|---|
| `--no-ai` | Rules only. Never contacts the model. |
| `--peek` | Lets the local model read the first 400 characters of `.txt` / `.md` files to decide better. |
| `--model TAG` | Any Ollama model tag, e.g. `gemma4:e4b`. Also settable via `SLOTHSORT_MODEL`. |
| `--min-age N` | Skip files modified in the last N seconds (default 300). |

If Ollama is not running or the model is not pulled, SlothSort says so and carries on with rules only, so it never blocks you.

## Where files go

| Folder | Decided by |
|---|---|
| `Images/`, `Videos/`, `Audio/`, `Archives/`, `Installers/`, `Code/`, `Data/` | Extension rules (instant, no model) |
| `Documents/Study`, `Documents/Work`, `Documents/Personal`, `Documents/Receipts` | The local model, for `.pdf`, `.docx`, `.txt`, `.md`, `.pptx`... |
| `Documents/Other`, `Other` | Model unsure, or no match |

Each line of the plan is tagged `[rule]`, `[gemma]` or `[?]` so you can see who decided what.

## How it works

```
folder -> planner -> rules.py (extension)  ---------------> destination
                  \-> llm.py (Gemma via Ollama, JSON-schema constrained) -> destination
                  -> mover.py (move + undo log)
```

- `slothsort/rules.py`: deterministic extension rules and the allowed-folder lists.
- `slothsort/llm.py`: a ~90-line Ollama client using only the standard library. Uses `/api/chat` with a JSON schema in `format`, temperature 0.
- `slothsort/planner.py`: builds the move plan; collision-safe.
- `slothsort/mover.py`: applies the plan and writes/reads undo logs.
- `slothsort/cli.py`: the `plan` / `apply` / `undo` commands.

## Why open models?

- **Privacy:** your file names (and optionally text) stay on your machine.
- **Offline:** works on a train, in a hostel, with no Wi-Fi.
- **Free forever:** no API key, no per-call cost, no quota.
- **Swappable:** change the model with one flag. Any Ollama model that supports structured output works.

## Development

```bash
pip install -e .[dev]
pytest -q
```

The tests use fake classifiers and temporary folders, so they never need Ollama and never touch real files.

## Limitations

- Only the top level of the chosen folder is tidied (not recursive, on purpose).
- PDFs and Office files are classified by file name only; their contents are not read.
- Small models can be wrong. That is what `plan` and `undo` are for.
- The "minutes saved" line printed by `apply` is a rough estimate (10 s per file), not a benchmark.

## License

MIT. Gemma models are subject to the [Gemma Terms of Use](https://ai.google.dev/gemma/terms).
