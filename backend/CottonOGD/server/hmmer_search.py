"""
本地方案：phmmer
适合需要远缘同源检测的场景
"""
import time, tempfile, os, subprocess, re
from .base3D import BaseSearcher, SearchResult, HitItem, SearchMethod


class HMMERSearcher(BaseSearcher):
    method = SearchMethod.HMMER

    def __init__(self, db_path: str):
        self.db_path = db_path  # /data/pdb_local/pdb_seqres.fasta

    def search(self, seq: str, top_n: int = 10,
               evalue: float = 0.001, **kwargs) -> SearchResult:

        start = time.time()

        # 写临时查询文件
        with tempfile.NamedTemporaryFile("w", suffix=".fasta",
                                         delete=False) as f:
            f.write(f">query\n{seq}\n")
            query_path = f.name

        # 输出文件
        tblout_path = query_path + ".tblout"

        # phmmer 命令
        cmd = [
            "phmmer",
            "--tblout", tblout_path,
            "--noali",            # 不输出比对详情（节省 I/O）
            "--E", str(evalue),   # E-value 阈值
            "-N", str(top_n),     # 最多返回 top_n 条
            "--domE", str(evalue),
            query_path,
            self.db_path,
        ]

        subprocess.run(cmd, check=True, capture_output=True)

        # 解析 tblout
        hits = []
        with open(tblout_path) as f:
            for line in f:
                if line.startswith("#"):
                    continue
                parts = line.split()
                if len(parts) < 5:
                    continue

                target = parts[0]        # e.g. "1TUP_A"
                evalue_hit = float(parts[4])
                bitscore = float(parts[5])

                # 提取 PDB ID 和链
                match = re.match(r"^(\d[A-Z0-9]{3})[_\s]?([A-Za-z0-9]*)", target)
                pdb_id = match.group(1).upper() if match else target[:4].upper()
                chain = match.group(2) if match else ""

                hits.append(HitItem(
                    rank=len(hits) + 1,
                    pdb_id=pdb_id,
                    chain=chain,
                    evalue=evalue_hit,
                    bitscore=bitscore,
                    raw_target=target,
                ))

        # 清理
        for f_path in [query_path, tblout_path]:
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
