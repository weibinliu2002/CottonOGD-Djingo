"""Transposable element annotation with EDTA (disabled by default)."""

if module_enabled("te"):
    rule run_edta:
        input:
            genome=lambda w: spath(w, "genome"),
            cds=lambda w: os.path.join(RESULTS_DIR, w.species, "sequences", "cds.fa"),
            validation=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
        output:
            gff=os.path.join(RESULTS_DIR, "{species}", "te", "{species}.EDTA.TEanno.gff3"),
            sum=os.path.join(RESULTS_DIR, "{species}", "te", "{species}.EDTA.TEanno.sum"),
        params:
            outdir=os.path.join(RESULTS_DIR, "{species}", "te"),
            prefix="{species}",
            species_name=module_opt("te", "species", "others"),
            sensitive=module_opt("te", "sensitive", 1),
            edta=TOOLS.get("edta", "EDTA.pl"),
            script=os.path.join(BASE_DIR, "workflow", "scripts", "te", "run_edta.sh"),
        threads: module_opt("te", "threads", 32)
        resources:
            mem_mb=resource("edta", "mem_mb") or 64000
        shell:
            """
            set -euo pipefail
            bash {params.script} {input.genome} {input.cds} {params.outdir} \
                {params.prefix} {threads} {params.sensitive} {params.species_name} \
                {params.edta}
            """

    rule parse_te:
        input:
            gff=os.path.join(RESULTS_DIR, "{species}", "te", "{species}.EDTA.TEanno.gff3"),
            sum=os.path.join(RESULTS_DIR, "{species}", "te", "{species}.EDTA.TEanno.sum"),
            metadata=lambda w: spath(w, "metadata"),
        output:
            json=os.path.join(RESULTS_DIR, "{species}", "qc", "te.json"),
        params:
            python=PYTHON,
            script=os.path.join(BASE_DIR, "workflow", "scripts", "te", "parse_te.py"),
            # The JSON may not exist when genome_size was already recorded in
            # MySQL; parse_te.py then falls back to metadata.existing_qc.
            genome_size=os.path.join(RESULTS_DIR, "{species}", "qc", "genome_size.json"),
        threads: 1
        resources:
            mem_mb=resource("qc", "mem_mb") or 8000
        shell:
            """
            set -euo pipefail
            {params.python} {params.script} --gff {input.gff} --sum {input.sum} \
                --genome-size {params.genome_size} --metadata {input.metadata} \
                --out {output.json}
            """