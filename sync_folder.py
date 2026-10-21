"""Shared sync folder: a small, deliberately simple file sync between the
people in one chat. Pure logic, no Qt, no networking.

- changed() lists files that are new or modified since the last scan
  (so the chat page can send each as an encrypted envelope);
- write_incoming() safely stores a file received from someone else.

Limits: depth <= 3, <= 200 files, <= 20 MB per file, no deletions are
synced, last write wins. Incoming paths are strictly validated so a member
can never write outside the folder you chose.
"""

import hashlib
import os

MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_FILES = 200
MAX_DEPTH = 3


def _clean_parts(rel):
    if not isinstance(rel, str) or not rel or "\\" in rel or rel.startswith("/") or len(rel) > 240:
        return None
    parts = rel.split("/")
    if len(parts) > MAX_DEPTH + 1:
        return None
    for p in parts:
        if p in ("", ".", "..") or p.startswith(".") or ":" in p or p.endswith((" ", ".")):
            return None
        if any(ord(ch) < 32 or ch in '<>"|?*' for ch in p):
            return None
    return parts


class SyncFolder:
    def __init__(self, folder):
        self.folder = os.path.abspath(folder)
        self.known = {}   # rel path -> (mtime_ns, size)

    def _iter_files(self):
        base_depth = self.folder.rstrip(os.sep).count(os.sep)
        count = 0
        for root, dirs, files in os.walk(self.folder):
            depth = root.rstrip(os.sep).count(os.sep) - base_depth
            dirs[:] = [d for d in dirs if not d.startswith(".")] if depth < MAX_DEPTH else []
            for name in files:
                if name.startswith(".") or name.endswith((".tmp", ".part")):
                    continue
                full = os.path.join(root, name)
                rel = os.path.relpath(full, self.folder).replace(os.sep, "/")
                if _clean_parts(rel) is None:
                    continue
                yield rel, full
                count += 1
                if count >= MAX_FILES:
                    return

    def prime(self):
        """Remember what's already there so it isn't re-sent."""
        self.known = {}
        for rel, full in self._iter_files():
            try:
                st = os.stat(full)
                self.known[rel] = (st.st_mtime_ns, st.st_size)
            except OSError:
                continue

    def changed(self, force_all=False):
        """[(rel, bytes, sha256 hex)] for new/modified files."""
        out = []
        for rel, full in self._iter_files():
            try:
                st = os.stat(full)
                sig = (st.st_mtime_ns, st.st_size)
                if not force_all and self.known.get(rel) == sig:
                    continue
                self.known[rel] = sig
                if st.st_size > MAX_FILE_BYTES:
                    continue
                with open(full, "rb") as f:
                    data = f.read()
                out.append((rel, data, hashlib.sha256(data).hexdigest()))
            except OSError:
                continue
        return out

    def write_incoming(self, rel, data, sha):
        """Store a received file. Returns True if written."""
        parts = _clean_parts(rel)
        if parts is None or len(data) > MAX_FILE_BYTES:
            return False
        if hashlib.sha256(data).hexdigest() != sha:
            return False
        target = os.path.abspath(os.path.join(self.folder, *parts))
        if os.path.commonpath([self.folder, target]) != self.folder:
            return False
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            if os.path.isfile(target):
                with open(target, "rb") as f:
                    if hashlib.sha256(f.read()).hexdigest() == sha:
                        return False  # already identical
            tmp = target + ".part"
            with open(tmp, "wb") as f:
                f.write(data)
            os.replace(tmp, target)
            st = os.stat(target)
            self.known[rel] = (st.st_mtime_ns, st.st_size)   # don't echo it back
            return True
        except OSError:
            return False
