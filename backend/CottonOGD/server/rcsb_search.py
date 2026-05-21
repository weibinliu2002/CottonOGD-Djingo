"""
云端方案：使用 rcsb-api 的 SeqSimilarityQuery
让 RCSB 服务器帮你做序列比对
"""
import time
# 延迟导入 rcsbapi，避免模块加载时依赖外部服务
# from rcsbapi.search import SeqSimilarityQuery
from CottonOGD.server.base3D import BaseSearcher, SearchResult, HitItem, SearchMethod


class RCSBSearcher(BaseSearcher):
    method = SearchMethod.RCSB_API

    def search(self, seq: str, top_n: int = 10,
               evalue_cutoff: float = 0.001,
               identity_cutoff: float = 0.0,
               **kwargs) -> SearchResult:

        start = time.time()

        # 延迟导入 SeqSimilarityQuery
        from rcsbapi.search import SeqSimilarityQuery
        query = SeqSimilarityQuery(
            seq,
            evalue_cutoff=evalue_cutoff,
            identity_cutoff=identity_cutoff,
            sequence_type="protein",
        )

        # 使用 "polymer_entity" 返回链级别结果
        # 返回值形如: ["1TUP_1", "2ABC_1", "2ABC_2", ...]
        hits = []
        seen_pdb = set()       # 去重用

        for poly_id in query("polymer_entity"):
            # poly_id 格式: "1TUP_1" → PDB=1TUP, 实体编号=1
            parts = poly_id.split("_")
            pdb_id = parts[0].upper()
            entity_num = parts[1] if len(parts) > 1 else ""

            # 去重：同一个 PDB ID 只取首次命中
            if pdb_id in seen_pdb:
                continue
            seen_pdb.add(pdb_id)

            hits.append(HitItem(
                rank=len(hits) + 1,
                pdb_id=pdb_id,
                chain=entity_num,
                raw_target=poly_id,
            ))

            if len(hits) >= top_n:
                break

        elapsed = time.time() - start

        return SearchResult(
            method=self.method,
            query_id="",
            top_hits=hits,
            total_hits=len(list(query("polymer_entity"))),
            time_elapsed=elapsed,
        )


# searcher/rcsb_search.py 中添加另一个方法
import requests

RCSB_SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"

def search_rcsb_with_scores(seq: str, top_n: int = 10,
                            evalue: float = 0.001,
                            identity: float = 0.0):
    """
    用 RCSB Search API v2 的 sequence terminal service
    可以返回更丰富的比对信息
    """
    query_json = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "sequence",
                    "parameters": {
                        "target": "pdb_chain",
                        "value": seq,
                        "evalue_cutoff": evalue,
                        "identity_cutoff": identity,
                        "sequence_type": "protein",
                    }
                }
            ]
        },
        "return_type": "polymer_entity",
        "request_options": {
            "results_content_type": "experimental",
            "return_all_hits": False,
            "pager": {
                "start": 0,
                "rows": top_n
            },
            "scoring_strategy": "combined",
        }
    }

    response = requests.post(RCSB_SEARCH_URL, json=query_json)
    data = response.json()

    hits = []
    for i, item in enumerate(data.get("result_set", [])):
        identifier = item.get("identifier", "")  # e.g. "1TUP_1"
        score = item.get("score", 0)
        parts = identifier.split("_")
        pdb_id = parts[0].upper() if parts else identifier
        chain = parts[1] if len(parts) > 1 else ""

        hits.append(HitItem(
            rank=i + 1,
            pdb_id=pdb_id,
            chain=chain,
            bitscore=score,
            raw_target=identifier,
        ))

    return hits
