#!/usr/bin/env python3
"""Split a tetraploid FASTA into At and Dt subgenome FASTA files.

Diploid handling: for a diploid genome, writes a single 'Whole' fasta
(identity copy of input) instead of splitting.

FASTA extraction is delegated to ``seqkit grep -f`` (streaming, no in-memory
load of the multi-GB genome), which is far more efficient than parsing the
whole FASTA in Python. Python only processes the small subgenome_map.tsv to
build the id lists, the identity mapping TSV and the stats.

Outputs (into out_dir):
  source.At.fa / source.Dt.fa  (or source.Whole.fa for diploids)
  split_stats.tsv
  sequence_id_mapping.tsv      -- tmp_id -> real seqid (for chain recovery)
  at_list.tsv / dt_list.tsv / unassigned_list.tsv
"""
import argparse
import csv
import os
import subprocess
import sys


def load_subgenome_map(path):
    """subgenome_mapping.tsv -> {seqid: subgenome}."""
    m = {}
    if not os.path.exists(path):
        return m
    with open(path, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            sid = (row.get("fasta_seqid") or "").strip()
            sub = (row.get("subgenome") or "").strip()
            if sid and sub:
                m[sid] = sub
    return m


def write_lines(path, ids):
    with open(path, "w", encoding="utf-8") as fh:
        for sid in ids:
            fh.write(sid + "\n")


def seqkit_ids(seqkit, fasta):
    """Return all FASTA sequence ids in file order (streaming, light).

    Only the first whitespace-delimited token of each header is kept, matching
    the id used elsewhere (and by seqkit's default name match). A header with a
    description (``>id some text``) therefore yields ``id``.
    """
    try:
        proc = subprocess.run([seqkit, "seq", "-n", fasta],
                              check=True, capture_output=True, text=True)
    except FileNotFoundError:
        print(f"[ERROR] seqkit binary not found: {seqkit}", file=sys.stderr)
        raise
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] seqkit seq failed: {exc.stderr}", file=sys.stderr)
        raise
    out = []
    for ln in proc.stdout.splitlines():
        ln = ln.strip()
        if ln:
            out.append(ln.split(None, 1)[0])
    return out


def seqkit_grep(seqkit, fasta, ids, out_path):
    """Write FASTA entries whose id is in ``ids`` via ``seqkit grep -f -``.

    FASTA ids are piped on stdin so no temp file is needed. ``seqkit grep``
    preserves the order in which sequences appear in ``fasta`` (not the list
    order), matching the original streaming behaviour. An empty id list emits
    an empty file.
    """
    if not ids:
        open(out_path, "w", encoding="utf-8").close()
        return 0
    try:
        with open(out_path, "w", encoding="utf-8") as fh:
            subprocess.run([seqkit, "grep", "-f", "-", fasta],
                           check=True, input="".join(s + "\n" for s in ids),
                           stdout=fh, text=True)
    except FileNotFoundError:
        print(f"[ERROR] seqkit binary not found: {seqkit}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"[ERROR] seqkit grep failed: {exc}", file=sys.stderr)
        return exc.returncode
    return 0


def main():
    ap = argparse.ArgumentParser(description="Split tetraploid FASTA into At/Dt (via seqkit)")
    ap.add_argument("--fasta", required=True)
    ap.add_argument("--subgenome-map", required=True)
    ap.add_argument("--genome-id", required=True)
    ap.add_argument("--ploidy", required=True)
    ap.add_argument("--out-at", required=True)
    ap.add_argument("--out-dt", required=True)
    ap.add_argument("--out-whole", required=True)
    ap.add_argument("--out-stats", required=True)
    ap.add_argument("--id-map", required=True)
    ap.add_argument("--at-list", required=True)
    ap.add_argument("--dt-list", required=True)
    ap.add_argument("--unassigned-list", required=True)
    ap.add_argument("--seqkit", default="/home/web/bin/seqkit",
                    help="path to seqkit binary")
    args = ap.parse_args()

    sub_map = load_subgenome_map(args.subgenome_map)
    diploid = (args.ploidy == "diploid")

    # Enumerate every sequence in the FASTA (ids only, streaming) so we can
    # faithfully reproduce the original behaviour: sequences absent from the map
    # fall into Unassigned, and a diploid Whole is an exact copy of the input.
    try:
        all_ids = seqkit_ids(args.seqkit, args.fasta)
    except (FileNotFoundError, subprocess.CalledProcessError):
        return 2

    at_ids, dt_ids, unassigned_ids = [], [], []
    if diploid:
        # Whole = identity copy of the entire input; At/Dt/Unassigned unused.
        whole_ids = list(all_ids)
    else:
        whole_ids = []
        for sid in all_ids:
            sub = sub_map.get(sid, "Unassigned")
            if sub == "At":
                at_ids.append(sid)
            elif sub == "Dt":
                dt_ids.append(sid)
            else:
                unassigned_ids.append(sid)

    if diploid:
        rc = seqkit_grep(args.seqkit, args.fasta, whole_ids, args.out_whole)
        if rc:
            return rc
        open(args.out_at, "w", encoding="utf-8").close()
        open(args.out_dt, "w", encoding="utf-8").close()
    else:
        rc = seqkit_grep(args.seqkit, args.fasta, at_ids, args.out_at)
        if rc:
            return rc
        rc = seqkit_grep(args.seqkit, args.fasta, dt_ids, args.out_dt)
        if rc:
            return rc
        # Whole is unused for tetraploids; emit empty so the output exists.
        open(args.out_whole, "w", encoding="utf-8").close()

    # Lists (ids only)
    write_lines(args.at_list, at_ids)
    write_lines(args.dt_list, dt_ids)
    write_lines(args.unassigned_list, unassigned_ids)

    # Identity id mapping (real seqid -> real seqid) for chain recovery.
    # Covers every sequence in the FASTA regardless of ploidy.
    with open(args.id_map, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        w.writerow(["tmp_id", "real_seqid"])
        ids_all = whole_ids if diploid else (at_ids + dt_ids + unassigned_ids)
        for sid in ids_all:
            w.writerow([sid, sid])

    # Stats
    stats = {
        "total_sequences": len(all_ids),
        "at_sequences": len(at_ids),
        "dt_sequences": len(dt_ids),
        "unassigned_sequences": len(unassigned_ids),
        "whole_sequences": len(whole_ids) if diploid else 0,
    }
    with open(args.out_stats, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(stats.keys()), delimiter="\t")
        w.writeheader()
        w.writerow(stats)

    print(f"{args.genome_id}: {stats}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
