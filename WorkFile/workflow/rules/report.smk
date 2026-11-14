"""Batch summary report across all selected species."""


def _report_inputs(wildcards):
    items = []
    for sample in SAMPLES:
        sid = sample["id"]
        items.append(os.path.join(RESULTS_DIR, sid, "qc", "qc_report.yaml"))
        if config.get("upload", {}).get("enabled", True):
            items.append(os.path.join(RESULTS_DIR, sid, "upload", "upload.done"))
        if module_enabled("jbrowse"):
            items.append(os.path.join(RESULTS_DIR, sid, "jbrowse", "jbrowse.done"))
            if module_opt("jbrowse", "tracks", True):
                items.append(os.path.join(RESULTS_DIR, sid, "jbrowse", "tracks.done"))
        if module_enabled("blast"):
            items.append(os.path.join(RESULTS_DIR, sid, "blast", "blast.done"))
    return items


rule aggregate_report:
    input:
        report_files=_report_inputs,
    output:
        # summary 报表是跨基因组的聚合产物，留在 results/ 根目录（RESULTS_ROOT）。
        tsv=os.path.join(RESULTS_ROOT, "summary.tsv"),
        html=os.path.join(RESULTS_ROOT, "summary.html"),
    params:
        python=PYTHON,
        script=os.path.join(BASE_DIR, "workflow", "scripts", "aggregate_report.py"),
        # 传给聚合脚本的根目录是基因组结果根（results/genome/），
        # 脚本会在其下逐个查找带 qc/qc_report.yaml 的物种目录。
        results_dir=RESULTS_DIR,
    threads: 1
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        {params.python} {params.script} --mode summary --results-dir {params.results_dir} \
            --out-tsv {output.tsv} --out-html {output.html}
        """