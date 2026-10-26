# CottonOGD Snakemake 工作流

## 概述

这个Snakemake工作流用于自动化CottonOGD数据库的基因组分析流程。

## 工作流步骤

1. **add_Species_info**: 将物种信息导入到Species_info表
2. **add_species**: 将基因组添加到数据库
3. **import_genemaster**: 导入GeneMaster数据
4. **import_transcriptmaster**: 导入TranscriptMaster数据
5. **run_busco**: 运行BUSCO评估基因组完整性
6. **run_lai**: 计算LAI（LTR Assembly Index）
7. **add_jbrowse**: 添加JBrowse轨道
8. **extract_sequences**: 提取序列（CDS、mRNA、蛋白质等）
9. **run_itak**: 使用iTAK鉴定转录因子
10. **import_tf_to_genefamily**: 将iTAK结果导入genefamily表

## 准备输入数据

### 1. 配置文件 (config.yaml)

编辑 `config.yaml` 文件，设置要分析的基因组列表：

```yaml
samples:
  - G.hirsutumAD1_TM-1_ZJU_v2.1
  - G.barbadenseAD2_3-79_HGSC_v1.1
  - G.arboreumA2_Shixiya1_HAU_v1
```

### 2. 物种信息文件 (species_info.csv)

创建 `species_info.csv` 文件，包含物种详细信息。参考 `species_info.csv.example` 文件：

**CSV字段说明：**

| 字段 | 说明 | 示例 |
|------|------|------|
| name | 物种名称（唯一） | G.hirsutumAD1_TM-1_ZJU_v2.1 |
| Cotton_Species | 棉花物种 | Gossypium hirsutum |
| Genome_type | 基因组类型 | AD1 |
| Category | 类别 | cultivated |
| Accession | 登录号 | AAD1 |
| Ploidy | 倍性 | 2x |
| Assembling_institution | 组装机构 | Zhejiang University |
| Website | 网站 | https://www.cottongen.org |
| Article | 文章DOI | doi:10.1038/nbt.3208 |
| LAI_value | LAI值 | 10.5 |
| Busco | BUSCO值 | 95.2 |
| Genome_size | 基因组大小（bp） | 2300000000 |
| description | 描述 | Reference genome of upland cotton |
| alias | 实际显示名 | TM-1_ZJU_v2.1 |

**示例CSV内容：**

```csv
name,Cotton_Species,Genome_type,Category,Accession,Ploidy,Assembling_institution,Website,Article,LAI_value,Busco,Genome_size,description,alias
G.hirsutumAD1_TM-1_ZJU_v2.1,Gossypium hirsutum,AD1,cultivated,AAD1,2x,Zhejiang University,https://www.cottongen.org,doi:10.1038/nbt.3208,10.5,95.2,2300000000,Reference genome of upland cotton,TM-1_ZJU_v2.1
```

### 3. 基因组文件

将基因组文件放置在 `/data/web/CottonOGD/OGD/backend/data/genome/{genome_name}/` 目录下：

- **FASTA文件**: `{genome_name}.fa` 或 `{genome_name}.genome.fa`
- **GFF文件**: `{genome_name}.gff.gz`

## 运行工作流

### 查看工作流图

```bash
cd /data/web/CottonOGD/OGD/Script/snakemake
snakemake --dag | dot -Tpng > workflow.png
```

### 运行完整流程

```bash
snakemake -j 8
```

### 运行特定步骤

```bash
# 只运行物种信息导入
snakemake G.hirsutumAD1_TM-1_ZJU_v2.1_species_info_added.txt

# 只运行BUSCO分析
snakemake G.hirsutumAD1_TM-1_ZJU_v2.1_busco.txt
```

### 干运行（测试）

```bash
snakemake -n
```

## 工具和数据库路径

在 `config.yaml` 中配置以下路径：

```yaml
busco_db: "/data/wbliu/data/CottonOGD/busco/busco_downloads/lineages/eudicots_odb10"
itak_dir: "/data/wbliu/data/CottonOGD/iTAK"
lai_dir: "/data/wbliu/data/CottonOGD/LAI"
```

## 输出结果

工作流完成后，结果将保存在以下位置：

- **基因组数据**: `/data/web/CottonOGD/OGD/backend/data/genome/{genome_name}/`
- **BUSCO结果**: `{genome_name}/busco/`
- **LAI结果**: `{genome_name}/result/{genome_name}/`
- **iTAK结果**: `/data/wbliu/data/CottonOGD/iTAK/iTAK_result/{genome_name}.pro/`

## 注意事项

1. 确保 `species_info.csv` 文件中的物种名称与 `config.yaml` 中的 `samples` 列表一致
2. 确保基因组文件已正确放置在指定目录
3. BUSCO和LAI分析需要较长时间，建议使用多线程运行
4. iTAK分析需要CDS序列文件，确保已正确提取

## 联系方式

如有问题，请联系 CottonOGD 项目团队。