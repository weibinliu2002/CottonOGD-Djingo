# CottonOGD 输入数据规范

## 1. 目录与文件

每个物种一个目录：

```
data/{species_id}/
├── genome.fasta          # 必需，FASTA 或 FASTA.gz
├── genes.gff3            # 必需，GFF3 或 GTF（GFF3 优先；GTF 自动经 gffread 转 GFF3）
├── proteins.fasta        # 可选，蛋白序列
├── transcripts.fasta     # 可选，转录本序列
├── cds.fasta             # 可选，CDS 序列
└── metadata.yaml         # 必需，见第 3 节
```

`species_id` 只允许 `[A-Za-z0-9_.-]`，且必须在 `samples.yaml` 中唯一。
建议使用规范拉丁名，例如 `Gossypium_hirsutum`。

批量清单 `samples.yaml`：

```yaml
samples:
  - id: Gossypium_hirsutum
    enabled: true
    genome: data/Gossypium_hirsutum/genome.fasta
    gff: data/Gossypium_hirsutum/genes.gff3
    protein: data/Gossypium_hirsutum/proteins.fasta      # 可选
    transcripts: data/Gossypium_hirsutum/transcripts.fasta
    cds: data/Gossypium_hirsutum/cds.fasta
    metadata: data/Gossypium_hirsutum/metadata.yaml
    # 可选：这些指标已在 MySQL 中存在，跳过重算
    qc_completed: [genome_size, lai, busco]
```

已有 MySQL 物种可用 `workflow/scripts/build_species_manifest.py` 自动生成上述
清单、软链接和 `metadata.yaml`。`qc_completed` 中的指标必须在
`metadata.yaml -> existing_qc` 中有值；未列出的指标仍会运行。
最长蛋白/CDS/mRNA 不受 `qc_completed` 影响，始终重新提取。

单物种模式不需要修改 `samples.yaml`：

```bash
snakemake --use-conda --cores 8 --configfile config.yaml \
  --config genome=data/new/genome.fasta gff=data/new/genes.gff3 \
           metadata=data/new/metadata.yaml species=new_species
```

未提供 `species` 时，流程优先使用 `metadata.yaml` 的 `species_name`，
否则使用 genome 文件名去掉 `.fasta/.fa/.fna[.gz]`。

## 2. FASTA 校验规则

`rule validate_input` 是 DAG 的第一个节点，失败立即终止（退出码 2）。

| 检查项 | 规则 |
|---|---|
| 序列数 | 至少 1 条 |
| header | 非空；第一个空白前的 token 必须唯一 |
| 序列 | 非空；只允许 `A C G T N`（大小写均可），`U` 仅警告 |
| 总长度 | 必须 > 0 |
| ID 字符集 | 不建议包含空白、`|`、`;`、`,`；允许但会在入库时告警 |

## 3. `metadata.yaml`

只填写无法从数据自动计算的信息：

```yaml
species_name: Gossypium_hirsutum     # 必填，需与 species_id 一致
common_name: Upland cotton           # 必填
ploidy: allotetraploid               # 必填
assembly_version: "UTX-T2T-v1.0"     # 必填
annotation_version: "CottON-v1.0"    # 必填；同一物种多版本入库的幂等键
literature:                          # 必填，可为空列表
  - title: "..."
    doi: "10.xxxx/xxxxx"
    url: "https://..."
    authors: "..."
    journal: "..."
    year: 2024
submitter: "..."                     # 必填
description: "..."                   # 必填
```

> `genome_size`、`LAI`、`BUSCO` **不要填写**。流程会从
> `genome.fasta`、LTR/LAI、BUSCO 结果自动计算并写入数据库。
> 如填写了同名字段，仅作为对照；最终以计算值为准并输出 warning。

文献使用 `species_literature` 关联表（一条文献一行），不覆盖旧的
`species.Article` 字段。

## 4. GFF3/GTF 校验规则

| 检查项 | 规则 |
|---|---|
| 列数 | GFF3 至少 9 列 |
| seqid | 必须存在于 genome FASTA |
| 坐标 | `start >= 1`、`end >= start`、`end <= seqid 长度`；`start > end` 时自动交换并 warning |
| 层级 | 每个 `gene` 至少有一个 `mRNA/transcript`；每个转录本至少有一个 `CDS` 或 `exon` |
| ID | `gene`/`mRNA` ID 全局唯一；`Parent` 必须指向已出现的 gene/mRNA |
| strand | 只允许 `+ - . ?`；`?` 归一化为 `.` |
| 序列 ID | GFF 的 seqid 集合与 FASTA 不一致时，按 FASTA 过滤并 warning |

预处理产物：`results/{species}/sequences/genes.fixed.gff[.gz]` + `.tbi`。
后续所有序列提取、最长序列、JBrowse、入库都使用该文件。

> GTF（以及少数只有转录本行的 GFF3）没有 `gene` feature 时，`prepare_gff.py`
> 会按 `gene_id`/`geneID`/`Parent` 汇总其转录本区间，补出 `gene` 行；原 ID
> 保持不变，避免与蛋白 FASTA、数据库 `genemaster.geneid` 不一致。

## 5. 自动计算字段与输出位置

| 字段 | 计算方式 | 输出 |
|---|---|---|
| genome_size | 所有 FASTA 序列长度之和 | `results/{s}/qc/genome_size.json` |
| LAI | 复用 `Script/CottonOGD/LAI/LAI.sh` 的 LTR + LAI 命令 | `results/{s}/qc/lai.json` |
| BUSCO | 复用 `Script/CottonOGD/busco/busco.sh` 的蛋白模式参数 | `results/{s}/qc/busco.json` |
| TE（可选） | EDTA，默认关闭 | `results/{s}/qc/te.json` |

合并报告：`results/{species}/qc/qc_report.yaml` + `.json`。
数据库写入时：

- `species.Genome_size` = 总碱基数
- `species.LAI_value` = LAI 字符串
- `species.Busco` = `Complete / Total`（4 位小数）
- `species_qc` 保存完整计数/百分比/原始 JSON

## 6. 可选文件缺失时的行为

- 缺少 `proteins.fasta`：用 `gffread -y` 从 GFF 提取蛋白；BUSCO/注释使用提取结果。
- 缺少 `transcripts.fasta`/`cds.fasta`：从 GFF + genome 提取。
- 缺少可选注释结果（eggNOG/iTAK/UniProt/InterProScan）：对应 Snakemake 分支
  不进入 DAG；`db_upload.py` 跳过对应表写入并在报告中记录。
- 缺少 EDTA：`modules.te.enabled=false`（默认），不产生 TE track/QC。