"""JBrowse assembly, GFF track and GO/KEGG/TE annotation tracks."""

_FA_CFG = config.get("modules", {}).get("functional_annotation", {})
_JB = config.get("modules", {}).get("jbrowse", {})


def _track_inputs(wildcards):
    """Only request annotation files that this run actually produces."""
    items = []
    if _FA_CFG.get("enabled", True) and _FA_CFG.get("eggnog", True):
        base = os.path.join(RESULTS_DIR, wildcards.species, "annotation", "eggnog")
        items.append(os.path.join(base, "GOannotation.tsv"))
        items.append(os.path.join(base, "KOannotation.tsv"))
    if module_enabled("te"):
        items.append(os.path.join(RESULTS_DIR, wildcards.species, "te",
                                  f"{wildcards.species}.EDTA.TEanno.gff3"))
    return items


if _JB.get("enabled", True):
    rule jbrowse:
        input:
            publish=os.path.join(RESULTS_DIR, "{species}", "publish", "publish.done"),
        output:
            done=os.path.join(RESULTS_DIR, "{species}", "jbrowse", "jbrowse.done"),
        params:
            outdir=os.path.join(PATHS.get("jbrowse_data", ""), "{species}"),
            genome=os.path.join(PATHS.get("genome_by_species", ""), "{species}", "{species}.genome.fa.gz"),
            gff=os.path.join(PATHS.get("genome_by_species", ""), "{species}", "{species}.gff.gz"),
            jbrowse=TOOLS.get("jbrowse", "jbrowse"),
            python=PYTHON,
            config_script=os.path.join(BASE_DIR, "workflow", "scripts", "jbrowse",
                                       "update_jbrowse_config.py"),
            script=os.path.join(BASE_DIR, "workflow", "scripts", "jbrowse", "add_jbrowse.sh"),
        threads: 2
        resources:
            mem_mb=resource("jbrowse", "mem_mb") or 8000
        shell:
            """
            set -euo pipefail
            bash {params.script} {wildcards.species} {params.outdir} \
                {params.genome} {params.gff} {params.jbrowse} {params.python} \
                {params.config_script}
            {params.python} {params.config_script} \
                --config {params.outdir}/config.json --species {wildcards.species} --defaults
            mkdir -p "$(dirname {output.done})"
            touch {output.done}
            """

    if _JB.get("tracks", True):
        rule jbrowse_tracks:
            input:
                publish=os.path.join(RESULTS_DIR, "{species}", "publish", "publish.done"),
                jbrowse=os.path.join(RESULTS_DIR, "{species}", "jbrowse", "jbrowse.done"),
                tracks=_track_inputs,
            output:
                summary=os.path.join(RESULTS_DIR, "{species}", "jbrowse", "tracks.json"),
                done=os.path.join(RESULTS_DIR, "{species}", "jbrowse", "tracks.done"),
            params:
                species="{species}",
                gff=os.path.join(PATHS.get("jbrowse_data", ""), "{species}", "{species}.gff.gz"),
                fai=os.path.join(PATHS.get("jbrowse_data", ""), "{species}", "{species}.genome.fa.gz.fai"),
                go_annotation=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "GOannotation.tsv"),
                ko_annotation=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "KOannotation.tsv"),
                te_gff=os.path.join(RESULTS_DIR, "{species}", "te", "{species}.EDTA.TEanno.gff3"),
                go_obo=TOOLS.get("go_obo", ""),
                kegg_desc=TOOLS.get("kegg_pathway_desc", ""),
                out_dir=PATHS.get("gokegg_track", ""),
                jbrowse_dir=os.path.join(PATHS.get("jbrowse_data", ""), "{species}"),
                bgzip=TOOLS.get("bgzip", "bgzip"),
                tabix=TOOLS.get("tabix", "tabix"),
                python=PYTHON,
                config_script=os.path.join(BASE_DIR, "workflow", "scripts", "jbrowse",
                                           "update_jbrowse_config.py"),
                script=os.path.join(BASE_DIR, "workflow", "scripts", "jbrowse",
                                    "build_jbrowse_tracks.py"),
                te_flag="--te-track" if module_enabled("te") and _JB.get("te_track", True) else "",
                # Always rebuild derived track files when this rule runs. It is
                # triggered by changed annotation/GFF inputs, so reusing an old
                # sorted GFF would silently publish stale GO/KEGG/TE tracks.
                # `publish.overwrite` only controls canonical genome/sequence files.
                force="--force",
            threads: 2
            resources:
                mem_mb=resource("jbrowse", "mem_mb") or 8000
            shell:
                """
                set -euo pipefail
                {params.python} {params.script} --species {wildcards.species} \
                    --gff {params.gff} --fai {params.fai} \
                    --go-annotation {params.go_annotation} \
                    --ko-annotation {params.ko_annotation} \
                    --te-gff {params.te_gff} --go-obo {params.go_obo} \
                    --kegg-desc {params.kegg_desc} --out-dir {params.out_dir} \
                    --jbrowse-dir {params.jbrowse_dir} --bgzip {params.bgzip} \
                    --tabix {params.tabix} {params.te_flag} {params.force} \
                    --summary {output.summary}
                {params.python} {params.config_script} \
                    --config {params.jbrowse_dir}/config.json --species {wildcards.species} --defaults
                touch {output.done}
                """