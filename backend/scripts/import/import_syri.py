#!/usr/bin/env python
"""
导入 SyRI 成对结构变异到 CottonOGD 的 syri_sr / syri_seq 表。

数据来源：genome_SV/<ref>_vs_<query>/syri.out（12 列，1-based）
路由规则（设计稿 §1.2 / §4.1）：
  - SR 结构重排  → syri_sr : SYN INV TRANS INVTR DUP INVDP
  - SEQ 序列注释 → syri_seq: HDR TDM CPG CPL
  - 短变异 SNP/INS/DEL（col4/col5 为具体碱基）与对齐注释（SYNAL/INVAL/.../NOTAL）
    不入库（短变异走文件层 C 域，对齐注释无变异语义）

幂等：先定位/创建 genome_pair(ref,query)，DELETE 该 pair 的旧 syri_sr/syri_seq
行后重导。重跑不影响其他 pair。

用法：
  python scripts/import/import_syri.py --syri-out <path> --summary <path> \
      --ref-id 67 --query-id 84 [--ref-name TM-1 --query-name Jin668] [--dry-run]
"""
import argparse
import json
import os
import sys
import django

# 与 manage.py 同目录的 settings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from CottonOGD.models import GenomePair, SyriSR, SyriSeq  # noqa: E402

SR_TYPES = {"SYN", "INV", "TRANS", "INVTR", "DUP", "INVDP"}
SEQ_TYPES = {"HDR", "TDM", "CPG", "CPL"}


def parse_summary(path):
    """粗略解析 syri.summary 为结构化 dict（分 Structural / Sequence 两块）。"""
    if not path or not os.path.exists(path):
        return None
    out = {"structural": [], "sequence": []}
    section = None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if line.startswith("#Structural"):
                section = "structural"
                continue
            if line.startswith("#Sequence"):
                section = "sequence"
                continue
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t")
            if len(parts) < 4:
                continue
            try:
                out[section].append({
                    "type": parts[0],
                    "count": int(parts[1]),
                    "len_ref": parts[2],
                    "len_qry": parts[3],
                })
            except (ValueError, IndexError):
                continue
    return out


def classify(son_type):
    if son_type in SR_TYPES:
        return "SR"
    if son_type in SEQ_TYPES:
        return "SEQ"
    return None


def load_syri_out(path, ref_genome_id, query_genome_id):
    sr_rows, seq_rows = [], []
    skipped = 0
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for ln, line in enumerate(fh, 1):
            if not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 12:
                skipped += 1
                continue
            (ref_chr, r_s, r_e, ref_seq, alt_seq, qry_chr, q_s, q_e,
             event_id, parent, son_type, copygain) = cols[:12]
            bucket = classify(son_type)
            if bucket is None:
                skipped += 1
                continue
            try:
                r_start, r_end = int(r_s), int(r_e)
                q_start, q_end = int(q_s), int(q_e)
            except ValueError:
                skipped += 1
                continue
            sv_length = r_end - r_start + 1
            base = dict(
                genome_pair_id=None,  # 由调用方回填
                ref_genome_id=ref_genome_id,
                query_genome_id=query_genome_id,
                ref_genome_chr=ref_chr,
                ref_start=r_start,
                ref_end=r_end,
                ref_seq=ref_seq if ref_seq != "-" else None,
                alt_seq=alt_seq if alt_seq != "-" else None,
                query_genome_chr=qry_chr,
                query_start=q_start,
                query_end=q_end,
                event_id=event_id if event_id != "-" else None,
                parent_event=parent if parent != "-" else None,
                son_type=son_type,
                copygain=copygain if copygain not in ("-", "") else None,
                sv_length=sv_length,
            )
            (sr_rows if bucket == "SR" else seq_rows).append(base)
    return sr_rows, seq_rows, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--syri-out", required=True)
    ap.add_argument("--summary", default=None)
    ap.add_argument("--ref-id", type=int, required=True)
    ap.add_argument("--query-id", type=int, required=True)
    ap.add_argument("--ref-name", default="")
    ap.add_argument("--query-name", default="")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.syri_out):
        print(f"ERROR: syri.out not found: {args.syri_out}", file=sys.stderr)
        sys.exit(1)

    syri_rows = load_syri_out(args.syri_out, args.ref_id, args.query_id)
    sr_rows, seq_rows, skipped = syri_rows
    summary_json = parse_summary(args.summary)

    print(f"[syri] SR rows={len(sr_rows)} SEQ rows={len(seq_rows)} skipped={skipped}")

    if args.dry_run:
        print("[syri] dry-run: skipping DB write")
        return

    pair, _ = GenomePair.objects.update_or_create(
        ref_genome_id=args.ref_id,
        query_genome_id=args.query_id,
        defaults={
            "syri_version": "syri",
            "status": "verified",
            "summary_json": summary_json,
        },
    )
    print(f"[syri] genome_pair id={pair.id} ({args.ref_id}x{args.query_id})")

    # 幂等：删旧重导
    n1 = SyriSR.objects.filter(genome_pair_id=pair.id).delete()[0]
    n2 = SyriSeq.objects.filter(genome_pair_id=pair.id).delete()[0]
    print(f"[syri] deleted old SR={n1} SEQ={n2}")

    for r in sr_rows:
        r["genome_pair_id"] = pair.id
    for r in seq_rows:
        r["genome_pair_id"] = pair.id

    SyriSR.objects.bulk_create([SyriSR(**r) for r in sr_rows], batch_size=2000)
    SyriSeq.objects.bulk_create([SyriSeq(**r) for r in seq_rows], batch_size=2000)
    print(f"[syri] imported SR={len(sr_rows)} SEQ={len(seq_rows)} OK")


if __name__ == "__main__":
    main()
