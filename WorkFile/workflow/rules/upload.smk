"""Upload results to MySQL (dry-run by default)."""


def _upload_inputs(wildcards):
    items = [
        os.path.join(RESULTS_DIR, wildcards.species, "qc", "qc_report.yaml"),
        os.path.join(RESULTS_DIR, wildcards.species, "publish", "publish.done"),
    ]
    fa = config.get("modules", {}).get("functional_annotation", {})
    if fa.get("enabled", True) and fa.get("eggnog", True):
        base = os.path.join(RESULTS_DIR, wildcards.species, "annotation", "eggnog")
        items += [os.path.join(base, "GOannotation.tsv"), os.path.join(base, "KOannotation.tsv"),
                  os.path.join(base, "eggnog.tsv")]
    if fa.get("enabled", True) and fa.get("itak", True):
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "annotation", "itak", "itak.tsv"))
    if fa.get("enabled", True) and fa.get("uniprot", True):
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "annotation", "uniprot",
                                  "Final_Annotation.tsv"))
    if fa.get("enabled", True) and fa.get("interproscan", True):
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "annotation", "interproscan",
                                  "interproscan.tsv"))
    if module_enabled("te"):
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "qc", "te.json"))
    return items


if config.get("upload", {}).get("enabled", True):
    rule upload_to_db:
        input:
            upload_files=_upload_inputs,
            metadata=lambda w: spath(w, "metadata"),
            genome=lambda w: spath(w, "genome"),
            gff=lambda w: spath(w, "gff"),
        output:
            report=os.path.join(RESULTS_DIR, "{species}", "upload", "upload_report.json"),
            done=os.path.join(RESULTS_DIR, "{species}", "upload", "upload.done"),
        params:
            python=PYTHON,
            script=os.path.join(BASE_DIR, "workflow", "scripts", "db_upload.py"),
            config=CONFIG_FILE,
            samples=(f"--samples {SAMPLES_FILE}" if os.path.exists(SAMPLES_FILE) else ""),
            results_dir=RESULTS_DIR,
            apply="--apply --yes" if not config.get("upload", {}).get("dry_run", True) else "--dry-run",
            policy=config.get("upload", {}).get("conflict_policy", "skip"),
            verbose="--verbose" if config.get("upload", {}).get("verbose", False) else "",
        threads: 1
        resources:
            mem_mb=resource("qc", "mem_mb") or 8000
        shell:
            """
            set -euo pipefail
            mkdir -p "$(dirname {output.report})"
            {params.python} {params.script} --config {params.config} \
                {params.samples} --species {wildcards.species} \
                --results-dir {params.results_dir} --policy {params.policy} \
                --sample-genome {input.genome} --sample-gff {input.gff} \
                --sample-metadata {input.metadata} {params.apply} {params.verbose}
            touch {output.done}
            """