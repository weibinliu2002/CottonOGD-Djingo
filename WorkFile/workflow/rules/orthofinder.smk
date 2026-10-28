"""OrthoFinder placeholder (disabled by default).

The I/O contract is fixed now so enabling this branch later needs no changes
elsewhere:

    input : directory of one longest-protein FASTA per species
    output: OrthoFinder results directory

Future incremental strategy (see README):
  1. run a full analysis once on the core species set;
  2. add all remaining species with `orthofinder --assign ... --core ...`;
  3. for new species use the same `--assign`/`--core` flow instead of a full
     rerun. Note: OrthoFinder 3.x `-op` only prepares input files; it does not
     append species, so it must not be used for incremental updates.
"""

rule prepare_orthofinder_inputs:
    output:
        directory(os.path.join(RESULTS_DIR, "orthofinder", "input")),
    params:
        longest=lambda w: [
            os.path.join(RESULTS_DIR, s["id"], "longest", "pro_longest.fasta")
            for s in SAMPLES
        ],
    threads: 1
    resources:
        mem_mb=resource("qc", "mem_mb") or 8000
    shell:
        """
        set -euo pipefail
        mkdir -p {output}
        for f in {params.longest}; do
            ln -sf "$(readlink -f "$f")" "{output}/$(basename "$(dirname "$(dirname "$f")")").pro.fa"
        done
        """


rule orthofinder:
    input:
        proteins=os.path.join(RESULTS_DIR, "orthofinder", "input"),
    output:
        done=os.path.join(RESULTS_DIR, "orthofinder", "orthofinder.done"),
    params:
        outdir=os.path.join(RESULTS_DIR, "orthofinder", "results"),
        orthofinder=TOOLS.get("orthofinder", "orthofinder"),
        threads=module_opt("orthofinder", "threads", 32),
        search=module_opt("orthofinder", "search", "diamond"),
    threads: module_opt("orthofinder", "threads", 32)
    resources:
        mem_mb=resource("orthofinder", "mem_mb") or 64000
    shell:
        """
        set -euo pipefail
        mkdir -p {params.outdir}
        {params.orthofinder} -f {input.proteins} -t {params.threads} \
            -a {params.threads} -S {params.search} -o {params.outdir}
        touch {output.done}
        """