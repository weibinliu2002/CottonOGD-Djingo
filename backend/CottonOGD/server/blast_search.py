"""
本地方案：BLAST+
"""
import time, tempfile, os, subprocess, re
from CottonOGD.server.base3D import BaseSearcher, SearchResult, HitItem, SearchMethod


class BLASTSearcher(BaseSearcher):
    method = SearchMethod.BLAST

    def __init__(self, db_path: str):
        self.db_path = db_path  # /data/pdb_local/pdb_seqres_blastdb

    def search(self, seq: str, top_n: int = 10,
               evalue: float = 0.001, **kwargs) -> SearchResult:

        start = time.time()

        with tempfile.NamedTemporaryFile("w", suffix=".fasta",
                                         delete=False) as f:
            f.write(f">query\n{seq}\n")
            query_path = f.name

        result_path = query_path + ".out"

        cmd = [
            "blastp",
            "-query", query_path,
            "-db", self.db_path,
            "-evalue", str(evalue),
            "-max_target_seqs", str(top_n),
            "-outfmt", "6 qseqid sseqid evalue bitscore pident qcovs tcovs qstart qend sstart send sseq",
            "-out", result_path,
        ]

        subprocess.run(cmd, check=True, capture_output=True)

        hits = []
        with open(result_path) as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) < 12:
                    continue

                target = parts[1]
                match = re.match(r"^(\d[A-Z0-9]{3})[_\s]?([A-Za-z0-9]*)", target)
                pdb_id = match.group(1).upper() if match else target[:4].upper()
                chain = match.group(2) if match else ""

                hits.append(HitItem(
                    rank=len(hits) + 1,
                    pdb_id=pdb_id,
                    chain=chain,
                    evalue=float(parts[2]),
                    bitscore=float(parts[3]),
                    identity=float(parts[4]) / 100.0,
                    cov_q=float(parts[5]) / 100.0,
                    cov_t=float(parts[6]) / 100.0,
                    q_start=int(parts[7]),
                    q_end=int(parts[8]),
                    t_start=int(parts[9]),
                    t_end=int(parts[10]),
                    raw_target=target,
                ))

        for f_path in [query_path, result_path]:
            try:
                os.unlink(f_path)
            except Exception:
                pass

        elapsed = time.time() - start
        return SearchResult(
            method=self.method,
            query_id="",
            top_hits=hits,
            total_hits=len(hits),
            time_elapsed=elapsed,
        )
