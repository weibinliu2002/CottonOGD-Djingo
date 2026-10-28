# CottonOGD 现状审计报告

审计范围：`Script/`、`Script/CottonOGD/`、`Script/snakemake/`、`backend/scripts/`、
`backend/CottonOGD/models.py`、MySQL、Redis、`backend/data/`、`backend/static/jbrowse/`。
本报告只记录现状与本次改造依据，不包含任何删除/写入操作。

## 1. 脚本位置核实

| 能力 | 实际路径 | 备注 |
|---|---|---|
| 最长蛋白 | `~/bin/longest_protein_by_gene.py` | 用户指定，流程直接调用，未重写 |
| 旧最长转录本 | `Script/script/longest.R` | 仅按 `.\d+` 去后缀，无 GFF 映射 |
| LAI 主流程 | `Script/CottonOGD/LAI/LAI.sh` | **不存在** `LAI,Genome_size/` 目录（无逗号） |
| Genome size | `Script/CottonOGD/LAI/Genome_size/Genome_size.R` | `sum(width(genome))` |
| LAI 汇总 | `Script/CottonOGD/LAI/result/LAI_summary.R` | 取 `whole_genome` 行 |
| BUSCO | `Script/CottonOGD/busco/busco.sh` + `busco_summary.R` | 蛋白模式、`--augustus --long --offline` |
| eggNOG | `Script/CottonOGD/eggnog_annoation/emapper.sh` | `emapper.py -m mmseqs ...` |
| eggNOG/GO 解析 | `Script/CottonOGD/eggnog_annoation/eggnog/parse_eggNOG.py` → `/public2/wbliu/data/CottonOGD/Script/parse_eggNOG.py` | 软链接到外部生产脚本 |
| GO OBO 过滤 | `.../eggnog/parse_go_obofile.py` | 生成 `GO, Description, level` 表 |
| UniProt 解析 | `/data/wbliu/data/CottonOGD/Function/uniprot/unipro_annotation.py` | BLAST `best_hits.m8` + Swiss-Prot header |
| iTAK 入库 | `Script/script/import_itak_to_genefamily.py` | 旧脚本会 `TRUNCATE genefamily`，新流程禁用该行为 |
| 序列提取 | `Script/snakemake/extract_seq.R`、`Script/script/extract_seq.R` | upstream/downstream 打印 20000 实际执行 2000 |
| 旧 Snakefile | `Script/snakemake/Snakefile` | 未纳入根流程，保留作参考 |
| GFF 修复 | `Script/snakemake/fix_gff.sh` | 交换坐标、排序、bgzip/tabix |
| JBrowse | `backend/static/jbrowse/add_jbrowes.sh`、`update_config_paths.py`、`set_default_tracks.py` | `CAT_CMD` 存在字面量 bug |
| BLAST 建库 | `Script/script/add_blast_db.sh` | 旧 Snakefile 路径写成 `blastdb`，实际为 `blast_db` |
| GO/KEGG track | `backend/scripts/build_gokegg_tracks.py` | 读取外部 emapper 结果，生成 4 个 track |
| 旧序列入库 | `Script/snakemake/import_sequences_to_geneseq.py` | 由 `db_upload.py` 替代 |

## 2. 旧 Snakefile 规则与处理方式

| 旧 rule | 现状/缺陷 | 新流程 |
|---|---|---|
| `add_jbrowse` | 只调用 `fix_gff.sh`；真正 `add_jbrowes.sh` 被注释；`CAT_CMD` 有 bug | `rule jbrowse` + `rule jbrowse_tracks` |
| `extract_mrna/cdna/cds/pro` | 四条独立 `gffread` | 合并为 `rule extract_sequences` |
| `extract_gene_genome` | 依赖 R/`.fai` | Python `extract_gene_genome` 逻辑并入 `extract_sequences` |
| `extract_upstream/downstream` | TBtools，真实长度 2000 | `gffread -u --w-add 20000` + `split_flanks.py` |
| `extract_longest_fa` | 仅 pro，调用 `longest.R` | `longest_protein/cds/mrna`，调用用户脚本 |
| `makeblast` | `blastdb` 路径错误；cds/mrna longest 无生产规则 | `rule build_blast_db`，修正路径并补齐输入 |
| `add_Species_info` 等入库规则 | 分散、ID 映射错误、无事务 | `db_upload.py` 单事务/幂等 |
| `prepare_annotation/uniprot/interproscan/eggno/result_egg` | 跨物种合并 + 注释 | 新 `annotation` 分支，按物种隔离 |
| `run_busco/run_lai` | 参数基本可用 | `workflow/scripts/qc/` 复制并参数化 |
| `parrel` | 拼写错误/空规则 | `aggregate_report` |

## 3. 数据库现状（MySQL `cottonogd-ortho`）

- 表结构由 `backend/CottonOGD/models.py`（Django）控制；审计时
  `makemigrations --check --dry-run` 返回 `No changes detected`。
- 审计时最新迁移为 `0053_gene_kegg_pathway.py`。
- `species` 258 行；`genemaster` 17,224,325 行。
- `species` 现有列：
  `id, name, Cotton_Species, Genome_type, Category, Accession, Ploidy,
  Assembling_institution, Website, Article, LAI_value, Busco, Genome_size,
  description, alias`。
  - **已有** `Ploidy / LAI_value / Busco / Genome_size`，无需新增。
  - **缺少** `common_name / assembly_version / annotation_version / submitter`
    以及文献/QC/上传状态表。
- `annotation_source` 15 行：`uniprot, pfam, smart, eggnog, prosite, prints,
  funfam, superfamily, cdd, gene3d, hamap, panther, pirsf, sfld, tigrfams`；
  **缺 `interproscan`**。
- `gene_go.id_id`、`gene_kegg.id_id`、`gene_annotation.id_id` 必须是
  `genemaster.id`；旧脚本部分分支误用 `transcriptmaster.id`。
- `gene_kegg.pathway_id` 为 5 位（如 `00010`）；emapper/旧解析输出
  `map00010`，入库前必须去 `map`。
- `genefamily.id_id` 是 `genemaster.id` 的 OneToOne；旧 iTAK 导入会
  `TRUNCATE` 全表，新流程按物种 upsert。

### 3.1 外键/键值类型（入库必须遵守）

| 表/列 | 实际目标 |
|---|---|
| `genemaster.genome_id` | `species.name`（字符串，不是数字 id） |
| `transcriptmaster.genome_id` | `species.id` |
| `gene_seq.genome_id` | `species.id` |
| `genefamily.genome_id` | `species.id` |
| `gene_annotation.genome_id` | `species.id` |
| `gene_go.id_id` / `gene_kegg.id_id` / `gene_annotation.id_id` | `genemaster.id` |
| `species_qc.species_id` / `species_literature.species_id` / `species_upload_state.species_id` | `species.name` |

`genemaster` 还包含 Django `auto_now_add` 的 `created_at NOT NULL`，
`species_qc`/`species_literature` 的 `created_at`、`species_upload_state`
的 `updated_at` 也是 `NOT NULL`；`db_upload.py` 用原始 SQL 写入时显式填值。

### 3.2 本次新增的 Django 迁移（只生成，不执行）

| 迁移 | 内容 |
|---|---|
| `0054_add_species_metadata_and_qc.py` | `species` 新增 4 列；新增 `species_literature`、`species_qc`、`species_upload_state` |
| `0055_add_interproscan_source.py` | `annotation_source` 增加 `interproscan` 行 |

SQL 输出：

- `workflow/sql/0054_plan.sql`
- `workflow/sql/0055_plan.sql`

> 未执行 `migrate`。执行前需另行确认并备份。

## 4. 文本 ER 关系（与入库相关）

```
species 1 ─── N genemaster 1 ─── N transcriptmaster
   │                │ 1
   │                ├── N gene_seq
   │                ├── N gene_go        ── N:1 go_term
   │                ├── N gene_kegg      ── N:1 ko_term / metabolic_pathway
   │                ├── 1 genefamily
   │                └── N gene_annotation ── N:1 annotation_source
   │                                      └── N:1 annotation_detail
   ├── N species_literature        (new)
   ├── N species_qc                (new, unique species+annotation_version)
   └── N species_upload_state      (new, unique species+annotation_version)
```

## 5. 数据目录与命名约定（保持不变）

```
backend/data/genome/{species}/          # 按物种分类，软链接
    {species}.genome.fa.gz -> ../../Genome/genome/{species}.genome.fa.gz
    {species}.gff.gz       -> ../../Genome/gff/{species}.gff.gz
    ...（cds/pro/cdna/mrna/gene/upstream/downstream/longest）

backend/data/Genome/{type}/             # 按类型分类，真实文件
    genome/ gff/ cds/ pep/ cdna/ mrna/ gene/ upstream/ downstream/
```

- 现有物种目录中同时存在少量原始文件（如 `N269.fa`）与软链接；新流程
  只新增/更新软链接，不移动、不删除原始文件。
- `DownloadGenome.py` 需要以下物种级文件：
  `{s}.genome.fa.gz`、`{s}.gene_genome.fa.gz`、`{s}.cds.fa.gz`、
  `{s}.pro.fa.gz`、`{s}.upstream.fa.gz`、`{s}.gff.gz`。
  现有部分物种缺少 `.gz` 版本，`publish` 规则会按需生成。
- BLAST 库实际路径：
  `backend/data/blast_db/CottonOGD/{species}/{genome,mrna,cds,protein}/{species}.*`
- JBrowse 数据：`backend/static/jbrowse/data/{species}/config.json`；
  大文件由 `/jbrowse/large/{species}/{file}`（`views/jbrowes_file.py`）提供。
- GO/KEGG/TE track 真实文件：`backend/data/gokegg_track/{species}/`，
  软链到 JBrowse 目录。

## 6. 工具与路径（已实测）

| 工具 | 路径/版本 |
|---|---|
| Snakemake | 9.6.2，`/data/wbliu/soft/home/.conda/envs/snakemake/bin/snakemake` |
| 后端 Python | `backend/venv/bin/python`（PyMySQL/YAML/pandas/Bio/redis/Django） |
| BUSCO | 5.8.2，`/data/wbliu/soft/home/.conda/envs/busco/bin/busco` |
| BUSCO lineage | `/data/wbliu/data/CottonOGD/busco/busco_downloads/lineages/eudicots_odb10` |
| eggNOG-mapper | 2.1.13，`.../eggnog-mapper-2.1.13/emapper.py`（需 `PYTHONPATH=.../eggnog-mapper-2.1.13`） |
| iTAK | 2.0.2，`python iTAK.py <proteins> -o <out> -p <threads>` |
| InterProScan | 5.77，`.../interproscan-5.77-108.0/interproscan.sh` |
| UniProt DB | BLAST 库 `/public2/wbliu/data/pfam_data/uniprot/uniprot`；FASTA `uniprot_sprot.fasta` |
| BLAST+ | `backend/soft/UNIX/blast+/bin/{blastp,makeblastdb}` |
| bgzip/tabix/samtools | `/usr/local/bin/` |
| JBrowse CLI | 3.7.0，`/home/web/.npm-global/bin/jbrowse` |
| gffread | `/home/web/bin/gffread` |

## 7. Redis 与缓存

- Redis 4.6.0（django-redis），配置在 `backend/.env` 与 `mysite/settings.py`。
- 与基因集/组织表达相关的 key 由 `cache_models.py`、`build_genesets` 管理；
  典型前缀：`tissues:*`、`genomes_with_tissue`、`geneset:*`。
- `db_upload.py` 在事务提交后按物种清理上述 key；dry-run 不清理。

## 8. 主要风险

| 风险 | 状态/应对 |
|---|---|
| 17.2M `genemaster` 大表 | 单物种事务 + 分批 `executemany`；不使用全表 DDL |
| `gene_go/gene_kegg/gene_annotation/gene_seq` 无唯一约束 | overwrite 按物种删除；skip 直接跳过；不依赖唯一键 |
| 旧 GO/KEGG 解析 ID 映射 | 统一用 GFF gene 解析 + `genemaster.id` |
| iTAK TRUNCATE | 新流程禁止；按物种 upsert |
| KEGG `map` 前缀 | 入库时归一化；GO/KEGG track 保留 `map` |
| BUSCO/LAI 资源大 | 资源声明；LAI 依赖 LTR 产物 |
| 已存在真实文件被覆盖 | `publish.overwrite=false` 默认跳过并 warning |
| Django migration 未执行 | `db_upload.py` 检测缺表/缺列并写入 warning，不执行 DDL |