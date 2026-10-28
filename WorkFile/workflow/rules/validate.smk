"""Input validation. This is the root of every per-species DAG branch."""

rule validate_input:
    input:
        genome=lambda w: spath(w, "genome"),
        gff=lambda w: spath(w, "gff"),
        metadata=lambda w: spath(w, "metadata"),
    output:
        report=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.json"),
        done=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "validate_input.py"),
        species="{species}",
        allow_id_alias=("--allow-id-alias" if config.get("validate", {}).get("allow_id_alias", False) else ""),
    threads: 1
    resources:
        mem_mb=resource("validate", "mem_mb") or 2000
    shell:
        """
        set -euo pipefail
        mkdir -p "$(dirname {output.report})"
        {params.python} {params.script} \
            --species {params.species} \
            --genome {input.genome} \
            --gff {input.gff} \
            --metadata {input.metadata} \
            --out {output.report} \
            {params.allow_id_alias}
        touch {output.done}
        """