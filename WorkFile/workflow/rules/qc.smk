"""Genome size, LAI/LTR and BUSCO QC."""


def _qc_inputs(wildcards):
    """Ask only for QC branches that are enabled and not already in MySQL.

    Samples may declare ``qc_completed: [genome_size, lai, busco]`` in
    samples.yaml. For those metrics the existing value is copied from
    metadata.yaml -> existing_qc by aggregate_report.py, so the expensive rule
    is not added to the DAG at all.
    """
    done = qc_completed(wildcards)
    items = [os.path.join(RESULTS_DIR, wildcards.species, "validated", "validation.json")]
    if "genome_size" not in done:
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "qc", "genome_size.json"))
    if config.get("qc", {}).get("lai", {}).get("enabled", True) and "lai" not in done:
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "qc", "lai.json"))
    if config.get("qc", {}).get("busco", {}).get("enabled", True) and "busco" not in done:
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "qc", "busco.json"))
    if module_enabled("te"):
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "qc", "te.json"))
    return items

rule calc_genome_size:
    input:
        genome=lambda w: spath(w, "genome"),
    output:
        json=os.path.join(RESULTS_DIR, "{species}", "qc", "genome_size.json"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "qc", "calc_genome_size.py"),
    threads: 1
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        mkdir -p "$(dirname {output.json})"
        {params.python} {params.script} --genome {input.genome} --out {output.json}
        """


if config.get("qc", {}).get("lai", {}).get("enabled", True):
    rule prepare_lai_genome:
        input:
            genome=lambda w: spath(w, "genome"),
        output:
            fasta=os.path.join(RESULTS_DIR, "{species}", "lai", "genome.renamed.fa"),
            map=os.path.join(RESULTS_DIR, "{species}", "lai", "id_map.tsv"),
        params:
            python=PYTHON,
            script=os.path.join(BASE_DIR, "workflow", "scripts", "qc", "prepare_lai_genome.py"),
        threads: 1
        resources:
            mem_mb=resource("qc", "mem_mb") or 8000
        shell:
            """
            set -euo pipefail
            mkdir -p "$(dirname {output.fasta})"
            {params.python} {params.script} --genome {input.genome} \
                --out-fasta {output.fasta} --out-map {output.map}
            """

    rule ltr_annotation:
        input:
            genome=os.path.join(RESULTS_DIR, "{species}", "lai", "genome.renamed.fa"),
        output:
            raw=os.path.join(RESULTS_DIR, "{species}", "lai", "{species}.rawLTR.scn"),
            pass_list=os.path.join(RESULTS_DIR, "{species}", "lai", "genome.renamed.fa.pass.list"),
            out=os.path.join(RESULTS_DIR, "{species}", "lai", "genome.renamed.fa.out"),
        params:
            outdir=os.path.join(RESULTS_DIR, "{species}", "lai"),
            prefix="{species}",
            ltr_finder_threads=config.get("qc", {}).get("lai", {}).get("ltr_finder_threads", 7),
            ltr_retriever_threads=config.get("qc", {}).get("lai", {}).get("ltr_retriever_threads", 35),
            size=config.get("qc", {}).get("lai", {}).get("ltr_finder_size", 1000000),
            time=config.get("qc", {}).get("lai", {}).get("ltr_finder_time", 300),
            ltr_finder=TOOLS.get("ltr_finder_parallel", "LTR_FINDER_parallel"),
            gt=TOOLS.get("gt", "gt"),
            ltr_retriever=TOOLS.get("ltr_retriever", "LTR_retriever"),
            script=os.path.join(BASE_DIR, "workflow", "scripts", "qc", "run_ltr.sh"),
        threads: config.get("qc", {}).get("lai", {}).get("ltr_finder_threads", 7)
        resources:
            mem_mb=resource("ltr", "mem_mb") or 32000
        shell:
            """
            set -euo pipefail
            bash {params.script} {input.genome} {params.outdir} {params.prefix} \
                {params.ltr_finder_threads} {params.ltr_retriever_threads} \
                {params.size} {params.time} {params.ltr_finder} {params.gt} \
                {params.ltr_retriever}
            """

    rule run_lai:
        input:
            pass_list=os.path.join(RESULTS_DIR, "{species}", "lai", "genome.renamed.fa.pass.list"),
            out=os.path.join(RESULTS_DIR, "{species}", "lai", "genome.renamed.fa.out"),
        output:
            lai=os.path.join(RESULTS_DIR, "{species}", "lai", "{species}.out.LAI"),
        params:
            outdir=os.path.join(RESULTS_DIR, "{species}", "lai"),
            prefix="{species}",
            genome=os.path.join(RESULTS_DIR, "{species}", "lai", "genome.renamed.fa"),
            threads=config.get("qc", {}).get("lai", {}).get("lai_threads", 20),
            lai=TOOLS.get("lai", "LAI"),
            script=os.path.join(BASE_DIR, "workflow", "scripts", "qc", "run_lai.sh"),
        threads: config.get("qc", {}).get("lai", {}).get("lai_threads", 20)
        resources:
            mem_mb=resource("lai", "mem_mb") or 32000
        shell:
            """
            set -euo pipefail
            bash {params.script} {params.genome} {params.outdir} {params.prefix} \
                {params.threads} {params.lai}
            """

    rule parse_lai:
        input:
            lai=os.path.join(RESULTS_DIR, "{species}", "lai", "{species}.out.LAI"),
        output:
            json=os.path.join(RESULTS_DIR, "{species}", "qc", "lai.json"),
        params:
            python=PYTHON,
            script=os.path.join(BASE_DIR, "workflow", "scripts", "qc", "parse_lai.py"),
        threads: 1
        resources:
            mem_mb=resource("qc", "mem_mb") or 8000
        shell:
            """
            set -euo pipefail
            {params.python} {params.script} --input {input.lai} --out {output.json}
            """


if config.get("qc", {}).get("busco", {}).get("enabled", True):
    rule run_busco:
        input:
            proteins=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.fasta"),
        output:
            outdir=directory(os.path.join(RESULTS_DIR, "{species}", "busco", "{species}")),
        params:
            busco=TOOLS.get("busco", "busco"),
            lineage=os.path.join(
                TOOLS.get("busco_lineage_dir", ""),
                config.get("qc", {}).get("busco", {}).get("lineage", "eudicots_odb10"),
            ),
            augustus=config.get("qc", {}).get("busco", {}).get("augustus_species", "Arabidopsis"),
            prefix="{species}",
            script=os.path.join(BASE_DIR, "workflow", "scripts", "qc", "run_busco.sh"),
        threads: config.get("qc", {}).get("busco", {}).get("threads", 10)
        resources:
            mem_mb=resource("busco", "mem_mb") or 16000
        shell:
            """
            set -euo pipefail
            bash {params.script} {input.proteins} {output.outdir} {params.prefix} \
                {params.lineage} {params.augustus} {threads} {params.busco}
            """

    rule parse_busco:
        input:
            outdir=os.path.join(RESULTS_DIR, "{species}", "busco", "{species}"),
        output:
            json=os.path.join(RESULTS_DIR, "{species}", "qc", "busco.json"),
        params:
            python=PYTHON,
            script=os.path.join(BASE_DIR, "workflow", "scripts", "qc", "parse_busco.py"),
            lineage=config.get("qc", {}).get("busco", {}).get("lineage", "eudicots_odb10"),
        threads: 1
        resources:
            mem_mb=resource("qc", "mem_mb") or 8000
        shell:
            """
            set -euo pipefail
            {params.python} {params.script} --input {input.outdir} --out {output.json} \
                --lineage {params.lineage}
            """

rule qc_report:
    input:
        qc_files=_qc_inputs,
        metadata=lambda w: spath(w, "metadata"),
    output:
        yaml=os.path.join(RESULTS_DIR, "{species}", "qc", "qc_report.yaml"),
        json=os.path.join(RESULTS_DIR, "{species}", "qc", "qc_report.json"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "aggregate_report.py"),
        validation=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.json"),
        genome_size=os.path.join(RESULTS_DIR, "{species}", "qc", "genome_size.json"),
        lai=os.path.join(RESULTS_DIR, "{species}", "qc", "lai.json"),
        busco=os.path.join(RESULTS_DIR, "{species}", "qc", "busco.json"),
        te=os.path.join(RESULTS_DIR, "{species}", "qc", "te.json"),
    threads: 1
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        {params.python} {params.script} --mode qc --species {wildcards.species} \
            --metadata {input.metadata} --validation {params.validation} \
            --genome-size {params.genome_size} --lai {params.lai} \
            --busco {params.busco} --te {params.te} \
            --out-yaml {output.yaml} --out-json {output.json}
        """
