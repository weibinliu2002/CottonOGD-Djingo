# CottonOGD 统一基因组处理流程

根目录 `Snakefile` 负责 DAG 编排；所有命令与解析脚本位于 `workflow/scripts/`，
参数集中在 `config.yaml` / `samples.yaml` / `metadata.yaml`。旧 `Script/`
目录保留作参考，不被新流程修改。

## 1. 安装与环境

```bash
# Snakemake（已安装版本 9.6.2）
/data/wbliu/soft/home/.conda/envs/snakemake/bin/snakemake --version

# 后端 Python（PyMySQL/PyYAML/pandas/Biopython/pyfaidx/pysam/redis/Django）
/data/web/CottonOGD/OGD/backend/venv/bin/python -V
```

外部工具在 `config.yaml` 的 `tools:` 中配置，包括：

- `longest_protein_by_gene.py`（用户指定，最长蛋白/转录本）
- `gffread`、`samtools`、`bgzip`、`tabix`
- `busco` + `busco_lineage_dir`
- `LTR_FINDER_parallel` / `gt` / `LTR_retriever` / `LAI`
- `emapper.py`（eggNOG-mapper 2.1.13）
- `iTAK.py`、`interproscan.sh`、`blastp`、`makeblastdb`
- `jbrowse` CLI
- 可选 `EDTA.pl`

eggNOG-mapper 需要把其目录加入 `PYTHONPATH`；`run_eggnog.sh` 已自动设置。

数据库/Redis 凭据只从环境变量或 `backend/.env` 读取，不写入 `config.yaml`。
首次使用时：

```bash
cp backend/.env.example backend/.env
# 编辑 backend/.env 中的 MYSQL_DB_HOST/USER/PASSWORD/NAME 和 REDIS_*
```

如需从零搭建环境（版本仅作示例，实际以服务器已安装版本为准）：

```bash
conda create -n cottonogd -c conda-forge -c bioconda \
  python=3.12 snakemake=9.6.2 gffread samtools htslib blast busco
conda activate cottonogd
pip install -r backend/requirements.txt
# iTAK / LTR_FINDER_parallel / LTR_retriever / LAI / EDTA / InterProScan
# 按各自上游文档安装，然后把可执行文件路径写入 config.yaml 的 tools:。
```

`backend/requirements.txt` 含一个 `git+ssh` 依赖，需要能访问对应 GitHub 仓库；
已有 `backend/venv` 可直接使用，无需重复安装。

## 2. 准备输入

每个物种一个目录，详见 `input_spec.md`：

```
data/{species}/
├── genome.fasta
├── genes.gff3          # 也接受 genes.gtf（自动经 gffread 转为 GFF3 后再校验）
├── proteins.fasta      # 可选
├── transcripts.fasta   # 可选
├── cds.fasta           # 可选
└── metadata.yaml
```

批量清单 `samples.yaml`：

```yaml
samples:
  - id: Gossypium_hirsutum
    enabled: true
    genome: data/Gossypium_hirsutum/genome.fasta
    gff: data/Gossypium_hirsutum/genes.gff3
    metadata: data/Gossypium_hirsutum/metadata.yaml
```

`metadata.template.yaml` 可直接复制修改；`genome_size/LAI/BUSCO` 由流程计算，
不要手填。GTF 或“只有转录本行”的 GFF3 会按 `gene_id`/`geneID` 自动补出
`gene` 行，后续最长蛋白、序列提取、JBrowse 与入库均按 gene 聚合。

### 2.1 序列 ID 兼容

历史数据的 GFF 与 genome 常出现命名不一致，例如 GFF 使用 `At_01`、genome
使用 `At_01_Bar32`；或 GFF 使用 `A01`、genome 使用 `At01_HAU-AD2_v1.0`。
`validate_input.py` 与 `prepare_gff.py` 会按以下顺序做**唯一**匹配：

1. 完全相同的 seqid；
2. 唯一的前缀别名（`At_01` → `At_01_Bar32`）；
3. 染色体标签（`A01`/`At_01`/`GhirP_A01` → `At01_...` 或
   `CM045499.1 ... chromosome A01 ...`）。

匹配成功后会写 warning 并在 `prepare_gff` 阶段把 GFF seqid 改写为 genome
seqid，保证 gffread、JBrowse、BLAST 使用同一套坐标名。无法唯一匹配的
contig 会被丢弃并记录 warning（例如 GFF 中保留了未挂载 scaffold）；如果
所有 gene/mRNA 都无法匹配，则仍以 exit code 2 失败，避免悄悄产出空结果。

部分历史 `{species}.gff` 只有 `##gff-version 3`，真实注释在同名 `.gff.gz`
中；`build_species_manifest.py` 会检查文件内容，自动选择非空的 GFF。

### 2.2 从 MySQL 已有物种生成批量清单

已有 `species` 表的物种可以一键生成 `data/species/{species}/` 输入目录、
`metadata.yaml`、`samples.yaml` 和 `data/species_manifest.tsv`：

```bash
../backend/venv/bin/python workflow/scripts/build_species_manifest.py
```

脚本只创建软链接和元数据，不复制、不移动、不删除原有 genome/GFF。它会读取
MySQL 中已有的 `Genome_size`、`LAI_value`、`Busco`，并补充读取旧流程
`Script/CottonOGD` 下已计算但可能未入库的汇总：

- `busco/Busco_summary.txt`
- `LAI/result/LAI_summary.txt`
- `LAI/Genome_size/Genome_size.txt`

结果写入每条样本的 `qc_completed`、`metadata.yaml -> existing_qc`，并生成
`data/legacy_qc_report.tsv` 记录每个指标来自 MySQL 还是旧汇总、哪些值冲突：

```yaml
samples:
  - id: G.herbaceumA1a_HAU_v1
    enabled: true
    genome: data/species/G.herbaceumA1a_HAU_v1/genome.fasta
    gff: data/species/G.herbaceumA1a_HAU_v1/genes.gff3
    metadata: data/species/G.herbaceumA1a_HAU_v1/metadata.yaml
    qc_completed: [genome_size, lai, busco]
```

合并规则：MySQL 已有值优先，旧汇总只填补 MySQL 缺失的指标；两者不同会写入
`legacy_qc_conflicts` 和 `data/legacy_qc_report.tsv`，不会静默覆盖。明显非法
的值（`NaN`、BUSCO > 1、LAI > 100）会被旧汇总中的有效值替换；没有有效值时
不标记完成，交由流程重算。

`qc_completed` 中的指标不会重新计算，`aggregate_report.py` 会把已有值写进
`qc_report.yaml` 并标记来源。未列出的指标照常运行。最长蛋白/CDS/mRNA 提取
不受影响，始终会从 genome + GFF 重新提取。如需对已存在的 results 强制重跑，
可加 `--forcerun longest_protein longest_cds longest_mrna`。

## 3. 单物种运行

```bash
snakemake --use-conda --cores 8 --configfile config.yaml \
  --config genome=data/new_species.fasta \
           gff=data/new_species.gff3 \
           metadata=data/new_species_metadata.yaml
```

如需显式指定物种 ID（否则取 metadata 的 `species_name` 或 genome 文件名）：

```bash
snakemake --use-conda --cores 8 --configfile config.yaml \
  --config genome=data/new_species.fasta gff=data/new_species.gff3 \
           metadata=data/new_species_metadata.yaml species=new_species
```

## 4. 批量运行

```bash
snakemake --use-conda --cores 32 --configfile config.yaml
```

只运行某几个物种：

```bash
snakemake --use-conda --cores 16 --configfile config.yaml \
  --config species_filter=species_A,species_B
```

（也可直接在 `samples.yaml` 中把不需要的条目设为 `enabled: false`。）

## 5. 重跑与增量

```bash
# 强制重跑单个物种（通过删除该物种结果或 --forcerun）
snakemake --use-conda --cores 8 --configfile config.yaml \
  --forcerun validate_input --config species_filter=species_A

# 只重跑 QC
snakemake --use-conda --cores 8 results/species_A/qc/qc_report.yaml

# 只跑某个规则及其上游
snakemake --use-conda --cores 8 results/species_A/jbrowse/tracks.done
```

Snakemake 默认按文件时间戳增量执行；已存在的产物会跳过。
数据库入库幂等键为 `species_id + annotation_version`，由
`upload.conflict_policy` 控制：

- `skip`（默认）：已有成功记录则跳过并 warning；
- `overwrite`：按物种删除旧基因/注释后重插；
- `version`：以 `annotation_version` 区分版本，QC/上传状态按版本记录。

## 6. 只跑 QC / dry-run

```bash
# 只生成 QC 报告
snakemake --use-conda --cores 8 results/species_A/qc/qc_report.yaml

# 全流程 DAG 预演（不执行）
snakemake -n --cores 1 --configfile config.yaml

# 入库 dry-run（默认即 dry-run）
snakemake --use-conda --cores 8 results/species_A/upload/upload_report.json
```

dry-run 同样会写 `results/{species}/upload/upload.done` 作为本次检查完成的标记；
不会写数据库。确认要真正入库时，把 `config.yaml` 的 `upload.dry_run` 改为
`false`，并强制重跑该规则：

```bash
snakemake --use-conda --cores 8 --configfile config.yaml \
  --forcerun upload_to_db --config species_filter=species_A
```

`db_upload.py` 也支持独立调用：

```bash
backend/venv/bin/python workflow/scripts/db_upload.py \
  --config config.yaml --species species_A --dry-run --verbose

# 确认后写入（单物种）
backend/venv/bin/python workflow/scripts/db_upload.py \
  --config config.yaml --species species_A --apply --yes

# 批量写入：先 dry-run 输出清单，再加 --apply --yes
backend/venv/bin/python workflow/scripts/db_upload.py \
  --config config.yaml --samples samples.yaml --dry-run
```

## 7. 数据库迁移（只生成，不自动执行）

表结构由 Django `backend/CottonOGD/models.py` 控制：

```bash
cd backend
./venv/bin/python manage.py makemigrations CottonOGD --name add_species_metadata_and_qc
./venv/bin/python manage.py makemigrations CottonOGD --empty --name add_interproscan_source
./venv/bin/python manage.py sqlmigrate CottonOGD 0054 > ../workflow/sql/0054_plan.sql
./venv/bin/python manage.py sqlmigrate CottonOGD 0055 > ../workflow/sql/0055_plan.sql
# 审阅 SQL 后、另行确认再执行：
# ./venv/bin/python manage.py migrate CottonOGD
```

`0054` 增加 `species` 元数据列和 `species_literature/species_qc/
species_upload_state`；`0055` 增加 `annotation_source.interproscan`。
`db_upload.py` 不做 DDL；缺表/缺列时在报告中写 warning。

执行迁移前先确认 `backend/.env` 指向正确数据库并做好备份；审阅
`workflow/sql/0054_plan.sql`、`0055_plan.sql` 后再运行
`manage.py migrate CottonOGD`，禁止使用 `--fake`。未执行迁移时，
基因/序列/GO/KEGG 等旧表仍可入库，QC 明细与文献会跳过并记录 warning。

## 8. 输出结构

```
results/{species}/
├── validated/validation.json
├── sequences/genes.fixed.gff[.gz|.tbi]
├── sequences/{mrna,cdna,cds,pro,gene_genome,upstream20000,downstream20000}.fa
├── longest/{pro,cds,mrna}_longest.fasta
├── qc/{genome_size,lai,busco,te}.json + qc_report.yaml/json
├── annotation/{eggnog,itak,uniprot,interproscan}/
├── publish/manifest.json
├── jbrowse/{jbrowse.done,tracks.json,tracks.done}
├── blast/blast.done
├── upload/upload_report.json
└── logs/
results/summary.tsv
results/summary.html
```

发布到后端：

```
backend/data/Genome/{genome,gff,cds,pep,cdna,mrna,gene,upstream,downstream}/
backend/data/genome/{species}/        # 指向 ../../Genome/... 的相对软链
backend/data/blast_db/CottonOGD/{species}/{genome,mrna,cds,protein}/
backend/data/gokegg_track/{species}/  # GO/KEGG/TE track
backend/static/jbrowse/data/{species}/config.json
```

`publish.overwrite=false` 时不会覆盖已有真实文件；只补充缺失文件/软链。
即使显式设置 `publish.overwrite=true`，脚本也会拒绝删除物种目录中已存在的
普通文件（标记为 `blocked`），只允许替换/重建软链接。

## 9. JBrowse

`rule jbrowse` 添加 assembly + GFF track；`rule jbrowse_tracks` 追加：

- GO: `biological_process_annotation`、`cellular_component_annotation`、
  `molecular_function_annotation`
- KEGG: `kegg_annotation`
- TE: `TE_annotation`（仅 `modules.te.enabled=true` 且存在 EDTA GFF）

大文件 URI 统一为 `/jbrowse/large/{species}/{file}`，由
`backend/CottonOGD/views/jbrowes_file.py` 提供 Range 服务。

## 10. BLAST 建库

`rule build_blast_db` 生成：

```
backend/data/blast_db/CottonOGD/{species}/genome/{species}
backend/data/blast_db/CottonOGD/{species}/mrna/{species}
backend/data/blast_db/CottonOGD/{species}/cds/{species}
backend/data/blast_db/CottonOGD/{species}/protein/{species}
```

路径与 `backend/CottonOGD/views/blast.py` 一致（旧 Snakefile 的 `blastdb`
是错误路径）。

## 11. 功能注释

`modules.functional_annotation` 控制四个分支：

- eggNOG → `parse_eggnog.py` → GO/KEGG + `eggnog.tsv`
- iTAK → TF/kinase → `itak.tsv`
- UniProt → BLASTP → `Final_Annotation.tsv`
- InterProScan → `interproscan.tsv`

eggNOG/GO 解析复用 vendored 的 `parse_eggNOG.py` 和 `parse_go_obofile.py`；
KEGG REST 响应缓存在 `workflow/cache/kegg/`。`link/pathway/ko` 首次下载约
5–6 分钟，之后直接读缓存；离线环境可预先填充缓存或设置
`eggnog_offline: true`。

## 12. OrthoFinder（未来接入）

占位规则默认关闭：

```yaml
modules:
  orthofinder:
    enabled: false
```

I/O 契约已固定：

- 输入：`results/orthofinder/input/`，每个物种一个最长蛋白 FASTA；
- 输出：`results/orthofinder/results/` + `orthofinder.done`。

未来增量策略：

1. 核心物种先做一次完整 OrthoFinder；
2. 其余物种用 `orthofinder --assign <new_dir> --core <core_results>` 追加；
3. 新物种沿用 `--assign/--core`，不重跑全量。

注意：OrthoFinder 3.x 的 `-op` 只是“准备输入文件”，**不能**用于追加物种。
`db_upload.py` 预留 orthogroup 映射；表不存在时跳过并记录。建表建议见
`workflow/sql/orthogroup_proposal.sql`（仅建议，未纳入 models/migrations）。

## 13. 测试与验证

```bash
# DAG 预演
snakemake -n --cores 1 --configfile config.yaml

# 语法检查
backend/venv/bin/python -m py_compile $(find workflow/scripts -name '*.py')
while IFS= read -r f; do bash -n "$f"; done < <(find workflow/scripts -name '*.sh')

# 试点物种后对比旧结果
# - genome size 与 Genome_size.txt
# - LAI 与 LAI_summary
# - BUSCO 与 Busco_summary.txt
# - longest 与旧 longest.R（差异需解释）
```

## 14. 已知限制

- BUSCO/LAI/EDTA/InterProScan 资源消耗大，按 `config.yaml` 的
  `resources` 声明调度；EDTA 默认关闭。
- `publish` 对超大 genome 首次会执行 bgzip，耗时较长；后续复用。
- `species_literature/species_qc/species_upload_state` 需先执行迁移
  （当前仅生成 SQL）。
- 未执行任何生产库写入；`db_upload.py --apply` 需显式确认。