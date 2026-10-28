"""BLAST database construction (mirrors legacy add_blast_db.sh)."""

if module_enabled("blast"):
    rule build_blast_db:
        input:
            publish=os.path.join(RESULTS_DIR, "{species}", "publish", "publish.done"),
            pro_longest=os.path.join(RESULTS_DIR, "{species}", "longest", "pro_longest.fasta"),
            cds_longest=os.path.join(RESULTS_DIR, "{species}", "longest", "cds_longest.fasta"),
            mrna_longest=os.path.join(RESULTS_DIR, "{species}", "longest", "mrna_longest.fasta"),
        output:
            done=os.path.join(RESULTS_DIR, "{species}", "blast", "blast.done"),
        params:
            db_root=PATHS.get("blast_db", ""),
            genome=os.path.join(PATHS.get("genome_by_type", ""), "genome", "{species}.genome.fa.gz"),
            mrna=os.path.join(PATHS.get("genome_by_type", ""), "mrna", "{species}.mrna_longest.fasta"),
            cds=os.path.join(PATHS.get("genome_by_type", ""), "cds", "{species}.cds_longest.fasta"),
            protein=os.path.join(PATHS.get("genome_by_type", ""), "pep", "{species}.pro_longest.fasta"),
            workdir=os.path.join(RESULTS_DIR, "{species}", "blast"),
            makeblastdb=TOOLS.get("makeblastdb", "makeblastdb"),
            script=os.path.join(BASE_DIR, "workflow", "scripts", "blast", "build_blast_db.sh"),
        threads: 8
        resources:
            mem_mb=resource("blast", "mem_mb") or 16000
        shell:
            """
            set -euo pipefail
            bash {params.script} {wildcards.species} {params.db_root} \
                {params.genome} {params.mrna} {params.cds} {params.protein} \
                {params.makeblastdb} {params.workdir}
            touch {output.done}
            """