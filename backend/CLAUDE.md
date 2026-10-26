# CottonOGD 后端项目

## 项目简介

CottonOGD（Cotton Orthologous Gene Database）是棉属直系同源基因数据库，提供基因搜索、注释、表达分析、序列比对、蛋白结构搜索、共线性分析、AI 对话等功能。

## 技术栈

| 组件 | 版本/说明 |
|------|-----------|
| Django | 5.2.3 |
| ASGI Server | Daphne 4.2.1 |
| 数据库 | MySQL (PyMySQL 1.1.1)，双配置：default(localhost) + server(远程) |
| 缓存/会话 | Redis (django-redis, cached_db session) |
| 搜索引擎 | Meilisearch 0.40.0（genemaster + family 索引） |
| REST API | Django REST Framework 3.16.1 |
| AI/LLM | OpenAI SDK 3.14.0（兼容接口，tool-calling 循环） |
| 生信工具 | biopython, pysam, pyfaidx, pyfastx, rcsb-api, gseapy, bcbio-gff |
| 可视化 | matplotlib, seaborn, Pillow, CairoSVG |

## 目录结构

```
backend/
├── mysite/                    # Django 项目配置（核心区）
│   ├── settings.py            # DB/Redis/Meilisearch/CORS/Middleware
│   ├── urls.py                # 顶层路由
│   └── asgi.py                # ASGI 入口
├── CottonOGD/                 # 主应用
│   ├── models.py              # 全部 ORM 模型（547 行，20+ 类）
│   ├── cache_models.py        # Redis 缓存框架 + GO/KEGG 基因集缓存
│   ├── auth.py                # Token + Cookie 双通道认证
│   ├── signals.py             # GeneMaster → Meilisearch 实时同步
│   ├── urls.py                # API 路由
│   ├── config/
│   │   └── meilisearch_config.py  # Meilisearch 客户端工厂 + 索引注册
│   ├── views/                 # API 视图层（12 个功能模块）
│   │   ├── base.py            # 登录/登出
│   │   ├── base_info.py       # 物种/家族信息
│   │   ├── Meilisearch.py     # 基因搜索 (F1)
│   │   ├── gene_id_result.py  # 基因详情 (F2)
│   │   ├── location_ID.py     # ID 映射 (F2)
│   │   ├── gene_Go.py         # GO 注释/富集 (F3)
│   │   ├── gene_Kegg.py       # KEGG 注释/富集 (F3)
│   │   ├── gene_expression.py # RNA-seq 表达热图 (F4)
│   │   ├── expression_EFP.py  # EFP 伪彩图 (F4)
│   │   ├── extract_seq.py     # 序列提取 (F5)
│   │   ├── extract_seq_from_gff.py  # 坐标序列提取 (F5)
│   │   ├── blast.py           # BLAST+ 搜索 (F6)
│   │   ├── protein3D.py       # 蛋白结构搜索 (F7)
│   │   ├── genome_api.py      # 基因组/共线性/SV (F8)
│   │   ├── jbrowes_file.py    # JBrowse 大文件服务 (F9)
│   │   ├── DownloadGenome.py  # 基因组下载 (F10)
│   │   ├── ai_chat.py         # AI 对话入口 (F11)
│   │   └── primer_design.py   # 引物设计 (F12)
│   ├── server/                # 业务逻辑/服务层
│   │   ├── ai_chat.py         # OpenAI tool-calling 循环 (F11)
│   │   ├── ai_tools.py        # 3 个 LLM 工具定义 (F11)
│   │   ├── annotation_search.py   # 注释查询 (F2)
│   │   ├── Go_kegg_search.py  # GO/KEGG 服务 (F2/F3)
│   │   ├── seq_fetch.py       # 序列获取 (F5)
│   │   ├── base3D.py          # 蛋白搜索基类 (F7)
│   │   ├── rcsb_search.py     # RCSB PDB 搜索 (F7)
│   │   ├── hmmer_search.py    # HMMER 搜索 (F7)
│   │   ├── mmseqs_search.py   # MMseqs2 搜索 (F7)
│   │   ├── blast_search.py    # BLAST 搜索 (F7)
│   │   └── serializers.py     # DRF 序列化器 (F7)
│   └── management/commands/   # 管理命令
│       ├── rebuild_index.py           # 重建 genemaster 索引
│       ├── rebuild_family_index.py    # 重建 family 索引
│       ├── sync_genes.py             # 增量同步 Meilisearch
│       ├── setup_meili_keys.py       # 创建前端 API Key
│       └── build_genesets.py         # 构建基因集缓存
├── scripts/
│   ├── import/                # 数据导入脚本
│   │   ├── batch_import_uniprot.py
│   │   ├── import_annotation_databases.py
│   │   ├── import_eggnog.py
│   │   ├── import_interproscan_databases.py
│   │   └── uniprot_import_all.py
│   ├── bulk_rna_seq_analysis.R  # 普通转录组差异分析（DESeq2，输入 count + 分组）
│   ├── single_cell_analysis.py  # 单细胞转录组分析（scanpy 流程）
│   ├── ppi_analysis.py          # PPI 网络（STRING API + trembl 序列映射）
│   ├── build_gokegg_tracks.py   # GO/KEGG JBrowse track 生成
│   └── verify_import.py       # MySQL/Meilisearch 一致性校验
├── data/                      # 数据目录（大文件，不纳入 git）
├── soft/                      # 外部生信工具（hmmer/mmseq2/blast+/primer3 等）
├── static/                    # 静态文件 + JBrowse
├── temp/                      # 临时任务目录
├── .env                       # 环境变量（不纳入 git）
└── requirements.txt           # Python 依赖
```

## 功能模块速查

| 模块 | API 前缀 | 主要视图文件 |
|------|----------|-------------|
| F1 搜索 | `/CottonOGD_api/search_genes/`, `/CottonOGD_api/search/` | `views/Meilisearch.py` |
| F2 基因详情 | `/CottonOGD_api/geneid_result/`, `/CottonOGD_api/Id_map/` | `views/gene_id_result.py`, `views/location_ID.py` |
| F3 GO/KEGG | `/CottonOGD_api/go_annotation/`, `/CottonOGD_api/kegg_enrichment/` | `views/gene_Go.py`, `views/gene_Kegg.py` |
| F4 表达 | `/CottonOGD_api/extract_expression/`, `/CottonOGD_api/expression_EFP_image/` | `views/gene_expression.py`, `views/expression_EFP.py` |
| F5 序列 | `/CottonOGD_api/extract_seq/`, `/CottonOGD_api/extract_seq_gff/` | `views/extract_seq.py`, `views/extract_seq_from_gff.py` |
| F6 BLAST | `/CottonOGD_api/blast_cmd/` | `views/blast.py` |
| F7 蛋白3D | `/CottonOGD_api/search_similar_structure/` | `views/protein3D.py`, `server/*_search.py` |
| F8 基因组 | `/CottonOGD_api/genome_synteny/`, `/CottonOGD_api/search_by_genome_location/` | `views/genome_api.py` |
| F9 JBrowse | `/jbrowse/large/` | `views/jbrowes_file.py`；GO/KEGG track 见 `scripts/build_gokegg_tracks.py` 和 `.claude/skills/jbrowse-track.md` |
| F10 下载 | `/download_genome/<genome_id>/<file_type>` | `views/DownloadGenome.py` |
| F11 AI对话 | `/CottonOGD_api/ai/chat/` | `views/ai_chat.py`, `server/ai_chat.py`, `server/ai_tools.py` |
| F12 引物 | `/CottonOGD_api/primer_design/` | `views/primer_design.py` |

## 常用命令

```bash
# 激活虚拟环境
source /data/web/CottonOGD/OGD/backend/venv/bin/activate

# 开发服务器
python manage.py runserver 0.0.0.0:8000

# 数据库迁移
python manage.py migrate

# Meilisearch 索引管理
python manage.py rebuild_index --confirm          # 重建 genemaster 索引
python manage.py rebuild_family_index --confirm   # 重建 family 索引
python manage.py sync_genes                       # 增量同步
python manage.py setup_meili_keys                 # 创建前端 API Key
python manage.py build_genesets                   # 构建基因集缓存

# 数据导入
python scripts/import/batch_import_uniprot.py --seq-uniprot <path> --gene-mapping <path>
python scripts/import/import_eggnog.py <eggnog_db>
python scripts/import/import_interproscan_databases.py

# 一致性校验
python scripts/verify_import.py --samples 200

# 生成 JBrowse GO/KEGG 注释 track（全部物种，幂等）
python scripts/build_gokegg_tracks.py
python scripts/build_gokegg_tracks.py --genome <物种名>   # 单物种

# 普通转录组差异分析（R/DESeq2：输入 count 矩阵 + 分组文件）
Rscript scripts/bulk_rna_seq_analysis.R --counts counts.csv --group group.tsv --outdir results/bulk

# 单细胞转录组分析（scanpy：输入 count 矩阵 + 可选细胞分组）
# 依赖：pip install scanpy leidenalg igraph
python scripts/single_cell_analysis.py --counts counts.csv --group cells.tsv --outdir results/sc

# PPI 网络（STRING REST API；基因→UniProt 走 data/genome/function 的 trembl BLAST 表）
python scripts/ppi_analysis.py --genes results/bulk/deg_genes_A_vs_B.txt \
    --genome <物种名> --outdir results/ppi
```

## 环境变量

参见 `.env.example`，关键配置：
- `DJANGO_SECRET_KEY` / `DEBUG`
- `MYSQL_DB_*` — MySQL 连接
- `REDIS_*` — Redis 连接
- `MEILISEARCH_URL` / `MEILISEARCH_MASTER_KEY` / `MEILISEARCH_FRONTEND_API_KEY` — Meilisearch
- `AI_CHAT_API_KEY` / `AI_CHAT_BASE_URL` / `AI_CHAT_MODEL` — AI 对话

## 开发注意事项

- 认证使用自定义 Token + Cookie 双通道（`CottonOGD/auth.py`），非 Django 内置 auth
- Meilisearch 实时同步通过 Django signal（`CottonOGD/signals.py`）post_save/post_delete 触发
- 基因集缓存（富集分析用）存储在 Redis，由 `cache_models.py` 管理
- 视图层多使用 `JsonResponse` 手动构建响应，仅蛋白3D使用 DRF Serializer
- `data/` 和 `soft/` 目录含大文件，不纳入 git
