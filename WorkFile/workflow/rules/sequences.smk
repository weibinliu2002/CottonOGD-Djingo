"""GFF preparation and sequence extraction (mirrors legacy extract_* rules)."""

rule prepare_gff:
    input:
        done=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
        genome=lambda w: spath(w, "genome"),
        gff=lambda w: spath(w, "gff"),
    output:
        gff=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff"),
        gz=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff.gz"),
        tbi=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff.gz.tbi"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "sequences", "prepare_gff.py"),
        gffread=TOOLS.get("gffread", "gffread"),
        bgzip=TOOLS.get("bgzip", "bgzip"),
        tabix=TOOLS.get("tabix", "tabix"),
    threads: 1
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        mkdir -p "$(dirname {output.gff})"
        {params.python} {params.script} \
            --genome {input.genome} \
            --gff {input.gff} \
            --out {output.gff} \
            --gffread {params.gffread} \
            --bgzip {params.bgzip} \
            --tabix {params.tabix}
        """


rule extract_sequences:
    input:
        done=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
        genome=lambda w: spath(w, "genome"),
        gff=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff"),
    output:
        mrna=os.path.join(RESULTS_DIR, "{species}", "sequences", "mrna.fa"),
        cdna=os.path.join(RESULTS_DIR, "{species}", "sequences", "cdna.fa"),
        cds=os.path.join(RESULTS_DIR, "{species}", "sequences", "cds.fa"),
        pro=os.path.join(RESULTS_DIR, "{species}", "sequences", "pro.fa"),
        gene=os.path.join(RESULTS_DIR, "{species}", "sequences", "gene_genome.fa"),
        span=os.path.join(RESULTS_DIR, "{species}", "sequences", "span20000.fa"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "sequences", "extract_sequences.py"),
        outdir=os.path.join(RESULTS_DIR, "{species}", "sequences"),
        prefix="{species}",
        gffread=TOOLS.get("gffread", "gffread"),
        samtools=TOOLS.get("samtools", "samtools"),
        flank=config.get("sequences", {}).get("flank_length", 20000),
        protein=lambda w: spath(w, "protein") or "",
        transcripts=lambda w: spath(w, "transcripts") or "",
        cds=lambda w: spath(w, "cds") or "",
    threads: 2
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        mkdir -p {params.outdir}
        {params.python} {params.script} \
            --genome {input.genome} \
            --gff {input.gff} \
            --outdir {params.outdir} \
            --prefix {params.prefix} \
            --gffread {params.gffread} \
            --samtools {params.samtools} \
            --flank {params.flank} \
            --protein "{params.protein}" \
            --transcripts "{params.transcripts}" \
            --cds "{params.cds}"
        """


rule split_flanks:
    input:
        span=os.path.join(RESULTS_DIR, "{species}", "sequences", "span20000.fa"),
    output:
        upstream=os.path.join(RESULTS_DIR, "{species}", "sequences", "upstream20000.fa"),
        downstream=os.path.join(RESULTS_DIR, "{species}", "sequences", "downstream20000.fa"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "sequences", "split_flanks.py"),
        flank=config.get("sequences", {}).get("flank_length", 20000),
    threads: 1
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        {params.python} {params.script} \
            --input {input.span} \
            --upstream {output.upstream} \
            --downstream {output.downstream} \
            --flank {params.flank}
        """