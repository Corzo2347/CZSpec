# Changelog

All notable public changes to CZSpec are documented here.

## [1.0.0] - 2026-09-25

First stable public release.

### Public modules

- M1 — Detection and fitting.
- M2 — Molecular identification.
- M3 — Column density.

### Added

- Bilingual Spanish/English interface.
- Runtime Online/Offline mode in the application header.
- Equal-sized header controls with a more consistent order.
- Version button opens the official CZSpec GitHub repository.
- Persistent Offline mode that prevents live external-service queries.
- M1 spectral loading for ASCII and reduced FITS products.
- External GILDAS/CLASS bridge for `.30m` import.
- Multi-spectrum sessions, preview selection and comparison views.
- Baseline handling, smoothing, line detection and Gaussian/Lorentzian/Voigt fitting.
- M2 Splatalogue/CDMS/JPL candidate search with configurable TOP-K and scientific filters.
- Propagation of source identity, VLSR and excitation-temperature metadata across modules.
- M3 optically thin and hyperfine/isotopologue column-density methods.
- Editable isotopic-ratio table and multiple valid column-density solutions per identified line.
- Independent save labels and module-specific export folders.
- Non-destructive export naming using incremental suffixes such as `_001`, `_002`, etc.

### Online / Offline behavior

When Offline mode is active:

- M1 local spectral analysis remains available.
- live Splatalogue identification in M2 is skipped;
- previously generated/local M2 tables can still be loaded;
- M3 can continue using existing M2 results;
- SIMBAD lookup is disabled;
- GitHub and other explicit external-service actions are disabled or skipped.

### Scope

CZSpec v1.0.0 is intended for post-reduction molecular spectral analysis. It does not calibrate or image raw interferometric visibilities.
