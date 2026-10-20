"""Tiny Ollama client (standard library only). Talks to a model running on YOUR machine."""

import json
import os
import urllib.error
import urllib.request

DEFAULT_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "gemma4:e2b"

SYSTEM = (
    "You sort files into folders for a busy student. You are given only a file name "
    "(and sometimes a short text snippet). Pick exactly one folder from the allowed list. "
    "Study = lectures, assignments, notes, textbooks, papers, syllabus. "
    "Work = resumes, offer letters, internship or job documents, reports for employers. "
    "Personal = ID, tickets, travel, health, family. Receipts = invoices, bills, payment proofs. "
    "If unsure, choose the 'Other' option. Reply with JSON only."
)


class OllamaClient:
    def __init__(self, host=None, model=None, timeout=120):
        host = host or os.environ.get("OLLAMA_HOST") or DEFAULT_HOST
        if not host.startswith("http"):
            host = "http://" + host
        self.host = host.rstrip("/")
        self.model = model or os.environ.get("SLOTHSORT_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    def _request(self, path, payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(
            self.host + path, data=data, headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            return json.loads(resp.read().decode())

    def check(self):
        """Return (ok, message). Never raises."""
        try:
            tags = self._request("/api/tags")
        except (urllib.error.URLError, OSError, ValueError):
            return False, f"Ollama is not reachable at {self.host}. Start it with: ollama serve"
        names = [m.get("name", "") for m in tags.get("models", [])]
        wanted = self.model if ":" in self.model else self.model + ":latest"
        if wanted not in names:
            return False, f"Model '{self.model}' not found locally. Run: ollama pull {self.model}"
        return True, f"Using {self.model} via {self.host}"

    def classify(self, name, allowed, snippet=""):
        """Return (folder, reason) or None. Output is validated against `allowed`."""
        schema = {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "enum": allowed},
                "reason": {"type": "string"},
            },
            "required": ["folder", "reason"],
        }
        user = f"File name: {name}\nAllowed folders: {', '.join(allowed)}"
        if snippet:
            user += f"\nFirst characters of the file:\n{snippet}"
        payload = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
        }
        try:
            content = self._request("/api/chat", payload)["message"]["content"]
            out = json.loads(content)
            folder = out["folder"]
        except (urllib.error.URLError, OSError, ValueError, KeyError, TypeError):
            return None
        if folder not in allowed:
            return None
        return folder, str(out.get("reason", ""))[:120]
