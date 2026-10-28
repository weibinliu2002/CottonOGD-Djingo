#!/usr/bin/env python3
"""Rewrite one species' JBrowse config for the backend large-file service.

The backend serves JBrowse data through `/jbrowse/large/{species}/{file}`
(see `views/jbrowes_file.py`), not through Django static URLs. This script
updates assembly/track adapter URIs and optionally rebuilds `defaultSession`
so every registered track is visible.
"""
import argparse
import json
import os
import sys


def set_uri(obj, uri):
    if isinstance(obj, dict) and "uri" in obj:
        obj["uri"] = uri
        obj.setdefault("locationType", "UriLocation")


def update(config, species, defaults):
    for assembly in config.get("assemblies", []):
        assembly["name"] = assembly.get("name") or species
        adapter = assembly.get("sequence", {}).get("adapter", {})
        if adapter.get("type") == "BgzipFastaAdapter":
            set_uri(adapter.get("fastaLocation"), f"/jbrowse/large/{species}/{species}.genome.fa.gz")
            set_uri(adapter.get("faiLocation"), f"/jbrowse/large/{species}/{species}.genome.fa.gz.fai")
            set_uri(adapter.get("gziLocation"), f"/jbrowse/large/{species}/{species}.genome.fa.gz.gzi")

    for track in config.get("tracks", []):
        adapter = track.get("adapter", {})
        if adapter.get("type") == "Gff3TabixAdapter":
            gff = adapter.get("gffGzLocation", {})
            uri = gff.get("uri", "")
            # Only the base GFF track uses the canonical name; derived tracks
            # (GO/KEGG/TE) point at their own generated files.
            if track.get("trackId") == "GFF" or uri.endswith(f"{species}.gff.gz"):
                set_uri(gff, f"/jbrowse/large/{species}/{species}.gff.gz")
                index = adapter.get("index", {}).get("location", {})
                set_uri(index, f"/jbrowse/large/{species}/{species}.gff.gz.tbi")

    if defaults:
        track_ids = [t["trackId"] for t in config.get("tracks", []) if t.get("trackId")]
        by_id = {t["trackId"]: t for t in config.get("tracks", []) if t.get("trackId")}
        assembly_name = species
        if config.get("assemblies"):
            assembly_name = config["assemblies"][0].get("name", species)
        config["defaultSession"] = {
            "name": assembly_name,
            "views": [{
                "id": "linearGenomeView",
                "type": "LinearGenomeView",
                "tracks": [{
                    "type": by_id[tid].get("type", "FeatureTrack"),
                    "configuration": tid,
                    "displays": [{
                        "type": "LinearBasicDisplay",
                        "configuration": f"{tid}-LinearBasicDisplay",
                    }],
                } for tid in track_ids if tid in by_id],
            }],
        }
    return config


def main():
    ap = argparse.ArgumentParser(description="Update one JBrowse config.json")
    ap.add_argument("--config", required=True)
    ap.add_argument("--species", required=True)
    ap.add_argument("--defaults", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(args.config):
        print(f"[ERROR] config not found: {args.config}", file=sys.stderr)
        return 3
    with open(args.config, "r", encoding="utf-8") as fh:
        config = json.load(fh)
    config = update(config, args.species, args.defaults)
    with open(args.config, "w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)
    print(f"[OK] updated {args.config}")
    return 0


if __name__ == "__main__":
    sys.exit(main())