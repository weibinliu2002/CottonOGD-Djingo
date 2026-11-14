"""id_map rule module: NCBI-metadata-assisted subgenome split + nf-LO Chain generation.

The module reads the existing liftover pairs TSV and produces:
  - a genome registry (ploidy / genome_type / source / fasta path)
  - per-genome chromosome<->NCBI mapping
  - At/Dt subgenome assignment for tetraploids
  - At/Dt (or Whole) sub-FASTAs
  - nf-LO Chain files (LastZ) with validation
  - a unified chain index TSV

Explicitly out of scope (handled by the future web service, not here):
UCSC liftOver, CrossMap, GFF3/BED/VCF coordinate conversion.
"""
import os
import yaml

idmap_cfg = config.get("id_map", {})
ID_MAP_ENABLED = idmap_cfg.get("enabled", False)

if ID_MAP_ENABLED:
    BASE = config["base_dir"]
    RESULTS = os.path.join(BASE, config.get("results_dir", "results"))
    IDMAP_ROOT = idmap_cfg.get("results_dir", os.path.join(RESULTS, "id_map"))

    # Inputs (static files, NOT DAG outputs)
    PAIRS_TSV = os.path.join(BASE, "metadata", "cotton_core_liftover_pairs.tsv")
    GENOME_DIR = idmap_cfg.get("genome_dir",
                               os.path.join(config["paths"]["genome_by_type"], "genome"))
    SPECIES_DIR = idmap_cfg.get("species_dir", os.path.join(BASE, "data", "species"))
    NCBI_BIN = idmap_cfg.get("datasets_bin", "/home/web/bin/datasets")
    NFLO_DIR = idmap_cfg.get("nflo_dir", "/data/wbliu/soft/nf-LO")
    NEXTFLOW_BIN = idmap_cfg.get("nextflow_bin", "/usr/bin/nextflow")

    # Output roots
    NCBI_META_DIR = os.path.join(IDMAP_ROOT, "metadata", "ncbi")
    CHROM_MAP_DIR = os.path.join(IDMAP_ROOT, "metadata", "chromosome_mapping")
    SUBGENOME_DIR = os.path.join(IDMAP_ROOT, "metadata", "subgenome_mapping")
    SPLIT_DIR = os.path.join(IDMAP_ROOT, "intermediate")
    CHAIN_DIR = os.path.join(IDMAP_ROOT, "chain")
    LOG_DIR = os.path.join(IDMAP_ROOT, "logs")

    REGISTRY_TSV = os.path.join(IDMAP_ROOT, "metadata", "genome_registry.tsv")
    TASKS_TSV = os.path.join(IDMAP_ROOT, "metadata", "liftover_tasks.tsv")
    CHAIN_INDEX = os.path.join(IDMAP_ROOT, "chain_index.tsv")
    SUMMARY_TSV = os.path.join(IDMAP_ROOT, "reports", "id_map_summary.tsv")

    ID_MAP_SCRIPTS = os.path.join(BASE, "workflow", "scripts", "id_map")
    PYTHON = config.get("tools", {}).get("python", "python3")

    # ------------------------------------------------------------------ helpers
    def _read_pairs_tsv():
        """Read liftover pairs (STATIC input) -> list of dicts."""
        import csv
        tasks = []
        with open(PAIRS_TSV, "r", encoding="utf-8") as fh:
            for row in csv.DictReader(fh, delimiter="\t"):
                tasks.append(row)
        return tasks

    def _read_metadata(genome_id):
        """Read ploidy/genome_type from metadata.yaml (static input)."""
        meta_path = os.path.join(SPECIES_DIR, genome_id, "metadata.yaml")
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return {
                "ploidy": data.get("ploidy", "unknown"),
                "genome_type": data.get("genome_type", ""),
                "species": data.get("cotton_species", ""),
            }
        return {"ploidy": "unknown", "genome_type": "", "species": ""}

    def _read_registry_accession(genome_id):
        """Look up NCBI accession for a genome from the registry (built file)."""
        if os.path.exists(REGISTRY_TSV):
            import csv
            with open(REGISTRY_TSV, "r", encoding="utf-8") as fh:
                for row in csv.DictReader(fh, delimiter="\t"):
                    if row["genome_id"] == genome_id:
                        return (row.get("ncbi_assembly_accession", "") or "").strip()
        return ""

    def _ncbi_report_path(genome_id):
        return os.path.join(NCBI_META_DIR, genome_id, "sequence_report.jsonl")

    def _is_tetraploid(genome_id):
        m = _read_metadata(genome_id)
        return (m["ploidy"] == "allotetraploid") or (m["genome_type"] or "").startswith("AD")

    def _subgenomes_for_pair(pair):
        """Return list of (src_sub, tgt_sub) chain tasks for a pair."""
        src = pair["source_id"]
        tgt = pair["target_id"]
        src_t = _is_tetraploid(src)
        tgt_t = _is_tetraploid(tgt)
        if not src_t and not tgt_t:
            return [("Whole", "Whole")]
        if src_t and tgt_t:
            return [("At", "At"), ("Dt", "Dt")]
        # diploid<->tetraploid within same species: A-diploid->At, D-diploid->Dt
        def _diploid_sub(gid):
            gt = _read_metadata(gid)["genome_type"]
            if gt.startswith("A"):
                return "At"
            if gt.startswith("D"):
                return "Dt"
            return None
        out = []
        for sg in ("At", "Dt"):
            src_sub = sg if src_t else _diploid_sub(src)
            tgt_sub = sg if tgt_t else _diploid_sub(tgt)
            if src_sub == sg and tgt_sub == sg:
                out.append((sg, sg))
        return out

    def _all_genome_ids():
        gids = set()
        for p in _read_pairs_tsv():
            gids.add(p["source_id"])
            gids.add(p["target_id"])
        return sorted(gids)

    def _pairs_for_chain():
        """Pairs to run chain generation on (config-gated)."""
        selected = idmap_cfg.get("pairs", "test")  # 'test' | 'all' | explicit list
        all_pairs = _read_pairs_tsv()
        if selected == "all":
            return all_pairs
        if selected == "test":
            test_pairs = idmap_cfg.get("test_pairs", [
                ("G.hirsutumAD1_TM-1_HAU_v1.1", "G.hirsutumAD1_TM-1_HAU_v1"),
            ])
            result = []
            for (s, t) in test_pairs:
                for p in all_pairs:
                    if p["source_id"] == s and p["target_id"] == t:
                        result.append(p)
            return result
        # explicit list of (source,target) tuples
        result = []
        for (s, t) in selected:
            for p in all_pairs:
                if p["source_id"] == s and p["target_id"] == t:
                    result.append(p)
        return result

    def _nflo_source_fasta(wc):
        sub = wc.subgenome
        return os.path.join(SPLIT_DIR, wc.source_id, f"{wc.source_id}.{sub if sub != 'Whole' else 'Whole'}.fa")

    def _nflo_target_fasta(wc):
        sub = wc.subgenome
        return os.path.join(SPLIT_DIR, wc.target_id, f"{wc.target_id}.{sub if sub != 'Whole' else 'Whole'}.fa")

    # -------------------------------------------------------------------- rules

    rule all_id_map:
        """Final id_map target: chain index plus summary."""
        input:
            CHAIN_INDEX,
            SUMMARY_TSV,
        default_target: True
        # (no default_target on prep/chain rules; use explicit targets)

    rule prepare_genome_pairs:
        """Build genome registry + liftover task list from pairs TSV."""
        input:
            PAIRS_TSV,
        output:
            registry=REGISTRY_TSV,
            tasks=TASKS_TSV,
        params:
            species_dir=SPECIES_DIR,
            genome_dir=GENOME_DIR,
            script=os.path.join(ID_MAP_SCRIPTS, "build_registry.py"),
        shell:
            "{params.script} --pairs-tsv {input} --species-dir {params.species_dir} "
            "--genome-dir {params.genome_dir} --registry-out {output.registry} "
            "--tasks-out {output.tasks}"

    rule assign_subgenome:
        """Assign At/Dt subgenome to each chromosome (tetraploid) or Whole (diploid)."""
        input:
            fasta=os.path.join(GENOME_DIR, "{genome_id}.fa"),
            config=os.path.join(BASE, "config.yaml"),
        output:
            mapping=os.path.join(SUBGENOME_DIR, "{genome_id}.tsv"),
            summary=os.path.join(SUBGENOME_DIR, "{genome_id}.summary.tsv"),
            unmapped=os.path.join(SUBGENOME_DIR, "{genome_id}.unmapped.tsv"),
        params:
            script=os.path.join(ID_MAP_SCRIPTS, "assign_subgenome.py"),
            ploidy=lambda wc: _read_metadata(wc.genome_id)["ploidy"],
            genome_type=lambda wc: _read_metadata(wc.genome_id)["genome_type"],
            ncbi_report=lambda wc: _ncbi_report_path(wc.genome_id),
            seqkit=idmap_cfg.get("seqkit_bin", "/home/web/bin/seqkit"),
        wildcard_constraints:
            genome_id=r"[A-Za-z0-9_.-]+",
        shell:
            """{params.script} --fasta {input.fasta} --config {input.config} \
                --genome-id {wildcards.genome_id} \
                --genome-type {params.genome_type} --ploidy {params.ploidy} \
                --ncbi-report {params.ncbi_report} --seqkit {params.seqkit} \
                --out-tsv {output.mapping} --out-summary {output.summary} \
                --out-unmapped {output.unmapped}"""

    rule fetch_ncbi_metadata:
        """Fetch and cache NCBI Sequence Report for a genome (optional enrichment)."""
        input:
            registry=REGISTRY_TSV,
        output:
            seq=os.path.join(NCBI_META_DIR, "{genome_id}", "sequence_report.jsonl"),
            genome=os.path.join(NCBI_META_DIR, "{genome_id}", "genome_report.jsonl"),
        params:
            datasets=NCBI_BIN,
            script=os.path.join(ID_MAP_SCRIPTS, "fetch_ncbi.sh"),
            accession=lambda wc: _read_registry_accession(wc.genome_id),
        wildcard_constraints:
            genome_id=r"[A-Za-z0-9_.-]+",
        shell:
            """
            ACC={params.accession};
            if [ -z "$ACC" ]; then
                echo "No NCBI accession for {wildcards.genome_id}; skipping fetch." >&2;
                touch {output.seq} {output.genome};
                exit 0;
            fi;
            OUTDIR=$(dirname {output.seq});
            DATASETS_BIN={params.datasets} bash {params.script} "$ACC" "$OUTDIR"
            """

    rule map_fasta_to_ncbi:
        """Map local FASTA seqids to NCBI Sequence Report entries (NCBI-aware)."""
        input:
            fasta=os.path.join(GENOME_DIR, "{genome_id}.fa"),
            seqreport=os.path.join(NCBI_META_DIR, "{genome_id}", "sequence_report.jsonl"),
        output:
            mapping=os.path.join(CHROM_MAP_DIR, "{genome_id}.tsv"),
            unmapped=os.path.join(CHROM_MAP_DIR, "{genome_id}.unmapped.tsv"),
            ambiguous=os.path.join(CHROM_MAP_DIR, "{genome_id}.ambiguous.tsv"),
        params:
            script=os.path.join(ID_MAP_SCRIPTS, "map_fasta_to_ncbi.py"),
            seqkit=idmap_cfg.get("seqkit_bin", "/home/web/bin/seqkit"),
        wildcard_constraints:
            genome_id=r"[A-Za-z0-9_.-]+",
        shell:
            """{params.script} --fasta {input.fasta} --seqreport {input.seqreport} \
                --genome-id {wildcards.genome_id} --seqkit {params.seqkit} \
                --out-tsv {output.mapping} --unmapped {output.unmapped} \
                --ambiguous {output.ambiguous}"""

    rule split_subgenome_fasta:
        """Split a FASTA into At/Dt (tetraploid) or copy Whole (diploid)."""
        input:
            fasta=os.path.join(GENOME_DIR, "{genome_id}.fa"),
            sub_map=os.path.join(SUBGENOME_DIR, "{genome_id}.tsv"),
        output:
            at=os.path.join(SPLIT_DIR, "{genome_id}", "{genome_id}.At.fa"),
            dt=os.path.join(SPLIT_DIR, "{genome_id}", "{genome_id}.Dt.fa"),
            whole=os.path.join(SPLIT_DIR, "{genome_id}", "{genome_id}.Whole.fa"),
            stats=os.path.join(SPLIT_DIR, "{genome_id}", "split_stats.tsv"),
            id_map=os.path.join(SPLIT_DIR, "{genome_id}", "sequence_id_mapping.tsv"),
            at_list=os.path.join(SPLIT_DIR, "{genome_id}", "at_list.tsv"),
            dt_list=os.path.join(SPLIT_DIR, "{genome_id}", "dt_list.tsv"),
            unassigned=os.path.join(SPLIT_DIR, "{genome_id}", "unassigned_list.tsv"),
        params:
            script=os.path.join(ID_MAP_SCRIPTS, "split_subgenome_fasta.py"),
            outdir=os.path.join(SPLIT_DIR, "{genome_id}"),
            ploidy=lambda wc: _read_metadata(wc.genome_id)["ploidy"],
            seqkit=idmap_cfg.get("seqkit_bin", "/home/web/bin/seqkit"),
        wildcard_constraints:
            genome_id=r"[A-Za-z0-9_.-]+",
        shell:
            """
            mkdir -p {params.outdir};
            {params.script} --fasta {input.fasta} --subgenome-map {input.sub_map} \
                --genome-id {wildcards.genome_id} --ploidy {params.ploidy} \
                --out-at {output.at} --out-dt {output.dt} --out-whole {output.whole} \
                --out-stats {output.stats} \
                --id-map {output.id_map} --at-list {output.at_list} \
                --dt-list {output.dt_list} --unassigned-list {output.unassigned} \
                --seqkit {params.seqkit}
            """

    rule generate_chain:
        """Run nf-LO on one subgenome source->target pair."""
        input:
            src_fa=lambda wc: _nflo_source_fasta(wc),
            tgt_fa=lambda wc: _nflo_target_fasta(wc),
        output:
            chain=os.path.join(CHAIN_DIR, "{source_id}_to_{target_id}", "{subgenome}", "liftover.chain"),
            net=os.path.join(CHAIN_DIR, "{source_id}_to_{target_id}", "{subgenome}", "netfile.net"),
        params:
            script=os.path.join(ID_MAP_SCRIPTS, "run_nflo.sh"),
            workdir=os.path.join(CHAIN_DIR, "{source_id}_to_{target_id}", "{subgenome}", "work"),
            log=os.path.join(LOG_DIR, "{source_id}_to_{target_id}_{subgenome}.log"),
            nflo_dir=NFLO_DIR,
            max_cpus=idmap_cfg.get("nflo_max_cpus", 16),
            max_mem=idmap_cfg.get("nflo_max_memory", "64.GB"),
            max_forks=idmap_cfg.get("nflo_max_forks", 16),
            nextflow_bin=NEXTFLOW_BIN,
            nflo_cwd=BASE,
        threads: idmap_cfg.get("nflo_threads", 16)
        resources:
            mem_mb=idmap_cfg.get("nflo_mem_mb", 64000),
        wildcard_constraints:
            source_id=r"[A-Za-z0-9_.-]+",
            target_id=r"[A-Za-z0-9_.-]+",
            subgenome=r"(At|Dt|Whole)",
        shell:
            """mkdir -p $(dirname {params.log});
            NFLO_DIR={params.nflo_dir} NFLO_MAX_CPUS={params.max_cpus} \
            NFLO_MAX_MEM={params.max_mem} NFLO_MAX_FORKS={params.max_forks} \
            NEXTFLOW_BIN={params.nextflow_bin} \
            NFLO_CWD={params.nflo_cwd} \
            bash {params.script} {params.nflo_dir} {input.src_fa} {input.tgt_fa} \
                {params.workdir} {output.chain} {output.net} {params.log}"""

    rule validate_chain:
        """Validate the generated Chain file."""
        input:
            chain=os.path.join(CHAIN_DIR, "{source_id}_to_{target_id}", "{subgenome}", "liftover.chain"),
            net=os.path.join(CHAIN_DIR, "{source_id}_to_{target_id}", "{subgenome}", "netfile.net"),
            src_fa=lambda wc: _nflo_source_fasta(wc),
            tgt_fa=lambda wc: _nflo_target_fasta(wc),
        output:
            val=os.path.join(CHAIN_DIR, "{source_id}_to_{target_id}", "{subgenome}", "validation.tsv"),
        params:
            script=os.path.join(ID_MAP_SCRIPTS, "validate_chain.py"),
            seqkit=idmap_cfg.get("seqkit_bin", "/home/web/bin/seqkit"),
        wildcard_constraints:
            source_id=r"[A-Za-z0-9_.-]+",
            target_id=r"[A-Za-z0-9_.-]+",
            subgenome=r"(At|Dt|Whole)",
        shell:
            """{params.script} --chain {input.chain} --net {input.net} \
                --source-fasta {input.src_fa} --target-fasta {input.tgt_fa} \
                --source-id {wildcards.source_id} --target-id {wildcards.target_id} \
                --subgenome {wildcards.subgenome} --seqkit {params.seqkit} \
                --out {output.val}"""

    rule build_chain_index:
        """Aggregate all validated chains into the unified index TSV."""
        input:
            registry=REGISTRY_TSV,
            pairs=TASKS_TSV,
        output:
            index=CHAIN_INDEX,
        params:
            script=os.path.join(ID_MAP_SCRIPTS, "build_chain_index.py"),
            chain_root=CHAIN_DIR,
            intermediate_root=SPLIT_DIR,
            nflo_version=idmap_cfg.get("nflo_version", "1.8.8"),
            aligner=idmap_cfg.get("aligner", "lastz"),
        shell:
            """{params.script} --registry {input.registry} --pairs-tsv {input.pairs} \
                --chain-root {params.chain_root} --intermediate-root {params.intermediate_root} \
                --out {output.index} --nflo-version {params.nflo_version} --aligner {params.aligner}"""

    rule id_map_summary:
        """Produce the id_map summary report."""
        input:
            index=CHAIN_INDEX,
        output:
            summary=SUMMARY_TSV,
        shell:
            """{python} -c "import csv; rows=list(csv.DictReader(open('{input.index}'),delimiter='\\t')); tot=len(rows); ok=sum(1 for r in rows if r['status']=='OK'); wc=sum(1 for r in rows if 'chain' in r['status'] or r['status']=='OK'); spe=set(r['species'] for r in rows); print('species\\ttasks\\tok\\twith_chain'); print(f"{{len(spe)}}\\t{{tot}}\\t{{ok}}\\t{{wc}}")" > {output.summary}"""

    # ------------------------------------------------------------------ targets
    # Assign-level targets (metadata preparation, no nf-LO)
    # These run for all genomes once metadata is ready.
    if idmap_cfg.get("run_prep", True):
        _prep_targets = []
        for gid in _all_genome_ids():
            _prep_targets.append(os.path.join(SUBGENOME_DIR, f"{gid}.tsv"))
            _prep_targets.append(os.path.join(SUBGENOME_DIR, f"{gid}.summary.tsv"))
        rule all_id_map_prep:
            """Prepare subgenome assignment metadata for all genomes."""
            input:
                _prep_targets

    # Chain-generation targets: test pair(s) by default
    _chain_pairs = _pairs_for_chain()
    _chain_targets = []
    for p in _chain_pairs:
        for (ssub, tsub) in _subgenomes_for_pair(p):
            _chain_targets.append(os.path.join(
                CHAIN_DIR, f"{p['source_id']}_to_{p['target_id']}", ssub, "validation.tsv"))
    if _chain_targets:
        rule all_id_map_chains:
            """Run nf-LO + validation for configured chain pairs."""
            input:
                _chain_targets