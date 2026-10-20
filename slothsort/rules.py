"""Deterministic extension rules. The model only sees files these rules cannot decide."""

from pathlib import Path

EXT_MAP = {
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp", ".svg", ".tiff"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv", ".wmv"},
    "Audio": {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".tgz"},
    "Installers": {".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk", ".appimage", ".iso"},
    "Code": {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".go", ".rs", ".html", ".css", ".sh", ".ipynb"},
    "Data": {".csv", ".tsv", ".xlsx", ".xls", ".json", ".parquet", ".sql", ".db", ".sqlite"},
}

# Documents are where extension alone is not enough: a PDF can be a textbook or a receipt.
DOC_EXTS = {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".ppt", ".pptx", ".epub"}
DOC_FOLDERS = [
    "Documents/Study",
    "Documents/Work",
    "Documents/Personal",
    "Documents/Receipts",
    "Documents/Other",
]
PARTIAL_EXTS = {".crdownload", ".part", ".tmp", ".download", ".partial"}
PEEK_EXTS = {".txt", ".md"}


def ext(path: Path) -> str:
    return path.suffix.lower()


def by_extension(path: Path):
    """Return the folder for an unambiguous extension, else None."""
    e = ext(path)
    for folder, exts in EXT_MAP.items():
        if e in exts:
            return folder
    return None


def allowed_folders(path: Path) -> list:
    """The only folders the model may choose from for this file."""
    if ext(path) in DOC_EXTS:
        return list(DOC_FOLDERS)
    return list(EXT_MAP) + ["Documents/Other", "Other"]


def fallback_folder(path: Path) -> str:
    return "Documents/Other" if ext(path) in DOC_EXTS else "Other"
