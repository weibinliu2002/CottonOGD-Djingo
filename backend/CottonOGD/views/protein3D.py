# 你的 views.py
import hashlib
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

# 导入序列化器（用上一条消息里的定义）
from CottonOGD.server.serializers import SearchRequestSerializer
# 导入模型
from CottonOGD.models import SearchCache
# 导入统一基类和具体方法
from CottonOGD.server.base3D import SearchMethod
from CottonOGD.server.rcsb_search import RCSBSearcher
from CottonOGD.server.hmmer_search import HMMERSearcher
from CottonOGD.server.mmseqs_search import MMseqs2Searcher
from CottonOGD.server.blast_search import BLASTSearcher

# ---------------------------------------------
# 1. 初始化搜索器（放在函数外面，服务启动时只加载一次）
# ---------------------------------------------
SEARCHERS = {
    SearchMethod.RCSB_API: RCSBSearcher(),
    # 注意：替换成你服务器上真实的路径
    SearchMethod.HMMER:    HMMERSearcher("/data/pdb_local/pdb_seqres.fasta"),
    SearchMethod.MMSEQS2:  MMseqs2Searcher("/data/pdb_local/pdb_seqres_db"),
    SearchMethod.BLAST:    BLASTSearcher("/data/pdb_local/pdb_seqres_blastdb"),
}

# ---------------------------------------------
# 2. 辅助函数：清理 FASTA 序列
# ---------------------------------------------
def _clean_sequence(raw: str) -> str:
    lines = raw.strip().splitlines()
    return "".join([l.strip() for l in lines if not l.startswith(">")]).upper()


# ---------------------------------------------
# 3. 核心搜索接口 (对应你的 geneid_summary 风格)
# ---------------------------------------------
@api_view(['POST'])
def search_similar_structure(request):
    """
    接收序列，根据选择的方法返回相似的 PDB 结构
    """
    # 1. 校验前端传来的参数
    serializer = SearchRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
    
    req_data = serializer.validated_data
    seq = _clean_sequence(req_data['sequence'])
    method = req_data['method']

    # 2. 查缓存 (如果开启)
    if req_data['use_cache']:
        seq_hash = hashlib.md5(seq.encode()).hexdigest()
        cache_obj = SearchCache.objects.filter(seq_hash=seq_hash, method=method.value).first()
        if cache_obj:
            result_data = cache_obj.result_json
            result_data['from_cache'] = True  # 标记来自缓存，前端可以展示个小闪电⚡
            return Response(result_data)

    # 3. 执行搜索（核心逻辑）
    searcher = SEARCHERS.get(method)
    if not searcher:
        return Response({"error": "不支持的方法"}, status=400)

    try:
        # 调用我们写好的统一接口，无论是云端还是本地，返回格式都一样
        search_result = searcher.search(
            seq=seq,
            top_n=req_data['top_n'],
            evalue_cutoff=req_data['evalue'],
            identity_cutoff=req_data['identity_cutoff'],
        )
        result_data = search_result.to_dict()
    except Exception as e:
        # 捕获本地命令行执行报错（比如 mmseqs 路径不对）
        return Response({"error": f"比对执行失败: {str(e)}"}, status=500)

    # 4. 写入缓存
    if req_data['use_cache']:
        seq_hash = hashlib.md5(seq.encode()).hexdigest()
        SearchCache.objects.update_or_create(
            seq_hash=seq_hash,
            method=method.value,
            defaults={'result_json': result_data}
        )

    # 5. 返回统一格式的 JSON 给前端
    return Response(result_data)


# ---------------------------------------------
# 4. 获取方法列表接口
# ---------------------------------------------
@api_view(['GET'])
def get_search_methods(request):
    """
    返回前端下拉菜单需要的数据
    """
    methods = [
        {"id": "rcsb_api", "name": "RCSB 云端搜索", "description": "推荐，无需本地库，秒出结果", "is_local": False},
        {"id": "hmmer", "name": "HMMER 本地", "description": "远缘同源检测更强，需本地库", "is_local": True},
        {"id": "mmseqs2", "name": "MMseqs2 本地", "description": "速度最快，适合大批量，需本地库", "is_local": True},
        {"id": "blast", "name": "BLAST 本地", "description": "经典方法，需本地库", "is_local": True},
    ]
    return Response({"methods": methods})
