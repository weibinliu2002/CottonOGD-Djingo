#!/usr/bin/env python3
"""Split gffread --w-add output into upstream and downstream 20 kb FASTA files.

gffread -u --w-add N writes, for each transcript, N bases upstream + the whole
transcript span + N bases downstream, in transcript orientation. Therefore the
first N bases are upstream and the last N bases are downstream. At chromosome
boundaries gffread returns fewer bases; the actual length is recorded in the
FASTA header and a warning is emitted instead of padding with N.
"""
import argparse
import sys


def parse_fasta(path):
    header, chunks = None, []
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\r\n")
            if line.startswith(">"):
                if header is not None:
                    yield header, "".join(chunks)
                header, chunks = line[1:], []
            elif header is not None:
                chunks.append(line.strip())
    if header is not None:
        yield header, "".join(chunks)


def write_record(out, header, suffix, seq):
    ident = header.split()[0]
    out.write(f">{ident}\t{suffix} {len(seq)}\n")
    for i in range(0, len(seq), 60):
        out.write(seq[i:i + 60] + "\n")


def main():
    ap = argparse.ArgumentParser(description="Split upstream/downstream flanks")
    ap.add_argument("--input", required=True, help="gffread -u --w-add output")
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--downstream", required=True)
    ap.add_argument("--flank", type=int, default=20000)
    args = ap.parse_args()

    n = args.flank
    count = truncated = 0
    with open(args.upstream, "w", encoding="utf-8") as up, \
            open(args.downstream, "w", encoding="utf-8") as down:
        for header, seq in parse_fasta(args.input):
            count += 1
            if len(seq) < 2 * n:
                truncated += 1
                print(
                    f"[WARNING] {header.split()[0]}: length {len(seq)} < {2*n}; "
                    "flanks overlap/are truncated",
                    file=sys.stderr,
                )
            up_seq = seq[:min(n, len(seq))]
            down_seq = seq[-min(n, len(seq)):]
            write_record(up, header, "Up_Stream_Len", up_seq)
            write_record(down, header, "Down_Stream_Len", down_seq)

    print(f"[OK] split {count} records into upstream/downstream; truncated={truncated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())