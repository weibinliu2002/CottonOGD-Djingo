"""
本地方案：MMseqs2（速度最快，推荐用于大批量）
"""
import time, tempfile, os, subprocess, re
from .base3D import BaseSearcher, SearchResult, HitItem, SearchMethod


class MMseqs2Searcher(BaseSearcher):
    method = SearchMethod.MMSEQS2

    def __init__(self, db_path: str, tmp_dir: str = "/tmp/mmseqs_tmp"):
        self.db_path = db_path  # MMseqs2 格式的数据库路径
        self.tmp_dir = tmp_dir
        os.makedirs(tmp_dir, exist_ok=True)

    def search(self, seq: str, top_n: int = 10,
               evalue: float = 0.001, **kwargs) -> SearchResult:

        start = time.time()

        # 写临时查询文件
        with tempfile.NamedTemporaryFile("w", suffix=".fasta",
                                         delete=False, dir=self.tmp_dir) as f:
            f.write(f">query\n{seq}\n")
            query_path = f.name

        result_path = os.path.join(self.tmp_dir, f"result_{os.getpid()}.m8")
        tmp_prefix = os.path.join(self.tmp_dir, f"tmp_{os.getpid()}")

        cmd = [
            "mmseqs", "easy-search",
            query_path,
            self.db_path,
            result_path,
            tmp_prefix,
            "--format-output",
            "query,target,evalue,bits,pident,qcov,tcov,qstart,qend,tstart,tend",
            "--max-seqs", str(top_n),
            "-e", str(evalue),
        ]

        subprocess.run(cmd, check=True, capture_output=True)

        # 解析 m8 格式
        hits = []
        with open(result_path) as f:
            for line in f:
                parts = line.strip().split("\t")
                if len(parts) < 11:
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
                    identity=float(parts[4]) / 100.0,  # mmseqs 输出是百分比
                    cov_q=float(parts[5]) / 100.0,
                    cov_t=float(parts[6]) / 100.0,
                    q_start=int(parts[7]),
                    q_end=int(parts[8]),
                    t_start=int(parts[9]),
                    t_end=int(parts[10]),
                    raw_target=target,
                ))

        # 清理
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
