#!/usr/bin/env python3
import sys
import os
from Bio import SeqIO
from collections import defaultdict


def main():
    if len(sys.argv) != 2:
        print("Usage: python deduplicate_proteins.py <tmp_dir>")
        sys.exit(1)
    
    tmp_dir = sys.argv[1]
    all_proteins = os.path.join(tmp_dir, "all_proteins.fasta")
    unique_proteins = os.path.join(tmp_dir, "unique_proteins.fasta")
    
    seq_map = defaultdict(list)
    
    with open(all_proteins) as f:
        for record in SeqIO.parse(f, "fasta"):
            seq = str(record.seq)
            seq_map[seq].append(record.id)
    
    with open(unique_proteins, "w") as f:
        for i, (seq, ids) in enumerate(seq_map.items(), 1):
            f.write(f">unique_{i}|{','.join(ids[:5])}\\n{seq}\\n")
    
    print(f"合并完成: 原始 {sum(len(v) for v in seq_map.values())} 条, 去重后 {len(seq_map)} 条")


if __name__ == "__main__":
    main()
