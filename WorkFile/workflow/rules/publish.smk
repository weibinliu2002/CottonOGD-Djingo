"""Publish results into backend/data/Genome and backend/data/genome."""

rule publish:
    input:
        validation=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
        genome=lambda w: spath(w, "genome"),
        gff=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff"),
        gff_gz=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff.gz"),
        gff_tbi=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff.gz.tbi"),
        mrna=os.path.join(RESULTS_DIR, "{species}", "sequences", "mrna.fa"),
        cdna=os.path.join(RESULTS_DIR, "{species}", "sequences", "cdna.fa"),
        cds=os.path.join(RESULTS_DIR, "{species}", "sequences", "cds.fa"),
        pro=os.path.join(RESULTS_DIR, "{species}", "sequences", "pro.fa"),
        gene_genome=os.path.join(RESULTS_DIR, "{species}", "sequences", "gene_genome.fa"),
        upstream=os.path.join(RESULTS_DIR, "{species}", "sequences", "upstream20000.fa"),
        downstream=os.path.join(RESULTS_DIR, "{species}", "sequences", "downstream20000.fa"),
        pro_longest=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.fasta"),
        cds_longest=os.path.join(RESULTS_DIR, "{species}", "longest", "cds_longest.fasta"),
        mrna_longest=os.path.join(RESULTS_DIR, "{species}", "longest", "mrna_longest.fasta"),
        metadata=lambda w: spath(w, "metadata"),
    output:
        manifest=os.path.join(RESULTS_DIR, "{species}", "publish", "manifest.json"),
        done=os.path.join(RESULTS_DIR, "{species}", "publish", "publish.done"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "publish", "publish.py"),
        sequences_dir=os.path.join(RESULTS_DIR, "{species}", "sequences"),
        longest_dir=os.path.join(RESULTS_DIR, "{species}", "longest"),
        type_dir=PATHS.get("genome_by_type", ""),
        species_dir=os.path.join(PATHS.get("genome_by_species", ""), "{species}"),
        overwrite="--overwrite" if config.get("publish", {}).get("overwrite", False) else "",
        bgzip=TOOLS.get("bgzip", "bgzip"),
        tabix=TOOLS.get("tabix", "tabix"),
        samtools=TOOLS.get("samtools", "samtools"),
    threads: 2
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        mkdir -p "$(dirname {output.manifest})"
        {params.python} {params.script} --species {wildcards.species} \
            --genome {input.genome} --gff {input.gff} --gff-gz {input.gff_gz} \
            --gff-tbi {input.gff_tbi} --sequences-dir {params.sequences_dir} \
            --longest-dir {params.longest_dir} --metadata {input.metadata} \
            --type-dir {params.type_dir} --species-dir {params.species_dir} \
            --manifest {output.manifest} {params.overwrite} \
            --bgzip {params.bgzip} --tabix {params.tabix} --samtools {params.samtools}
        touch {output.done}
        """