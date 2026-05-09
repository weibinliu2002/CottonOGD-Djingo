"""
所有比对方法的统一接口
核心：每个方法都必须返回 UnifiedResult
"""
from dataclasses import dataclass, field, asdict
from typing import List
from enum import Enum


class SearchMethod(str, Enum):
    RCSB_API = "rcsb_api"
    HMMER = "hmmer"
    MMSEQS2 = "mmseqs2"
    BLAST = "blast"
    
    @classmethod
    def choices(cls):
        return [(item.value, item.name) for item in cls]


@dataclass
class HitItem:
    rank: int
    pdb_id: str          # 如 "1TUP"
    chain: str = ""      # 如 "A"
    evalue: float = 999.0
    bitscore: float = 0.0
    identity: float = 0.0 # 序列一致性比例 (0~1)
    description: str = ""
    cov_q: float = 0.0   # query 覆盖率
    cov_t: float = 0.0   # target 覆盖率
    q_start: int = 0
    q_end: int = 0
    t_start: int = 0
    t_end: int = 0
    raw_target: str = ""  # 原始 target 名，方便调试


@dataclass
class SearchResult:
    method: SearchMethod
    query_id: str
    top_hits: List[HitItem] = field(default_factory=list)
    total_hits: int = 0
    time_elapsed: float = 0.0

    def to_dict(self):
        return {
            "query_id": self.query_id,
            "method": self.method.value,
            "top_hits": [asdict(h) for h in self.top_hits],
            "total_hits": self.total_hits,
            "time_elapsed": round(self.time_elapsed, 3),
        }


class BaseSearcher:
    """所有比对方法必须继承此类，实现 search 方法"""
    method: SearchMethod

    def search(self, seq: str, top_n: int = 10, **kwargs) -> SearchResult:
        raise NotImplementedError
