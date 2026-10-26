"""
序列统一提取层：pysam（htslib，与 samtools faidx 同源）+ 句柄 LRU 缓存。

- 基因组坐标型序列：data/Genome/genome/{genome}.genome.fa.gz（.fai/.gzi 已就绪）
- 拼接产物型序列（cdna/cds/pep/mrna/...）：data/Genome/{type}/{genome}.{type}.fa.gz
  部分物种/类型尚未建立 faidx 索引，此时返回 None，由调用方回退 gene_seq 表（备用）。

坐标约定：GFF 1-based inclusive -> htslib 0-based half-open。
"""
import logging
from functools import lru_cache

import pysam
from django.conf import settings

logger = logging.getLogger(__name__)

GENOME_ROOT = settings.BASE_DIR / 'data' / 'Genome'

# gene_type（gene_seq 表用名）-> (子目录, 文件名模板)；'pro' 对应 pep 目录
SEQ_TYPE_FILES = {
    'genome': ('genome', '{genome}.genome.fa.gz'),
    'cdna': ('cdna', '{genome}.cdna.fa.gz'),
    'cds': ('cds', '{genome}.cds.fa.gz'),
    'pro': ('pep', '{genome}.pro.fa.gz'),
    'mrna': ('mrna', '{genome}.mrna.fa.gz'),
    'upstream': ('upstream', '{genome}.upstream.fa.gz'),
    'downstream': ('downstream', '{genome}.downstream.fa.gz'),
}

_COMPLEMENT = str.maketrans('ACGTNacgtnRYKMSWBDHVrykmswbdhv',
                            'TGCANtgcanYRMKSWVHDByrmkswvhdb')


@lru_cache(maxsize=60)  # 只保留最近 60 个已打开的基因组/产物文件句柄
def _open_fasta(path: str):
    try:
        return pysam.FastaFile(path)
    except (OSError, ValueError):
        # .fa.gz 缺 .fai/.gzi，或文件不存在
        return None


def _fasta_for(genome: str, gene_type: str):
    entry = SEQ_TYPE_FILES.get(gene_type)
    if not entry:
        return None
    subdir, template = entry
    return _open_fasta(str(GENOME_ROOT / subdir / template.format(genome=genome)))


def _revcomp(seq: str) -> str:
    return seq.translate(_COMPLEMENT)[::-1]


def fetch_by_id(genome: str, gene_type: str, seq_id: str):
    """按序列 ID 从产物文件整条提取；文件/索引/ID 任一不可用返回 None。"""
    fa = _fasta_for(genome, gene_type)
    if fa is None or seq_id not in fa.references:
        return None
    try:
        return fa.fetch(seq_id)
    except (KeyError, ValueError):
        return None


def fetch_region(genome: str, seqid: str, start: int, end: int, strand: str = '+'):
    """按基因组坐标提取（1-based inclusive）；文件不可用返回 None。"""
    fa = _fasta_for(genome, 'genome')
    if fa is None or seqid not in fa.references:
        return None
    start = max(1, int(start))
    end = min(int(end), fa.get_reference_length(seqid))
    if end < start:
        return None
    try:
        seq = fa.fetch(seqid, start - 1, end)
    except (KeyError, ValueError):
        return None
    return _revcomp(seq) if strand == '-' else seq
