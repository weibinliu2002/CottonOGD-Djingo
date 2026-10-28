#!/usr/bin/env python3
"""Resolve GFF sequence IDs against genome FASTA sequence IDs.

Legacy CottonOGD inputs are not always named consistently:

* ``At_01`` in a GFF vs ``At_01_Bar32`` in the genome;
* ``A01`` in a GFF vs ``At01_HAU-AD2_v1.0`` in the genome;
* ``GhirP_A01`` in a GFF vs ``CM045499.1 ... chromosome A01`` in the genome.

Only unambiguous aliases are resolved.  Anything else stays unresolved so the
caller can warn about it (or drop those features) instead of silently mapping
a contig to the wrong chromosome.
"""
import re

# A/D chromosome token: A01, At_01, DT01, "chromosome A01", etc.
_CHR_RE = re.compile(
    r"(?i)(?:^|[^A-Z0-9])((?:AT|DT|A|D)[_-]?0*([1-9]\d?))(?=$|[^0-9])"
)
# Chromosome-level sequence names such as A01, At_01, At01_HAU-v1.0, chrD12.
_CHR_ID_RE = re.compile(
    r"(?i)^(?:chr)?(?P<group>at|dt|a|d)[_-]?0*(?P<num>[1-9]\d?)(?:$|[._-])"
)
_CHROMOSOME_WORD_RE = re.compile(r"(?i)\bchromosome\b")


def chromosome_key(text):
    """Return normalized chromosome keys such as ``{"A01", "D09"}``."""
    keys = set()
    for match in _CHR_RE.finditer(text or ""):
        group = "A" if match.group(1).upper().startswith("A") else "D"
        number = int(match.group(2))
        if 1 <= number <= 99:
            keys.add(f"{group}{number:02d}")
    return keys


def chromosome_id_key(seqid):
    """Return a chromosome key only for chromosome-level sequence names.

    ``At01_HAU-v1.0`` and ``A01`` are chromosome-level, while a scaffold whose
    name merely contains ``A01`` (for example ``scaffold42_A01_HAU-v1.0``) is
    not.  Restricting this lookup prevents such scaffolds from making the
    chromosome alias ambiguous.
    """
    match = _CHR_ID_RE.match(seqid or "")
    if not match:
        return None
    group = "A" if match.group("group").lower().startswith("a") else "D"
    number = int(match.group("num"))
    return f"{group}{number:02d}" if 1 <= number <= 99 else None


class SeqidResolver:
    """Map GFF seqids to genome seqids using exact, prefix, or chromosome keys."""

    def __init__(self, genome_ids, genome_headers=None):
        self.genome_ids = set(genome_ids)
        self.headers = genome_headers or {gid: gid for gid in genome_ids}
        self.aliases = {}
        self.cache = {}
        self.by_chromosome = {}
        for gid in self.genome_ids:
            header = self.headers.get(gid, "")
            key = chromosome_id_key(gid)
            if key:
                self.by_chromosome.setdefault(key, set()).add(gid)
                continue
            # INSDC accessions (CM045499.1) carry the chromosome label only in
            # the full FASTA description ("... chromosome A01 ...").
            if _CHROMOSOME_WORD_RE.search(header):
                for header_key in chromosome_key(header):
                    self.by_chromosome.setdefault(header_key, set()).add(gid)

    def resolve(self, seqid):
        """Return the genome seqid for *seqid*, or ``None`` when ambiguous."""
        if seqid in self.cache:
            return self.cache[seqid]
        if seqid in self.genome_ids:
            self.cache[seqid] = seqid
            return seqid

        # Versioned/contig-style suffix, e.g. At_01 -> At_01_Bar32.  Requiring a
        # single candidate keeps this safe when a genome has both At_01 and
        # At_01_alt.
        prefixed = [
            gid for gid in self.genome_ids
            if gid.startswith(seqid + "_")
            or gid.startswith(seqid + ".")
            or gid.startswith(seqid + "-")
        ]
        if len(prefixed) == 1:
            self.aliases[seqid] = prefixed[0]
            self.cache[seqid] = prefixed[0]
            return prefixed[0]

        # Chromosome label, e.g. A01 / At_01 / GhirP_A01.  Only map when the
        # key identifies exactly one genome sequence.
        candidates = set()
        for key in chromosome_key(seqid):
            candidates |= self.by_chromosome.get(key, set())
        if len(candidates) == 1:
            resolved = next(iter(candidates))
            self.aliases[seqid] = resolved
            self.cache[seqid] = resolved
            return resolved

        self.cache[seqid] = None
        return None