#!/usr/bin/env python3
"""Merge BLASTP hits with UniProt Swiss-Prot headers (legacy semantics).

The parsing rules mirror /public2/wbliu/data/CottonOGD/Function/uniprot/
unipro_annotation.py: UniProt accession is the middle `sp|ACC|ENTRY` field;
protein name is the text before `OS=`; species is between `OS=` and `OX=`;
gene name is between `GN=` and `PE=`. The UniProt FASTA is streamed twice so
only accessions present in the hits are kept in memory.
"""
import argparse
import os
import sys


def read_hits(path):
    hits = []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 12:
                continue
            hits.append({
                "query": cols[0],
                "uniprot_id": cols[1],
                "identity": cols[2],
                "evalue": cols[10],
            })
    wanted = {h["uniprot_id"] for h in hits}
    return hits, wanted


def read_headers(path, wanted):
    headers = {}
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.startswith(">"):
                continue
            header = line[1:].strip()
            parts = header.split("|")
            if len(parts) >= 3 and parts[1] in wanted:
                headers[parts[1]] = header
    return headers


def parse_header(header):
    protein_name = gene_name = species = "NA"
    ox = pe = sv = None
    if " OS=" in header:
        before = header.split(" OS=")[0]
        if " " in before:
            protein_name = before.split(" ", 1)[1]
    if "OS=" in header and "OX=" in header:
        species = header.split("OS=")[1].split(" OX=")[0]
    if "GN=" in header and "PE=" in header:
        gene_name = header.split("GN=")[1].split(" PE=")[0]
    for key, name in (("OX=", "ox"), ("PE=", "pe"), ("SV=", "sv")):
        if key in header:
            token = header.split(key)[1].split(" ")[0]
            try:
                value = int(token)
            except ValueError:
                continue
            if name == "ox":
                ox = value
            elif name == "pe":
                pe = value
            else:
                sv = value
    return protein_name, gene_name, species, ox, pe, sv


def main():
    ap = argparse.ArgumentParser(description="Merge UniProt BLAST hits and headers")
    ap.add_argument("--m8", required=True)
    ap.add_argument("--uniprot-fasta", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    if not os.path.exists(args.m8):
        print(f"[ERROR] hits file not found: {args.m8}", file=sys.stderr)
        return 3
    if not os.path.exists(args.uniprot_fasta):
        print(f"[ERROR] UniProt FASTA not found: {args.uniprot_fasta}", file=sys.stderr)
        return 3

    hits, wanted = read_hits(args.m8)
    headers = read_headers(args.uniprot_fasta, wanted)
    missing = len(wanted) - len(headers)
    if missing:
        print(f"[WARN] {missing} UniProt accessions not found in FASTA", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as out:
        out.write(
            "Query_ID\tUniProt_ID\tIdentity\tE-value\tProtein_Name\tGene_Name\t"
            "Species\tFull_Header\tOX\tPE\tSV\n"
        )
        for hit in hits:
            header = headers.get(hit["uniprot_id"], "NA")
            protein_name, gene_name, species, ox, pe, sv = parse_header(header)
            out.write(
                "\t".join(
                    str(v) for v in (
                        hit["query"], hit["uniprot_id"], hit["identity"], hit["evalue"],
                        protein_name, gene_name, species, header,
                        ox if ox is not None else "NA",
                        pe if pe is not None else "NA",
                        sv if sv is not None else "NA",
                    )
                ) + "\n"
            )
    print(f"[OK] UniProt: {len(hits)} hits, {len(headers)} headers")
    return 0


if __name__ == "__main__":
    sys.exit(main())