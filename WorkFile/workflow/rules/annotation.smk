"""Functional annotation: eggNOG/GO/KEGG, iTAK, UniProt and InterProScan.

Each branch is independently switchable under modules.functional_annotation.
The master switch disables all four branches; a missing optional input (for
example a species without a protein FASTA) fails early in validate_input.
"""
import os

_FA = config.get("modules", {}).get("functional_annotation", {})
_FA_ENABLED = bool(_FA.get("enabled", True))


# UniProt BLASTP has also been run for part of the collection outside this
# workflow. Those results are flat `<species>_{blast,diamond}_uniprot_annotation.txt`
# files (12-column m8, no header) in one directory. `blast` is preferred because
# a number of the `diamond` files are empty. Configure under `reuse.uniprot`.
_UNIPROT_LEGACY_PATTERNS = [
    "{species}_blast_uniprot_annotation.txt",
    "{species}_diamond_uniprot_annotation.txt",
]


# iTAK has been run for most species outside this workflow. Its results live in
# `<species>.pro` directories holding the same three filenames this rule emits,
# so they can be adopted directly. Configure under `reuse.itak`.
_ITAK_DIRS = ["{species}.pro", "{species}"]
_ITAK_FILES = {
    "tf": "tf_classification.txt",
    "shiu": "shiu_classification.txt",
    "combined": "tf_tr_kinase_with_uniprot.txt",
}


def itak_result(wildcards, key):
    """Resolved iTAK output for `key`: legacy file when reusable, else own output."""
    legacy = legacy_file("itak", wildcards.species, _ITAK_FILES[key], _ITAK_DIRS)
    if legacy:
        return legacy
    return os.path.join(RESULTS_DIR, wildcards.species, "annotation", "itak",
                        _ITAK_FILES[key])


def uniprot_hits(wildcards):
    """Resolved best_hits.m8: legacy file when reusable, else this run's output."""
    legacy = legacy_flat_file("uniprot", wildcards.species, _UNIPROT_LEGACY_PATTERNS)
    if legacy:
        return legacy
    return os.path.join(RESULTS_DIR, wildcards.species, "annotation", "uniprot",
                        "best_hits.m8")


def annotation_proteins(wildcards):
    """Protein FASTA used as query for all annotation tools."""
    if _FA.get("use_longest_proteins", False):
        return os.path.join(RESULTS_DIR, wildcards.species, "longest", "pro_longest.fasta")
    return os.path.join(RESULTS_DIR, wildcards.species, "sequences", "pro.fa")


# eggNOG-mapper has already been run for most species outside this workflow
# (legacy dir, one directory per species holding `<species>.emapper.annotations`).
# Those runs are adopted instead of recomputed: `run_eggnog` is then skipped and
# `parse_eggnog` reads the legacy file directly. Configure under `reuse.eggnog`
# in config.yaml; `reuse.exclude` forces a recompute for listed species.
def eggnog_annotations(wildcards):
    """Resolved *.emapper.annotations: legacy result when reusable, else own output."""
    legacy = legacy_file("eggnog", wildcards.species,
                         f"{wildcards.species}.emapper.annotations")
    if legacy:
        return legacy
    return os.path.join(RESULTS_DIR, wildcards.species, "annotation", "eggnog",
                        f"{wildcards.species}.emapper.annotations")


if _FA_ENABLED:
    if _FA.get("eggnog", True):
        rule run_eggnog:
            input:
                proteins=annotation_proteins,
                validation=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
            output:
                annotations=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "{species}.emapper.annotations"),
                hits=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "{species}.emapper.hits"),
                orthologs=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "{species}.emapper.seed_orthologs"),
            params:
                outdir=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog"),
                prefix="{species}",
                mapper=TOOLS.get("eggnog_mapper", "emapper.py"),
                data_dir=TOOLS.get("eggnog_data_dir", ""),
                temp_dir=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "tmp"),
                python=PYTHON,
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "run_eggnog.sh"),
            threads: _FA.get("eggnog_threads", 16)
            resources:
                mem_mb=resource("eggnog", "mem_mb") or 32000
            shell:
                """
                set -euo pipefail
                bash {params.script} {input.proteins} {params.outdir} {params.prefix} \
                    {threads} {params.mapper} {params.data_dir} {params.temp_dir} \
                    {params.python}
                """

        rule parse_eggnog:
            input:
                # Either the legacy result (run_eggnog skipped) or this run's output.
                annotations=eggnog_annotations,
            output:
                go=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "GOannotation.tsv"),
                ko=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "KOannotation.tsv"),
                detail=os.path.join(RESULTS_DIR, "{species}", "annotation", "eggnog", "eggnog.tsv"),
            params:
                python=PYTHON,
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "parse_eggnog.py"),
                vendor=os.path.join(BASE_DIR, "workflow", "scripts", "vendor", "parse_eggNOG.py"),
                go_obo=TOOLS.get("go_obo", ""),
                kegg_desc=TOOLS.get("kegg_pathway_desc", ""),
                cache_dir=os.path.join(BASE_DIR, "workflow", "cache", "kegg"),
                orgs=",".join(_FA.get("eggnog_kegg_orgs", ["all"])),
                offline="--offline" if _FA.get("eggnog_offline", False) else "",
            threads: 1
            resources:
                mem_mb=resource("qc", "mem_mb") or 8000
            shell:
                """
                set -euo pipefail
                {params.python} {params.script} \
                    --input {input.annotations} --outdir "$(dirname {output.go})" \
                    --vendor {params.vendor} --go-obo {params.go_obo} \
                    --kegg-desc {params.kegg_desc} --cache-dir {params.cache_dir} \
                    --orgs {params.orgs} {params.offline}
                """

    if _FA.get("itak", True):
        # `run_itak` emits three files, but only tf/shiu feed `parse_itak`; the
        # combined table is kept for reference. Snakemake still has to produce
        # it, so reuse must cover all three or the rule is not skipped at all.
        def itak_reusable(wildcards):
            """True when all three legacy iTAK outputs exist for this species."""
            return all(
                legacy_file("itak", wildcards.species, _ITAK_FILES[k], _ITAK_DIRS)
                for k in ("tf", "shiu", "combined")
            )

        rule run_itak:
            input:
                proteins=annotation_proteins,
                validation=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
            output:
                tf=os.path.join(RESULTS_DIR, "{species}", "annotation", "itak", "tf_classification.txt"),
                shiu=os.path.join(RESULTS_DIR, "{species}", "annotation", "itak", "shiu_classification.txt"),
                combined=os.path.join(RESULTS_DIR, "{species}", "annotation", "itak", "tf_tr_kinase_with_uniprot.txt"),
            params:
                outdir=os.path.join(RESULTS_DIR, "{species}", "annotation", "itak"),
                prefix="{species}",
                python=TOOLS.get("itak_python", PYTHON),
                itak=TOOLS.get("itak", "iTAK.py"),
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "run_itak.sh"),
                # Adopt finished legacy results instead of recomputing; the
                # legacy dirs are read-only, so copy and never move/delete.
                legacy_tf=lambda w: legacy_file("itak", w.species, _ITAK_FILES["tf"], _ITAK_DIRS),
                legacy_shiu=lambda w: legacy_file("itak", w.species, _ITAK_FILES["shiu"], _ITAK_DIRS),
                legacy_combined=lambda w: legacy_file("itak", w.species, _ITAK_FILES["combined"], _ITAK_DIRS),
            threads: _FA.get("itak_threads", 8)
            resources:
                mem_mb=resource("itak", "mem_mb") or 8000
            shell:
                """
                set -euo pipefail
                mkdir -p {params.outdir}
                if [ -n "{params.legacy_tf}" ] && [ -n "{params.legacy_shiu}" ] && [ -n "{params.legacy_combined}" ]; then
                    echo "[INFO] adopting legacy iTAK results for {params.prefix}"
                    cp -n "{params.legacy_tf}" {output.tf}
                    cp -n "{params.legacy_shiu}" {output.shiu}
                    cp -n "{params.legacy_combined}" {output.combined}
                    exit 0
                fi
                bash {params.script} {input.proteins} {params.outdir} {params.prefix} \
                    {threads} {params.python} {params.itak}
                """

        rule parse_itak:
            input:
                tf=os.path.join(RESULTS_DIR, "{species}", "annotation", "itak", "tf_classification.txt"),
                shiu=os.path.join(RESULTS_DIR, "{species}", "annotation", "itak", "shiu_classification.txt"),
            output:
                tsv=os.path.join(RESULTS_DIR, "{species}", "annotation", "itak", "itak.tsv"),
            params:
                python=PYTHON,
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "parse_itak.py"),
            threads: 1
            resources:
                mem_mb=resource("qc", "mem_mb") or 8000
            shell:
                """
                set -euo pipefail
                {params.python} {params.script} --tf {input.tf} --shiu {input.shiu} \
                    --out {output.tsv}
                """

    if _FA.get("uniprot", True):
        rule run_uniprot:
            input:
                proteins=annotation_proteins,
                validation=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
            output:
                m8=os.path.join(RESULTS_DIR, "{species}", "annotation", "uniprot", "best_hits.m8"),
            params:
                outdir=os.path.join(RESULTS_DIR, "{species}", "annotation", "uniprot"),
                tmp=os.path.join(RESULTS_DIR, "{species}", "annotation", "uniprot", "tmp"),
                db=TOOLS.get("uniprot_db", ""),
                blastp=TOOLS.get("blastp", "blastp"),
                evalue=_FA.get("uniprot_evalue", "1e-5"),
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "run_uniprot.sh"),
            threads: _FA.get("uniprot_threads", 16)
            resources:
                mem_mb=resource("uniprot", "mem_mb") or 16000
            shell:
                """
                set -euo pipefail
                bash {params.script} {input.proteins} {params.db} {output.m8} \
                    {params.tmp} {threads} {params.evalue} {params.blastp}
                """

        rule parse_uniprot:
            input:
                # Either the legacy hit table (run_uniprot skipped) or this run's output.
                m8=uniprot_hits,
            output:
                tsv=os.path.join(RESULTS_DIR, "{species}", "annotation", "uniprot", "Final_Annotation.tsv"),
            params:
                python=PYTHON,
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "parse_uniprot.py"),
                fasta=TOOLS.get("uniprot_fasta", ""),
            threads: 1
            resources:
                mem_mb=resource("qc", "mem_mb") or 16000
            shell:
                """
                set -euo pipefail
                {params.python} {params.script} --m8 {input.m8} \
                    --uniprot-fasta {params.fasta} --out {output.tsv}
                """

    if _FA.get("interproscan", True):
        rule run_interproscan:
            input:
                proteins=annotation_proteins,
                validation=os.path.join(RESULTS_DIR, "{species}", "validated", "validation.done"),
            output:
                tsv=os.path.join(RESULTS_DIR, "{species}", "annotation", "interproscan", "{species}.tsv"),
            params:
                outdir=os.path.join(RESULTS_DIR, "{species}", "annotation", "interproscan"),
                prefix="{species}",
                interproscan=TOOLS.get("interproscan", "interproscan.sh"),
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "run_interproscan.sh"),
            threads: _FA.get("interproscan_threads", 16)
            resources:
                mem_mb=resource("interpro", "mem_mb") or 16000
            shell:
                """
                set -euo pipefail
                bash {params.script} {input.proteins} {params.outdir} {params.prefix} \
                    {threads} {params.interproscan}
                """

        rule parse_interproscan:
            input:
                tsv=os.path.join(RESULTS_DIR, "{species}", "annotation", "interproscan", "{species}.tsv"),
            output:
                tsv=os.path.join(RESULTS_DIR, "{species}", "annotation", "interproscan", "interproscan.tsv"),
            params:
                python=PYTHON,
                script=os.path.join(BASE_DIR, "workflow", "scripts", "annotation", "parse_interproscan.py"),
            threads: 1
            resources:
                mem_mb=resource("qc", "mem_mb") or 8000
            shell:
                """
                set -euo pipefail
                {params.python} {params.script} --input {input.tsv} --out {output.tsv}
                """