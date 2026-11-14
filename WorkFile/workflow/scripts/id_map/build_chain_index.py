#!/usr/bin/env python3
"""Build the unified chain index table from validated chain outputs.

Reads per-pair validation.tsv files plus registry data and emits a single
chain_index.tsv ready to be consumed by the CottonOGD web service.
"""
import argparse
import csv
import os
import re


def load_registry(path):
    reg = {}
    if not os.path.exists(path):
        return reg
    with open(path, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            reg[row["genome_id"]] = row
    return reg


def main():
    parser = argparse.ArgumentParser(description="Build chain index")
    parser.add_argument("--registry", required=True, help="genome_registry.tsv")
    parser.add_argument("--pairs-tsv", required=True, help="liftover pairs TSV")
    parser.add_argument("--chain-root", required=True, help="results/id_map/chain")
    parser.add_argument("--intermediate-root", required=True, help="results/id_map/intermediate")
    parser.add_argument("--out", required=True, help="chain_index.tsv")
    parser.add_argument("--nflo-version", default="1.8.8")
    parser.add_argument("--aligner", default="lastz")
    args = parser.parse_args()

    registry = load_registry(args.registry)

    rows = []
    with open(args.pairs_tsv, "r", encoding="utf-8") as fh:
        for pair in csv.DictReader(fh, delimiter="\t"):
            src = pair["source_id"]
            tgt = pair["target_id"]
            species = pair["species"]

            src_reg = registry.get(src, {})
            tgt_reg = registry.get(tgt, {})

            # Determine ploidy of both
            src_tetra = src_reg.get("ploidy") == "allotetraploid" or src_reg.get("genome_type", "").startswith("AD")
            tgt_tetra = tgt_reg.get("ploidy") == "allotetraploid" or tgt_reg.get("genome_type", "").startswith("AD")

            pair_dir = f"{src}_to_{tgt}"

            # Determine subgenome tasks
            if not src_tetra and not tgt_tetra:
                subs = [("Whole", "Whole")]
            elif src_tetra and tgt_tetra:
                subs = [("At", "At"), ("Dt", "Dt")]
            else:
                # Diploid<->tetraploid: map A-diploid->At, D-diploid->Dt
                # Determine source/target genome type
                src_gt = src_reg.get("genome_type", "")
                tgt_gt = tgt_reg.get("genome_type", "")
                # Diploid A -> At
                subs_map = {}
                for side, suffix in (("src", ["At", "Dt"]), ("tgt", ["At", "Dt"])):
                    pass
                # Simplification: build based on which is tetraploid
                # A-genome diploid ↔ At, D-genome diploid ↔ Dt
                subs = []
                for sg in ("At", "Dt"):
                    src_is = src_reg.get("genome_type", "")
                    tgt_is = tgt_reg.get("genome_type", "")
                    # A diploid name ends in A{num}, D diploid in D{num}; AD is tetra
                    def diploid_sub(gt):
                        if gt.startswith("A"): return "At"
                        if gt.startswith("D"): return "Dt"
                        return None
                    src_sub = diploid_sub(src_is) if not src_tetra else sg
                    tgt_sub = diploid_sub(tgt_is) if not tgt_tetra else sg
                    if (src_sub == sg or not src_tetra) and (tgt_sub == sg or not tgt_tetra):
                        subs.append((src_sub, tgt_sub))

            for (src_sub, tgt_sub) in subs:
                sub_label = src_sub  # subgenome column for index (use source sub for chain naming)
                sub_dir = src_sub
                base = os.path.join(args.chain_root, pair_dir, sub_dir)
                chain = os.path.join(base, "liftover.chain")
                net = os.path.join(base, "netfile.net")
                src_fa = os.path.join(args.intermediate_root, pair_dir, f"{src}.{src_sub}.fa"
                                      if src_tetra else f"{src}.Whole.fa")
                tgt_fa = os.path.join(args.intermediate_root, pair_dir, f"{tgt}.{tgt_sub}.fa"
                                      if tgt_tetra else f"{tgt}.Whole.fa")
                val_path = os.path.join(base, "validation.tsv")

                status = "missing"
                if os.path.exists(chain):
                    if os.path.exists(val_path):
                        # Read validation status
                        with open(val_path, "r", encoding="utf-8") as vfh:
                            for vr in csv.DictReader(vfh, delimiter="\t"):
                                status = vr.get("status", "unknown")
                    else:
                        status = "chain_present_unvalidated"

                rows.append({
                    "species": species,
                    "source_id": src,
                    "target_id": tgt,
                    "subgenome": sub_label,
                    "source_fasta": src_fa,
                    "target_fasta": tgt_fa,
                    "chain_path": chain,
                    "net_path": net,
                    "aligner": args.aligner,
                    "nflo_version": args.nflo_version,
                    "status": status,
                })

    fields = ["species", "source_id", "target_id", "subgenome", "source_fasta",
              "target_fasta", "chain_path", "net_path", "aligner", "nflo_version", "status"]
    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)

    ok = sum(1 for r in rows if r["status"] == "OK")
    done = sum(1 for r in rows if "chain" in r["status"] or r["status"] == "OK")
    print(f"chain_index: {len(rows)} rows total; OK={ok}; with-chain={done}")


if __name__ == "__main__":
    main()