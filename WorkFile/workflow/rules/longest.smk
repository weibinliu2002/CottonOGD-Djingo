"""Longest sequence per gene, using ~/bin/longest_protein_by_gene.py."""

_LONGEST_TOOL = TOOLS.get("longest_protein_by_gene", "/home/web/bin/longest_protein_by_gene.py")


# Snakemake parses real rule blocks; the three runs are kept explicit so the DAG
# and linting stay straightforward.

rule longest_protein:
    input:
        fa=os.path.join(RESULTS_DIR, "{species}", "sequences", "pro.fa"),
        gff=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff"),
    output:
        fasta=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.fasta"),
        unmapped_tsv=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.unmapped.tsv"),
        unmapped_fa=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.unmapped.fa"),
        stats=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.stats.json"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "longest", "run_longest.py"),
        tool=_LONGEST_TOOL,
        min_rate=config.get("longest", {}).get("min_mapping_rate", 0.0),
    threads: 1
    resources:
        mem_mb=resource("default", "mem_mb") or 2000
    shell:
        """
        set -euo pipefail
        mkdir -p "$(dirname {output.fasta})"
        {params.python} {params.script} \
            --input {input.fa} \
            --gff {input.gff} \
            --out {output.fasta} \
            --unmapped-tsv {output.unmapped_tsv} \
            --unmapped-fasta {output.unmapped_fa} \
            --stats {output.stats} \
            --tool {params.tool} \
            --min-mapping-rate {params.min_rate}
        """


rule longest_cds:
    input:
        fa=os.path.join(RESULTS_DIR, "{species}", "sequences", "cds.fa"),
        gff=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff"),
    output:
        fasta=os.path.join(RESULTS_DIR, "{species}", "longest", "cds_longest.fasta"),
        unmapped_tsv=os.path.join(RESULTS_DIR, "{species}", "longest", "cds_longest.unmapped.tsv"),
        unmapped_fa=os.path.join(RESULTS_DIR, "{species}", "longest", "cds_longest.unmapped.fa"),
        stats=os.path.join(RESULTS_DIR, "{species}", "longest", "cds_longest.stats.json"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "longest", "run_longest.py"),
        tool=_LONGEST_TOOL,
    threads: 1
    resources:
        mem_mb=resource("default", "mem_mb") or 2000
    shell:
        """
        set -euo pipefail
        mkdir -p "$(dirname {output.fasta})"
        {params.python} {params.script} \
            --input {input.fa} --gff {input.gff} --out {output.fasta} \
            --unmapped-tsv {output.unmapped_tsv} \
            --unmapped-fasta {output.unmapped_fa} \
            --stats {output.stats} --tool {params.tool}
        """


rule longest_mrna:
    input:
        fa=os.path.join(RESULTS_DIR, "{species}", "sequences", "mrna.fa"),
        gff=os.path.join(RESULTS_DIR, "{species}", "sequences", "genes.fixed.gff"),
    output:
        fasta=os.path.join(RESULTS_DIR, "{species}", "longest", "mrna_longest.fasta"),
        unmapped_tsv=os.path.join(RESULTS_DIR, "{species}", "longest", "mrna_longest.unmapped.tsv"),
        unmapped_fa=os.path.join(RESULTS_DIR, "{species}", "longest", "mrna_longest.unmapped.fa"),
        stats=os.path.join(RESULTS_DIR, "{species}", "longest", "mrna_longest.stats.json"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "longest", "run_longest.py"),
        tool=_LONGEST_TOOL,
    threads: 1
    resources:
        mem_mb=resource("default", "mem_mb") or 2000
    shell:
        """
        set -euo pipefail
        mkdir -p "$(dirname {output.fasta})"
        {params.python} {params.script} \
            --input {input.fa} --gff {input.gff} --out {output.fasta} \
            --unmapped-tsv {output.unmapped_tsv} \
            --unmapped-fasta {output.unmapped_fa} \
            --stats {output.stats} --tool {params.tool}
        """


if config.get("longest", {}).get("consistency_check", True):
    rule check_longest:
        input:
            pro=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.fasta"),
            cds=os.path.join(RESULTS_DIR, "{species}", "longest", "cds_longest.fasta"),
            mrna=os.path.join(RESULTS_DIR, "{species}", "longest", "mrna_longest.fasta"),
        output:
            report=os.path.join(RESULTS_DIR, "{species}", "longest", "longest_check.json"),
        params:
            python=PYTHON,
            script=os.path.join(BASE_DIR, "workflow", "scripts", "longest", "check_longest_consistency.py"),
        threads: 1
        resources:
            mem_mb=resource("default", "mem_mb") or 2000
        shell:
            """
            set -euo pipefail
            {params.python} {params.script} \
                --pro {input.pro} --cds {input.cds} --mrna {input.mrna} \
                --out {output.report}
            """