# Frontend Logic Cleanup Guide

## 1. Why this cleanup

Before this refactor, genome-browser related pages had duplicated logic in multiple places:

- Genome selector state (`selectedGenome`, `cascaderProps`, default genome)
- Data path building (`/data/genome/<genome>/...`)
- `.fai` parsing for first chromosome and default `locus`
- Initialization flow (`fetchGenomes -> pick default -> load page`)

This made behavior drift likely and increased maintenance cost.

## 2. What has been unified

New shared module:

- `src/composables/useGenomeBrowser.ts`

It now provides:

- `useGenomeSelector()`
- `buildGenomeDataPaths(genomeName)`
- `getFirstChromosomeFromFai(genomeName, fallback)`
- `createDefaultLocus(genomeName, range, fallbackChromosome)`

## 3. Current page responsibilities

### `IGVView.vue`

- Owns only IGV-specific rendering and lifecycle:
- Create/destroy igv browser instance
- Apply track config
- Handle user actions (`load/reset`)

Shared genome logic is fully delegated to `useGenomeSelector` and `createDefaultLocus`.

### `JbrowseView.vue`

- Owns only JBrowse iframe-specific rendering:
- Build iframe URL
- Refresh iframe key

Shared genome logic is fully delegated to `useGenomeSelector` and `createDefaultLocus`.

## 4. Standard flow for genome-dependent pages

Any new page that depends on genome selection should follow this sequence:

1. `const { ... } = useGenomeSelector()`
2. `await ensureGenomesLoaded()`
3. `const defaultGenome = pickDefaultGenome()`
4. `setSelectedGenome(defaultGenome)`
5. build page-specific view state (url/browser/task params)

Do not reimplement:

- cascader props
- default genome fallback logic
- `.fai` parsing
- `/data/genome` path templates

## 5. Suggested next cleanup targets

The following files still contain repeated genome initialization logic and should migrate to `useGenomeSelector`:

- `src/views/TFView.vue`
- `src/views/TRView.vue`
- `src/views/PrimerView.vue`
- `src/views/GeneExpressionView.vue`
- `src/views/GeneExpressionEfpView.vue`
- `src/views/BlastpView.vue`
- `src/views/IdSearchView.vue`
- `src/views/DownloadView.vue`

## 6. Practical rules

- Keep shared state/behavior in composables.
- Keep views focused on page rendering and user interaction.
- Keep stores focused on data source and caching policy.
- If two pages need the same algorithm, move it to a composable first.

## 7. Change summary in this refactor

- Added: `src/composables/useGenomeBrowser.ts`
- Refactored: `src/views/IGVView.vue`
- Refactored: `src/views/JbrowseView.vue`
- Refactored: `src/views/TFView.vue`
- Refactored: `src/views/TRView.vue`
- Refactored: `src/views/PrimerView.vue`
- Refactored: `src/views/BlastpView.vue`
- Refactored: `src/views/GeneExpressionView.vue`
- Refactored: `src/views/GeneExpressionEfpView.vue`
- Refactored: `src/views/IdSearchView.vue`
- Refactored: `src/views/DownloadView.vue`
- Added this document: `docs/logic-cleanup-guide.md`
