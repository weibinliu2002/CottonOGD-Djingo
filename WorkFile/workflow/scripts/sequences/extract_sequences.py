#!/usr/bin/env python3
"""Extract all sequence products required by the legacy CottonOGD backend.

Outputs (same names as the legacy pipeline):
  mrna.fa, cdna.fa, cds.fa, pro.fa, gene_genome.fa, span20000.fa

The four gffread commands mirror Script/snakemake/Snakefile's extract_* rules.
gene_genome.fa mirrors Script/snakemake/extract_seq.R (Name > ID > Parent).
span20000.fa is produced by gffread -u --w-add 20000 and split later by
split_flanks.py.
"""
import argparse
import os
import re
import shutil
import subprocess
import sys

try:
    from pyfaidx import Fasta
except Exception:  # pragma: no cover - pyfaidx is present in backend venv
    Fasta = None


def run(cmd):
    print("[CMD] " + " ".join(str(x) for x in cmd), flush=True)
    subprocess.run(cmd, check=True)


def parse_attrs(text):
    attrs = {}
    for item in text.strip().strip(";").split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
            attrs[key.strip()] = value.strip()
        else:
            m = re.match(r"^(\S+)\s+\"?(.+?)\"?$", item)
            if m:
                attrs[m.group(1).strip()] = m.group(2).strip().strip('"')
    return attrs


def open_text(path):
    import gzip
    with open(path, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return open(path, "rt", encoding="utf-8", errors="replace")


def write_fasta(path, records):
    with open(path, "w", encoding="utf-8") as out:
        for name, seq in records:
            out.write(f">{name}\n")
            for i in range(0, len(seq), 60):
                out.write(seq[i:i + 60] + "\n")


def copy_or_extract(provided, target, cmd):
    """Use a user-supplied FASTA when present, otherwise run gffread."""
    if provided and os.path.exists(provided):
        print(f"[INFO] using supplied file: {provided}")
        if os.path.abspath(provided) != os.path.abspath(target):
            shutil.copyfile(provided, target)
        return
    run(cmd)


def gene_records(gff_path, genome):
    """Yield (name, sequence) for gene rows, matching extract_seq.R naming."""
    records = []
    gene_rows = []
    tx_rows = []
    with open_text(gff_path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) != 9:
                continue
            ftype = fields[2].lower()
            attrs = parse_attrs(fields[8])
            if ftype in ("gene", "pseudogene"):
                gene_rows.append((fields, attrs))
            elif ftype in ("mrna", "transcript"):
                tx_rows.append((fields, attrs))
    if not gene_rows:
        print("[WARNING] no gene rows; using mRNA rows for gene_genome.fa")
        gene_rows = tx_rows

    for fields, attrs in gene_rows:
        seqid, start, end = fields[0], int(fields[3]), int(fields[4])
        if seqid not in genome:
            continue
        name = attrs.get("Name") or attrs.get("ID")
        if not name and attrs.get("Parent"):
            name = re.sub(r"\.\d+", "", attrs["Parent"])
        if not name:
            name = f"{seqid}_{start}_{end}"
        # Biostrings getSeq returns the genomic plus strand for a GRanges;
        # keep that behaviour for compatibility.
        seq = str(genome[seqid][start - 1:end])
        records.append((name, seq))
    return records


def main():
    ap = argparse.ArgumentParser(description="Extract mRNA/cDNA/CDS/protein/gene/flanks")
    ap.add_argument("--genome", required=True)
    ap.add_argument("--gff", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--gffread", default="gffread")
    ap.add_argument("--samtools", default="samtools")
    ap.add_argument("--flank", type=int, default=20000)
    ap.add_argument("--protein")
    ap.add_argument("--transcripts")
    ap.add_argument("--cds")
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    p = lambda name: os.path.join(args.outdir, name)
    mrna = p("mrna.fa")
    cdna = p("cdna.fa")
    cds = p("cds.fa")
    pro = p("pro.fa")
    span = p("span20000.fa")

    base = [args.gffread, "-E", args.gff, "-g", args.genome, "--w-nocds"]
    copy_or_extract(args.transcripts, mrna, base + ["-u", mrna])
    run(base + ["-w", cdna])
    copy_or_extract(args.cds, cds, base + ["-x", cds])
    copy_or_extract(args.protein, pro, base + ["-y", pro])

    # gffread --w-add adds N bases on both sides of every transcript, in the
    # transcript's orientation. split_flanks.py splits the two ends.
    run([
        args.gffread, "-E", args.gff, "-g", args.genome,
        "-u", span, "--w-add", str(args.flank),
    ])

    # gene_genome.fa needs an index; make one if it is missing.
    fai = args.genome + ".fai"
    if not os.path.exists(fai):
        try:
            run([args.samtools, "faidx", args.genome])
        except Exception as exc:
            print(f"[WARNING] samtools faidx failed: {exc}", file=sys.stderr)

    if Fasta is None:
        print("[ERROR] pyfaidx is required for gene_genome.fa", file=sys.stderr)
        return 3
    genome = Fasta(args.genome, as_raw=True, sequence_always_upper=False)
    try:
        records = gene_records(args.gff, genome)
        write_fasta(p("gene_genome.fa"), records)
    finally:
        genome.close()
    print(f"[OK] extracted: mrna/cdna/cds/pro/gene_genome ({len(records)} genes)/span20000")
    return 0


if __name__ == "__main__":
    sys.exit(main())