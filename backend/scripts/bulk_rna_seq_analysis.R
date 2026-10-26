#!/usr/bin/env Rscript
# 普通转录组（bulk RNA-seq）差异分析：DESeq2 标准流程
#
# 输入两个文件：
#   1. 基因 count 矩阵：TSV/CSV，首列 gene_id，表头为样本名（基因 x 样本）
#   2. 分组文件：TSV/CSV，两列 sample,group（样本 -> 分组）
#
# 用法：
#   Rscript scripts/bulk_rna_seq_analysis.R \
#     --counts counts.csv --group group.tsv --outdir results/bulk_20261025 \
#     [--group-a Leaf] [--group-b Root]     # 不指定时取分组文件的前两组
#     [--fdr 0.05] [--logfc 1] [--top-n 50]
#     [--term2gene go_kegg_terms.tsv]       # 可选，clusterProfiler 富集用
#
# 输出（outdir 下）：
#   qc_stats.tsv / normalized_expr.csv / pca.png
#   deg_<A>_vs_<B>.tsv / volcano_<A>_vs_<B>.png / heatmap_top_<A>_vs_<B>.png
#   enrichment_<A>_vs_<B>.tsv（提供 --term2gene 时）
#   deg_genes_<A>_vs_<B>.txt（显著 DEG 列表，供 PPI 等下游使用）

suppressPackageStartupMessages({
  library(optparse)
  library(DESeq2)
  library(ggplot2)
  library(ggrepel)
  library(pheatmap)
  library(dplyr)
  library(tibble)
  library(RColorBrewer)
})

option_list <- list(
  make_option("--counts", type = "character", help = "count 矩阵（首列 gene_id，表头样本名）"),
  make_option("--group", type = "character", help = "分组文件（sample,group 两列）"),
  make_option("--outdir", type = "character", help = "结果输出目录"),
  make_option("--group-a", type = "character", default = NULL, help = "组 A（默认分组文件第一组）"),
  make_option("--group-b", type = "character", default = NULL, help = "组 B（默认第二组）"),
  make_option("--fdr", type = "double", default = 0.05, help = "显著性阈值 [default %default]"),
  make_option("--logfc", type = "double", default = 1, help = "log2FC 阈值 [default %default]"),
  make_option("--top-n", type = "integer", default = 50, help = "热图展示 DEG 数 [default %default]"),
  make_option("--term2gene", type = "character", default = NULL,
              help = "富集基因集 TSV：term_id, gene_id[, term_name]；GO/KEGG 均可")
)
opt <- parse_args(OptionParser(option_list = option_list))

if (is.null(opt$counts) || is.null(opt$group) || is.null(opt$outdir)) {
  stop("必须提供 --counts、--group、--outdir")
}
dir.create(opt$outdir, showWarnings = FALSE, recursive = TRUE)
log <- function(msg) cat(format(Sys.time(), "%H:%M:%S"), msg, "\n", sep = "")

# ---- 读入 ---------------------------------------------------------------
sep <- ifelse(grepl("\\.csv$", opt$counts, ignore.case = TRUE), ",", "\t")
counts <- read.delim(opt$counts, sep = sep, row.names = 1, check.names = FALSE)
sep_g <- ifelse(grepl("\\.csv$", opt$group, ignore.case = TRUE), ",", "\t")
group_df <- read.delim(opt$group, sep = sep_g, check.names = FALSE,
                       colClasses = "character")
stopifnot(ncol(group_df) >= 2)
colnames(group_df)[1:2] <- c("sample", "group")

counts <- counts[, colnames(counts) %in% group_df$sample, drop = FALSE]
missing <- setdiff(colnames(counts), group_df$sample)
if (length(missing) > 0) {
  log(paste0("警告: ", length(missing), " 个样本在分组文件中缺失，已忽略"))
}
counts <- counts[, group_df$sample[group_df$sample %in% colnames(counts)], drop = FALSE]
if (ncol(counts) < 4) stop("counts 与分组共同样本过少")
groups <- group_df$group[match(colnames(counts), group_df$sample)]
coldata <- data.frame(row.names = colnames(counts), group = factor(groups))
log(sprintf("加载: %d 基因 x %d 样本, %d 组", nrow(counts), ncol(counts), nlevels(coldata$group)))

# ---- QC ------------------------------------------------------------------
qc <- data.frame(
  sample = colnames(counts),
  lib_size = colSums(counts),
  detected_genes = colSums(counts > 0),
  mean_count = colMeans(counts))
write.table(qc, file.path(opt$outdir, "qc_stats.tsv"), sep = "\t",
            row.names = FALSE, quote = FALSE)

# ---- DESeq2 --------------------------------------------------------------
dds <- DESeqDataSetFromMatrix(countData = round(as.matrix(counts)),
                              colData = coldata, design = ~ group)
dds <- dds[rowSums(counts(dds)) > 0, ]        # 去全零基因
log(sprintf("QC: 保留 %d 个非零基因", nrow(dds)))
dds <- DESeq(dds)
# vst 需要 >=1000 个基因（nsub），少于此数回退到完整 VST
vsd <- if (nrow(dds) >= 1000) vst(dds, blind = TRUE) else
  varianceStabilizingTransformation(dds, blind = TRUE)
write.table(counts(dds, normalized = TRUE),
            file.path(opt$outdir, "normalized_expr.csv"),
            sep = ",", quote = FALSE, col.names = NA)

# PCA
pca_dat <- plotPCA(vsd, intgroup = "group", returnData = TRUE)
pct <- round(100 * attr(pca_dat, "percentVar"))
p <- ggplot(pca_dat, aes(PC1, PC2, color = group)) +
  geom_point(size = 3, alpha = 0.8) +
  xlab(paste0("PC1: ", pct[1], "% variance")) +
  ylab(paste0("PC2: ", pct[2], "% variance")) +
  theme_bw() + ggtitle("PCA (vst)")
ggsave(file.path(opt$outdir, "pca.png"), p, width = 7, height = 6, dpi = 150)
log("PCA -> pca.png")

# ---- 差异表达 ------------------------------------------------------------
lvls <- levels(coldata$group)
grp_a <- if (!is.null(opt$`group-a`)) opt$`group-a` else lvls[1]
grp_b <- if (!is.null(opt$`group-b`)) opt$`group-b` else lvls[2]
if (!all(c(grp_a, grp_b) %in% lvls)) stop("指定的组不存在: ", grp_a, "/", grp_b)
log(sprintf("差异比较: %s vs %s", grp_a, grp_b))

res <- results(dds, contrast = c("group", grp_a, grp_b), alpha = opt$fdr)
deg <- as.data.frame(res) %>%
  rownames_to_column("gene_id") %>%
  arrange(pvalue)
tag <- paste(grp_a, "vs", grp_b, sep = "_")
write.table(deg, file.path(opt$outdir, paste0("deg_", tag, ".tsv")),
            sep = "\t", row.names = FALSE, quote = FALSE, na = "")

sig <- deg %>% filter(!is.na(padj), padj < opt$fdr, abs(log2FoldChange) >= opt$logfc)
log(sprintf("显著 DEG: %d 个 (FDR<%g, |log2FC|>=%g)", nrow(sig), opt$fdr, opt$logfc))

# ---- 火山图 --------------------------------------------------------------
vol_df <- as.data.frame(res) %>%
  rownames_to_column("gene_id") %>%
  filter(!is.na(log2FoldChange), !is.na(padj)) %>%
  mutate(sig = case_when(
    padj < opt$fdr & log2FoldChange >= opt$logfc ~ "Up",
    padj < opt$fdr & log2FoldChange <= -opt$logfc ~ "Down",
    TRUE ~ "NS"))
label_df <- vol_df %>%
  filter(sig != "NS") %>%
  group_by(sig) %>%
  arrange(desc(-log10(padj)), .by_group = TRUE) %>%
  slice_head(n = 10) %>%
  ungroup()
p <- ggplot(vol_df, aes(log2FoldChange, -log10(padj), color = sig)) +
  geom_point(size = 1, alpha = 0.6) +
  scale_color_manual(values = c(Up = "#d62728", Down = "#1f77b4", NS = "grey70")) +
  geom_vline(xintercept = c(-opt$logfc, opt$logfc), linetype = "dashed", color = "grey40") +
  geom_hline(yintercept = -log10(opt$fdr), linetype = "dashed", color = "grey40") +
  geom_text_repel(data = label_df, aes(label = gene_id), size = 2.2,
                  max.overlaps = 20, show.legend = FALSE) +
  labs(x = paste0("log2FC (", grp_a, " vs ", grp_b, ")"), y = "-log10(FDR)",
       title = paste0("Volcano: ", tag, " (sig=", nrow(sig), ")"),
       color = NULL) +
  theme_bw()
ggsave(file.path(opt$outdir, paste0("volcano_", tag, ".png")),
       p, width = 7, height = 6, dpi = 150)
log("火山图完成")

# ---- Top DEG 热图 ---------------------------------------------------------
if (nrow(sig) > 0) {
  top <- sig %>% arrange(desc(log2FoldChange)) %>% slice_head(n = opt$`top-n` / 2)
  bot <- sig %>% arrange(log2FoldChange) %>% slice_head(n = opt$`top-n` / 2)
  top_genes <- c(top$gene_id, bot$gene_id)
  mat <- assay(vsd[top_genes, ])[top_genes, , drop = FALSE]
  mat <- mat - rowMeans(mat)
  ann_col <- data.frame(group = coldata$group)
  rownames(ann_col) <- colnames(counts)
  ann_colors <- list(group = setNames(brewer.pal(max(3, nlevels(coldata$group)),
                                                 "Set2")[seq_len(nlevels(coldata$group))],
                                      levels(coldata$group)))
  png(file.path(opt$outdir, paste0("heatmap_top_", tag, ".png")),
      width = max(1200, ncol(mat) * 120), height = max(900, nrow(mat) * 20), res = 120)
  pheatmap(mat, annotation_col = ann_col, annotation_colors = ann_colors,
           cluster_cols = FALSE, border_color = NA,
           main = paste0("Top DEGs (vst, centered): ", tag),
           fontsize_row = 6, fontsize_col = 10)
  dev.off()
  log("热图完成")
}

# ---- 富集（可选）----------------------------------------------------------
if (!is.null(opt$term2gene) && file.exists(opt$term2gene) && nrow(sig) >= 10) {
  suppressPackageStartupMessages(library(clusterProfiler))
  t2g <- read.delim(opt$term2gene, sep = "\t", header = FALSE,
                    colClasses = "character")
  t2g <- t2g[t2g[[2]] != "", ]
  term2gene <- unique(t2g[, c(1, 2)])
  colnames(term2gene) <- c("term", "gene")
  term2name <- NULL
  if (ncol(t2g) >= 3 && any(t2g[[3]] != "")) {
    term2name <- unique(t2g[t2g[[3]] != "", c(1, 3)])
    colnames(term2name) <- c("term", "name")
  }
  universe <- rownames(res)[!is.na(rownames(res))]
  tryCatch({
    enr <- enricher(gene = sig$gene_id, TERM2GENE = term2gene,
                    TERM2NAME = term2name, universe = universe,
                    pAdjustMethod = "BH", pvalueCutoff = 0.05, qvalueCutoff = 0.2)
    out <- as.data.frame(enr)
    if (nrow(out) > 0) {
      write.table(out, file.path(opt$outdir, paste0("enrichment_", tag, ".tsv")),
                  sep = "\t", row.names = FALSE, quote = FALSE)
      log(sprintf("富集 -> enrichment_%s.tsv (%d terms)", tag, nrow(out)))
    } else {
      log("富集: 无显著 term")
    }
  }, error = function(e) log(paste0("富集失败（跳过）: ", conditionMessage(e))))
}

# ---- 显著基因列表（供 PPI 等下游使用）-------------------------------------
writeLines(sig$gene_id, file.path(opt$outdir, paste0("deg_genes_", tag, ".txt")))
log(sprintf("完成。显著 DEG %d 个 -> deg_genes_%s.txt", nrow(sig), tag))
