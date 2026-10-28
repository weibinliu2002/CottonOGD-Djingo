# Vendored parser sources

These files are copied **unchanged** from the CottonOGD production scripts and
are imported by `workflow/scripts/annotation/parse_eggnog.py`. Do not edit the
copies in place; put workflow-specific changes in the wrapper instead.

## parse_eggNOG.py

- Local origin: `/public2/wbliu/data/CottonOGD/Script/parse_eggNOG.py`
  (symlinked from `Script/CottonOGD/eggnog_annoation/eggnog/parse_eggNOG.py`)
- sha256: `6df672f94fa1633fda6ee59b55fd4746c2baa477e8cbcfec2d49a3af15d618eb`
- Upstream URL: not recorded in the local copy; header attributes the file to
  Zhongyi Hua (njbxhzy@hotmail.com).
- Upstream commit: unknown (the file is not tracked by this repository).

## parse_go_obofile.py

- Local origin: `Script/CottonOGD/eggnog_annoation/eggnog/parse_go_obofile.py`
- sha256: `6bb6ffa6d6ebdf24d337b43da95d0b828f8a8a404fe9169186a83db78154483d`
- Upstream URL / commit: unknown.

The wrapper adds HTTP timeout, retry and an on-disk KEGG cache around
`get_html`, normalises `map` prefixes for database upload, and keeps the legacy
GO/KEGG parsing logic intact.

## para_wggnog_.py

This file was **not found** in the CottonOGD tree (`find` across `Script/`,
`backend/scripts/` and `/public2/wbliu/data/CottonOGD` returned no match).
Per the implementation decision to **reuse the legacy `parse_eggNOG.py`**, it
was not fetched from GitHub and no upstream URL/commit is recorded. If a future
requirement needs `para_wggnog_.py`, fetch it explicitly, record the repository
URL plus the exact commit hash here, and add it as a separate vendored file.