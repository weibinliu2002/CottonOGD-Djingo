#!/usr/bin/env python3
"""Helpers to publish canonical files and relative symlinks.

The backend keeps two parallel trees:

* `backend/data/Genome/{type}/` — real files, grouped by data type
* `backend/data/genome/{species}/` — per-species entry points, symlinks into
  `../../Genome/{type}/`

These helpers never delete existing regular files. With `overwrite=False`
(default) an existing destination is kept and a warning is returned.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile


def _log(msg):
    print(msg, flush=True)


def _replace_symlink(target, link):
    """Atomically create/replace a relative symlink."""
    os.makedirs(os.path.dirname(link), exist_ok=True)
    rel = os.path.relpath(target, os.path.dirname(link))
    tmp = link + ".tmp-symlink"
    if os.path.lexists(tmp):
        os.remove(tmp)
    os.symlink(rel, tmp)
    os.replace(tmp, link)


def ensure_symlink(target, link, overwrite=False):
    """Return (status, message). status is created|updated|skipped."""
    target = os.path.abspath(target)
    link = os.path.abspath(link)
    if not os.path.exists(target):
        return "skipped", f"target does not exist: {target}"
    if os.path.lexists(link):
        if os.path.islink(link):
            current = os.path.realpath(link)
            if current == os.path.realpath(target):
                return "skipped", f"symlink already correct: {link}"
            if not overwrite:
                return "skipped", f"symlink exists and points elsewhere: {link} -> {current}"
            _replace_symlink(target, link)
            return "updated", f"symlink updated: {link}"
        if not overwrite:
            return "skipped", f"regular file exists, not replacing: {link}"
        # Never delete an existing real file automatically, even with
        # --overwrite: replacing it requires an explicit manual decision.
        return "blocked", f"regular file exists; refusing to remove: {link}"
    _replace_symlink(target, link)
    return "created", f"symlink created: {link} -> {os.readlink(link)}"


def ensure_copy(src, dst, overwrite=False, hardlink=True):
    """Copy (or hardlink) a canonical file. Return (status, message)."""
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if not os.path.exists(src):
        return "skipped", f"source does not exist: {src}"
    if os.path.lexists(dst) and not overwrite:
        return "skipped", f"canonical file exists, not replacing: {dst}"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    tmp = dst + ".tmp"
    if os.path.lexists(tmp):
        os.remove(tmp)
    if hardlink:
        try:
            os.link(src, tmp)
        except OSError:
            shutil.copy2(src, tmp)
    else:
        shutil.copy2(src, tmp)
    os.replace(tmp, dst)
    return "created", f"canonical file written: {dst}"


def _is_gzip(path):
    with open(path, "rb") as fh:
        return fh.read(2) == b"\x1f\x8b"


def _is_bgzip(path, bgzip):
    if not _is_gzip(path):
        return False
    proc = subprocess.run(
        [bgzip, "-t", path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def ensure_bgzip(src, dst, bgzip="bgzip", overwrite=False):
    """Write a canonical bgzipped FASTA/GFF.

    Plain input is compressed directly; ordinary gzip input is decompressed
    first (otherwise it would be double-compressed); an existing bgzip file is
    copied as-is.
    """
    src = os.path.abspath(src)
    dst = os.path.abspath(dst)
    if not os.path.exists(src):
        return "skipped", f"source does not exist: {src}"
    if os.path.lexists(dst) and not overwrite:
        return "skipped", f"compressed file exists, not replacing: {dst}"
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=os.path.basename(dst) + ".", dir=os.path.dirname(dst))
    os.close(fd)
    try:
        if _is_bgzip(src, bgzip):
            shutil.copy2(src, tmp)
        elif _is_gzip(src):
            with open(tmp, "wb") as out:
                decomp = subprocess.Popen(["gzip", "-dc", src], stdout=subprocess.PIPE)
                try:
                    subprocess.run([bgzip, "-c"], stdin=decomp.stdout, stdout=out, check=True)
                finally:
                    if decomp.stdout:
                        decomp.stdout.close()
                    if decomp.wait() != 0:
                        raise RuntimeError(f"gzip decompression failed: {src}")
        else:
            with open(tmp, "wb") as out, open(src, "rb") as inp:
                subprocess.run([bgzip, "-c"], stdin=inp, stdout=out, check=True)
        os.replace(tmp, dst)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return "created", f"bgzip written: {dst}"


def ensure_fai(path, samtools="samtools", bgzip_index=False):
    """Create `.fai` (and `.gzi` for bgzipped input) when missing."""
    path = os.path.abspath(path)
    if not os.path.exists(path):
        return "skipped", f"file does not exist: {path}"
    fai = path + ".fai"
    if os.path.exists(fai) and os.path.getmtime(fai) >= os.path.getmtime(path):
        return "skipped", f"index exists: {fai}"
    subprocess.run([samtools, "faidx", path], check=True)
    if bgzip_index and path.endswith(".gz"):
        gzi = path + ".gzi"
        if not os.path.exists(gzi):
            # samtools faidx writes .gzi for bgzip inputs on modern versions;
            # fall back to `bgzip -r` if it did not.
            subprocess.run(["bgzip", "-r", path], check=False)
    return "created", f"index written: {fai}"


def sha256(path, max_bytes=None):
    if max_bytes is not None and os.path.getsize(path) > max_bytes:
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def record(path, base_dir, max_hash_bytes=None):
    path = os.path.abspath(path)
    info = {
        "path": os.path.relpath(path, base_dir) if os.path.exists(base_dir) else path,
        "size": os.path.getsize(path) if os.path.exists(path) else None,
        "symlink": os.path.islink(path),
    }
    if info["symlink"]:
        info["target"] = os.readlink(path)
    if os.path.exists(path) and not info["symlink"]:
        info["sha256"] = sha256(path, max_hash_bytes)
    return info