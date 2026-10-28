# CottonOGD 清理、合并与改造方案

> **本次实施未删除、未移动任何旧文件。**
> 下列“删除候选”仅在试点物种验证通过后，另行列出清单并征得确认后执行。
> MySQL 迁移只生成文件与 SQL，未执行 `migrate`。

## 1. 删除候选（待确认）

| 文件 | 原因 | 替代 |
|---|---|---|
| `Script/script/longest.R` | 仅按后缀取最长，无 GFF 映射 | `~/bin/longest_protein_by_gene.py` |
| `Script/CottonOGD/LAI/Genome_size/Genome_size.R` | 被 Python 流式求和替代 | `workflow/scripts/qc/calc_genome_size.py` |
| `Script/CottonOGD/LAI/result/LAI_summary.R` | 仅取 `whole_genome` 行 | `workflow/scripts/qc/parse_lai.py` |
| `Script/CottonOGD/busco/busco_summary.R` | 解析 short_summary | `workflow/scripts/qc/parse_busco.py` |
| `Script/snakemake/config2.yaml` | `base_dir` 与根配置冲突 | `config.yaml` |
| `Script/snakemake/LAI_for_snakemake.sh` | 硬编码路径 | `workflow/scripts/qc/run_ltr.sh` + `run_lai.sh` |
| `Script/snakemake/Snakefile` | 被根目录新流程替代 | 根 `Snakefile` + `workflow/rules/` |
| `Script/snakemake/import_eggnog_annotation.py` | ID 映射缺陷、无事务 | `db_upload.py` |
| `Script/snakemake/import_sequences_to_geneseq.py` | 分散入库、无幂等 | `db_upload.py` |
| `Script/script/import_itak_to_genefamily.py` | `TRUNCATE genefamily` | `db_upload.py` 按物种 upsert |
| `Script/script/GO_KEGG.R`、`add_annoation.R` | 被 parser/uploader 替代 | `parse_eggnog.py` + `db_upload.py` |
| `Script/script/extract_seq.R`、`genemaster.R` | 被 Python 提取/入库替代 | `extract_sequences.py`、`db_upload.py` |

### 不建议删除（保留作对照/回滚）

- `Script/CottonOGD/LAI/LAI.sh`、`busco/busco.sh`、`eggnog_annoation/emapper.sh`
- `Script/snakemake/fix_gff.sh`、`extract_seq.R`
- `backend/scripts/build_gokegg_tracks.py`
- `backend/static/jbrowse/{add_jbrowes.sh,update_config_paths.py,set_default_tracks.py}`
- 全部旧 R 脚本：试点对比完成前保留。

## 2. 目录迁移（建议，未执行）

用户提到的 `Script/CottonOGD/LAI,Genome_size/` 实际不存在；真实目录为：

```
Script/CottonOGD/LAI/                 # LAI.sh
Script/CottonOGD/LAI/Genome_size/     # Genome_size.R
Script/CottonOGD/LAI/result/          # LAI_summary.R
Script/CottonOGD/busco/               # busco.sh / busco_summary.R
```

建议将 QC 相关脚本统一归档到：

```
workflow/scripts/qc/
├── calc_genome_size.py
├── prepare_lai_genome.py
├── run_ltr.sh
├── run_lai.sh
├── parse_lai.py
├── run_busco.sh
└── parse_busco.py
```

旧目录**复制**而非移动；验证通过后再询问是否删除旧副本。

## 3. 合并清单

| 合并前 | 合并后 |
|---|---|
| `extract_mrna/cdna/cds/pro` 四条规则 | `rule extract_sequences` |
| `extract_gene_genome`（R） | `workflow/scripts/sequences/extract_sequences.py` 内 gene_genome 分支 |
| `extract_upstream/downstream`（TBtools） | `gffread --w-add 20000` + `split_flanks.py` |
| `longest.R` 三份逻辑 | `run_longest.py` 调用用户脚本 |
| 旧 `import_*` 多条入库规则 | `db_upload.py` 单事务 |
| `unipro_annotation.py` | `annotation/parse_uniprot.py`（同样的 header 解析） |
| `build_gokegg_tracks.py` + 新 TE 需求 | `jbrowse/build_jbrowse_tracks.py` |
| `add_jbrowes.sh` + `update_config_paths.py` | `jbrowse/add_jbrowse.sh` + `update_jbrowse_config.py` |
| `add_blast_db.sh` + `makeblast` | `blast/build_blast_db.sh` + `rule build_blast_db` |
| `LAI_summary.R` / `busco_summary.R` | `parse_lai.py` / `parse_busco.py` |
| `Genome_size.R` | `calc_genome_size.py` |

## 4. 改造清单：只参数化，不重写计算逻辑

| 能力 | 复用来源 | 改造方式 |
|---|---|---|
| genome size | `Genome_size.R` 的 `sum(width)` | Python 流式累加，结果口径一致 |
| LAI | `LAI/LAI.sh` | `run_ltr.sh` / `run_lai.sh` 参数化线程、路径、LTR 参数 |
| BUSCO | `busco/busco.sh` | `run_busco.sh` 参数化 lineage/threads/augustus |
| LTR | `LAI.sh` 中 `LTR_FINDER_parallel + gt ltrharvest + LTR_retriever` | 保留原命令顺序与阈值 |
| eggNOG | `emapper.sh` + `parse_eggNOG.py` + `parse_go_obofile.py` | 包装调用，增加超时/重试/缓存；vendor 原文件不改 |
| UniProt | `unipro_annotation.py` | 保留 header 解析规则；输入改为流程内 BLAST 结果 |
| InterProScan | 新接入（无旧脚本） | `interproscan.sh -f TSV -dp -goterms -pa` + parser |
| iTAK | 旧 `import_itak_to_genefamily.py` 的解析逻辑 | 参数化运行；入库改为 upsert |
| TE | 新接入（EDTA） | 默认关闭；`run_edta.sh` + `parse_te.py` |
| JBrowse GO/KEGG | `build_gokegg_tracks.py` | 复用 GFF 属性/排序/软链/config 逻辑 |
| JBrowse TE | 参考 issue #192 的 GFF 处理 | 只排序/压缩，不改 EDTA 属性 |
| 上下游 20000 | `gffread -u --w-add 20000` | 真实 20000 bp；边界截断 warning |

## 5. 新增/调整的规则

| rule | 说明 |
|---|---|
| `validate_input` | 首节点，失败即停 |
| `prepare_gff` | 解压/过滤/交换坐标/排序/bgzip/tabix；GTF 先经 `gffread -F -O` 转 GFF3 |
| `extract_sequences` | 7 类序列 + span20000 |
| `split_flanks` | 拆分 upstream/downstream 20000 bp |
| `longest_protein/cds/mrna` | 调用 `~/bin/longest_protein_by_gene.py` |
| `check_longest` | 三份最长序列一致性检查（可选） |
| `calc_genome_size` | 基因组大小 |
| `prepare_lai_genome` | 重命名 seq1..seqN |
| `ltr_annotation` → `run_lai` → `parse_lai` | LAI 依赖 LTR |
| `run_busco` → `parse_busco` | 可配置 lineage |
| `run_edta` → `parse_te` | 默认关闭 |
| `run_eggnog` → `parse_eggnog` | GO/KEGG/eggnog.tsv |
| `run_itak` → `parse_itak` | TF/kinase |
| `run_uniprot` → `parse_uniprot` | BLASTP + header |
| `run_interproscan` → `parse_interproscan` | member DB 映射 |
| `publish` | `Genome/{type}` + `genome/{species}` 软链；默认不覆盖，拒绝删除已存在普通文件 |
| `jbrowse` → `jbrowse_tracks` | assembly/GFF + GO/KEGG/TE |
| `build_blast_db` | 4 个 BLAST 库 |
| `qc_report` | 合并 QC |
| `upload_to_db` | `db_upload.py` |
| `aggregate_report` | `summary.tsv/html` |
| `orthofinder` | 占位，默认关闭 |

## 6. 数据库变更（只生成，未执行）

```bash
# 已生成，未执行
backend/venv/bin/python backend/manage.py makemigrations CottonOGD --name add_species_metadata_and_qc
backend/venv/bin/python backend/manage.py makemigrations CottonOGD --empty --name add_interproscan_source
# SQL 已导出到 workflow/sql/
```

- `0054`：`species` 增加 `common_name/assembly_version/annotation_version/submitter`；
  新增 `species_literature/species_qc/species_upload_state`。
- `0055`：`annotation_source` 增加 `interproscan`。
- `db_upload.py` 只做 DML；缺表/缺列时 warning，不执行 DDL。
- 执行 `migrate` 前需另行确认；禁止 `--fake`。

## 7. 需要用户确认的事项

1. 删除清单第 1 节：是否在试点验证后删除？
2. 旧 `Script/` 目录是否保留（默认保留）？
3. 是否执行 `migrate CottonOGD`（当前仅生成 SQL）？
4. 是否允许 `publish` 在 `backend/data/Genome`、`backend/data/genome`、
   `backend/data/blast_db`、`backend/static/jbrowse/data` 写入/更新软链？
   （默认不覆盖已有真实文件）
5. `db_upload.py --apply` 是否先对测试库执行，再对生产库执行？
6. OrthoFinder 是否仅保留占位（默认），暂不创建 orthogroup 表？