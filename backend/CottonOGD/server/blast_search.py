"""
本地方案：BLAST+
"""
import time, tempfile, os, subprocess, re
from CottonOGD.server.base3D import BaseSearcher, SearchResult, HitItem, SearchMethod
from django.conf import settings

class BLASTSearcher(BaseSearcher):
    method = SearchMethod.BLAST

    def __init__(self, db_path: str):
        self.db_path = str(db_path)  # 转换为字符串，确保不是PosixPath对象

    def search(self, seq: str, top_n: int = 10,
               evalue: float = 0.001, **kwargs) -> SearchResult:

        start = time.time()

        if not seq or len(seq) < 10:
            raise RuntimeError(f"序列太短或为空: 长度={len(seq) if seq else 0}")

        with tempfile.NamedTemporaryFile("w", suffix=".fasta",
                                         delete=False) as f:
            f.write(f">query\n{seq}\n")
            query_path = f.name

        result_path = query_path + ".out"
        blastp_path = os.path.join(settings.SOFTWARE_DIR, "UNIX", "blast+", "bin", "blastp")
        
        # 使用自定义路径的 blastp，如果不存在则使用系统 blastp
        blastp_exec = blastp_path if os.path.exists(blastp_path) else "blastp"
        
        cmd = [
            blastp_exec,
            "-query", query_path,
            "-db", self.db_path,
            "-evalue", str(evalue),
            "-max_target_seqs", str(top_n),
            "-outfmt", "6 qseqid sseqid evalue bitscore pident qcovs tcovs qstart qend sstart send sseq",
            "-out", result_path,
        ]

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            error_msg = f"BLAST执行失败: {e.stderr}" if e.stderr else f"BLAST执行失败，退出码: {e.returncode}"
            raise RuntimeError(error_msg)

        hits = []
        with open(result_path) as f:
            for line in f:
                parts = line.strip().split("\t")
                # BLAST 2.16 可能不输出 tcovs 或输出为空，所以最少11个字段
                if len(parts) < 11:
                    continue

                target = parts[1]
                # 处理 pdb|xxx|A 格式
                if target.startswith('pdb|'):
                    pdb_part = target.replace('pdb|', '')
                    parts_pdb = pdb_part.split('|')
                    pdb_id = parts_pdb[0].upper()
                    chain = parts_pdb[1] if len(parts_pdb) > 1 else ""
                else:
                    match = re.match(r"^(\d[A-Z0-9]{3})[_\s]?([A-Za-z0-9]*)", target)
                    pdb_id = match.group(1).upper() if match else target[:4].upper()
                    chain = match.group(2) if match else ""

                # 根据字段数量决定 tcovs 的位置
                if len(parts) >= 12:
                    cov_t = float(parts[6]) / 100.0
                    q_start = int(parts[7])
                    q_end = int(parts[8])
                    t_start = int(parts[9])
                    t_end = int(parts[10])
                else:
                    # tcovs 缺失，使用默认值
                    cov_t = 0.0
                    q_start = int(parts[6])
                    q_end = int(parts[7])
                    t_start = int(parts[8])
                    t_end = int(parts[9])

                hits.append(HitItem(
                    rank=len(hits) + 1,
                    pdb_id=pdb_id,
                    chain=chain,
                    evalue=float(parts[2]),
                    bitscore=float(parts[3]),
                    identity=float(parts[4]) / 100.0,
                    cov_q=float(parts[5]) / 100.0,
                    cov_t=cov_t,
                    q_start=q_start,
                    q_end=q_end,
                    t_start=t_start,
                    t_end=t_end,
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
