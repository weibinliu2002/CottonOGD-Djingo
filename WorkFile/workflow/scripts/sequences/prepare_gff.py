#!/usr/bin/env python3
"""Prepare a sorted, coordinate-sanitised GFF for all downstream tools.

Equivalent to the legacy decompress_gff + fix_gff.sh pair:
  * decompress plain/gzip GFF
  * keep only seqids present in the genome
  * swap start/end when start > end
  * drop coordinates outside the sequence
  * replace strand '?' with '.'
  * sort by genome sequence order, then start
  * bgzip + tabix
"""
import argparse
import gzip
import os
import subprocess
import sys
import tempfile

# Make workflow/scripts/seqid_alias.py importable when this script is run by
# Snakemake with an absolute path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seqid_alias import SeqidResolver


def open_text(path):
    real = os.path.realpath(path)
    with open(real, "rb") as fh:
        magic = fh.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(real, "rt", encoding="utf-8", errors="replace")
    return open(real, "rt", encoding="utf-8", errors="replace")


def looks_like_gtf(path):
    """Detect GTF by extension or by its `key "value";` attribute syntax."""
    name = str(path).lower()
    if name.endswith((".gtf", ".gtf.gz")):
        return True
    with open_text(path) as fh:
        for line in fh:
            if not line.strip() or line.startswith("#"):
                continue
            fields = line.rstrip("\r\n").split("\t")
            if len(fields) == 9:
                # GTF always uses `gene_id "x";`; GFF3 uses `ID=x;`.
                return "=" not in fields[8] and "gene_id" in fields[8]
    return False


def convert_gtf(path, gffread, tmpdir):
    """Convert GTF to GFF3, keeping gene rows (`-O`) and all attributes (`-F`)."""
    fd, tmp = tempfile.mkstemp(prefix=".converted.", suffix=".gff", dir=tmpdir)
    os.close(fd)
    proc = subprocess.run(
        [gffread, "-F", "-O", "-o", tmp, path],
        stdout=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        os.remove(tmp)
        raise RuntimeError(f"gffread failed to convert GTF: {path}")
    return tmp


def parse_attrs(text):
    """Parse GFF3 key=value or GTF key "value" attribute syntax."""
    attrs = {}
    for item in str(text).strip().strip(";").split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            key, value = item.split("=", 1)
        else:
            parts = item.split(None, 1)
            if len(parts) != 2:
                continue
            key, value = parts
        attrs[key.strip()] = value.strip().strip('"')
    return attrs


def add_missing_gene_records(records):
    """Synthesize `gene` rows when the annotation only has transcript rows.

    GTF files (and some transcript-only GFF3 files) have no `gene` feature.
    gffread keeps the gene id on the transcript (`geneID=...` or `gene_id=...`)
    but does not create a gene row. Downstream steps (gene_genome extraction,
    the database uploader and GO/KEGG JBrowse tracks) need gene coordinates,
    so derive them from the union of their transcripts.
    """
    existing = set()
    transcript_ids = set()
    for _seqid, _start, _end, fields in records:
        attrs = parse_attrs(fields[8])
        ftype = fields[2].lower()
        if ftype in ("gene", "pseudogene"):
            gid = attrs.get("ID") or attrs.get("gene_id")
            if gid:
                existing.add(gid)
        elif ftype in ("mrna", "transcript"):
            tid = attrs.get("ID") or attrs.get("transcript_id")
            if tid:
                transcript_ids.add(tid)

    spans = {}
    for seqid, start, end, fields in records:
        if fields[2].lower() not in ("mrna", "transcript"):
            continue
        attrs = parse_attrs(fields[8])
        gid = attrs.get("geneID") or attrs.get("gene_id")
        if not gid:
            parent = (attrs.get("Parent") or "").split(",")[0].strip()
            # In GFF3 an mRNA Parent is normally a gene; ignore the rare case
            # of a transcript parented to another transcript.
            if parent and parent not in transcript_ids:
                gid = parent
        if not gid or gid in existing:
            continue
        key = (gid, seqid)
        if key not in spans:
            spans[key] = [start, end, fields[1], fields[6]]
        else:
            spans[key][0] = min(spans[key][0], start)
            spans[key][1] = max(spans[key][1], end)

    added = 0
    for (gid, seqid), (start, end, source, strand) in spans.items():
        if gid in existing:
            continue
        attrs = f"ID={gid}"
        records.append((
            seqid, start, end,
            [seqid, source or "workflow", "gene", str(start), str(end), ".", strand or ".", ".", attrs],
        ))
        existing.add(gid)
        added += 1
    return added


def genome_lengths(path):
    """Return ordered ids, lengths, and full FASTA headers without loading DNA."""
    order, lengths, headers = [], {}, {}
    current = None
    length = 0
    with open_text(path) as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if line.startswith(">"):
                if current is not None:
                    lengths[current] = length
                header = line[1:].strip()
                current = header.split()[0]
                headers[current] = header
                order.append(current)
                length = 0
            elif current is not None:
                length += len(line)
    if current is not None:
        lengths[current] = length
    return order, lengths, headers


def main():
    ap = argparse.ArgumentParser(description="Prepare sorted GFF")
    ap.add_argument("--genome", required=True)
    ap.add_argument("--gff", required=True)
    ap.add_argument("--out", required=True, help="plain GFF output path")
    ap.add_argument("--gffread", default="gffread")
    ap.add_argument("--bgzip", default="bgzip")
    ap.add_argument("--tabix", default="tabix")
    args = ap.parse_args()

    order, lengths, genome_headers = genome_lengths(args.genome)
    if not order:
        print("[ERROR] genome FASTA is empty", file=sys.stderr)
        return 2
    rank = {name: idx for idx, name in enumerate(order)}
    resolver = SeqidResolver(lengths, genome_headers)

    outdir = os.path.dirname(os.path.abspath(args.out))
    os.makedirs(outdir, exist_ok=True)
    converted = None
    gff_source = args.gff
    try:
        if looks_like_gtf(args.gff):
            converted = convert_gtf(args.gff, args.gffread, outdir)
            gff_source = converted
            print(f"[INFO] converted GTF to GFF3: {args.gff} -> {converted}")

        headers, records = [], []
        dropped_seqid = dropped_coord = swapped = 0
        unresolved_seqids = set()
        with open_text(gff_source) as fh:
            for line in fh:
                line = line.rstrip("\r\n")
                if not line:
                    continue
                # A GFF3 may embed the genome after ##FASTA; stop before writing it
                # into the annotation or trying to parse sequence lines as features.
                if line.startswith("##FASTA"):
                    break
                if line.startswith("#"):
                    headers.append(line)
                    continue
                fields = line.split("\t")
                if len(fields) != 9:
                    continue
                seqid = fields[0]
                resolved = resolver.resolve(seqid)
                if resolved is None:
                    dropped_seqid += 1
                    unresolved_seqids.add(seqid)
                    continue
                if resolved != seqid:
                    # Rewrite aliases so all downstream tools (gffread, JBrowse,
                    # BLAST) see the same seqids as the genome FASTA.
                    seqid = resolved
                    fields[0] = resolved
                try:
                    start, end = int(fields[3]), int(fields[4])
                except ValueError:
                    dropped_coord += 1
                    continue
                if start > end:
                    start, end = end, start
                    swapped += 1
                if start < 1 or end > lengths[seqid]:
                    dropped_coord += 1
                    continue
                fields[3], fields[4] = str(start), str(end)
                if fields[6] == "?":
                    fields[6] = "."
                records.append((seqid, start, end, fields))

        added_genes = add_missing_gene_records(records)

        # Gene rows must precede their transcripts when they share a start
        # coordinate, which keeps GFF3 consumers that rely on file order happy.
        feature_rank = {"gene": 0, "pseudogene": 0, "mrna": 1, "transcript": 1}
        records.sort(key=lambda r: (
            rank.get(r[0], len(rank)), r[1],
            feature_rank.get(r[3][2].lower(), 2), r[2],
        ))
        with open(args.out, "w", encoding="utf-8") as out:
            if not any(h.startswith("##gff-version") for h in headers):
                out.write("##gff-version 3\n")
            for header in headers:
                out.write(header + "\n")
            for _seqid, _start, _end, fields in records:
                out.write("\t".join(fields) + "\n")

        gz = args.out + ".gz"
        with open(args.out, "rb") as fin, open(gz, "wb") as fout:
            proc = subprocess.run([args.bgzip, "-c"], stdin=fin, stdout=fout)
            if proc.returncode != 0:
                print(f"[ERROR] bgzip failed for {args.out}", file=sys.stderr)
                return 3
        proc = subprocess.run([args.tabix, "-f", "-p", "gff", gz])
        if proc.returncode != 0:
            print(f"[ERROR] tabix failed for {gz}", file=sys.stderr)
            return 3
    finally:
        if converted and os.path.exists(converted):
            os.remove(converted)

    print(
        f"[OK] GFF prepared: {len(records)} records; "
        f"dropped_seqid={dropped_seqid}, dropped_coord={dropped_coord}, "
        f"swapped={swapped}, synthesized_genes={added_genes}, "
        f"seqid_aliases={len(resolver.aliases)}"
    )
    if unresolved_seqids:
        print(
            "[WARNING] GFF seqid(s) absent from genome and dropped: "
            + ", ".join(sorted(unresolved_seqids)[:10]),
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())