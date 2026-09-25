# CZSpec

**Current public version: v1.0.0**

CZSpec is a desktop application for reproducible analysis of radioastronomical and molecular spectral-line data. It is written in Python/PySide6 and provides a bilingual Spanish/English interface.

## Public workflow

CZSpec v1.0.0 exposes three public modules:

1. **M1 — Detection and fitting**
   - ASCII spectral files (`.dat`, `.txt`, `.csv`)
   - reduced scientific FITS spectra/cubes
   - CLASS `.30m` import through an external GILDAS/CLASS installation
   - baseline handling, smoothing, calibration, line detection, Gaussian/Lorentzian/Voigt fitting, multi-spectrum comparison and exports

2. **M2 — Molecular identification**
   - Splatalogue queries with CDMS/JPL context
   - configurable TOP-K candidates and identification filters
   - partition functions Q(T)
   - source/VLSR propagation from M1
   - final identified-spectrum visualization and exports

3. **M3 — Column density**
   - optically thin method (**MOD** in Spanish / **OTM** in English)
   - hyperfine/isotopologue method (**MTH** in Spanish / **HTM** in English)
   - editable isotopic ratios
   - multiple valid column-density solutions associated with the same identified line
   - tables, spectra and figure exports

## Online / Offline mode

The header includes a persistent **Online / Offline** switch.

- **Online** enables external services when requested, including Splatalogue and SIMBAD.
- **Offline** prevents CZSpec from contacting those services and skips Internet-dependent stages.
- M1 remains available offline.
- M2 can still load previously generated/local tables, but a new live molecular-identification query requires Online mode.
- M3 remains available offline when the required M2 results are already present.
- The GitHub version button is disabled while Offline mode is active.

The first installation will normally require Internet access so `pip` can obtain Python dependencies. Runtime Offline mode refers to scientific use after installation.

## Installation

Download the appropriate package from **GitHub Releases**:

- `CZSpec-1.0.0-Windows-installer.zip`
- `CZSpec-1.0.0-Linux-installer.zip`
- `CZSpec-1.0.0-macOS-installer.zip`

Each installer package includes `czspec-1.0.0-py3-none-any.whl`.

Advanced/manual installation:

```bash
python -m pip install czspec-1.0.0-py3-none-any.whl
czspec
```

### Requirements

- Python **3.10 or newer**
- Windows, Linux or macOS
- GILDAS/CLASS is **external** and is required only for direct `.30m` import
- macOS package is currently a script-based installer, not a signed/notarized `.dmg` or `.pkg`

## Scientific scope

CZSpec is intended for post-reduction spectral analysis. It does **not** calibrate or image raw interferometric visibilities. Interferometric observations should enter CZSpec as scientifically reduced/calibrated FITS products or extracted spectra.

Scientific results should be inspected and validated by the user; CZSpec is an analysis tool, not a replacement for physical interpretation or reduction-quality control.

## Data and outputs

By default, each module keeps its own output structure. Exported products use non-destructive naming: if a requested filename already exists, CZSpec appends an incremental suffix such as `_001`, `_002`, etc., rather than silently overwriting previous scientific results.

## Citation

If CZSpec contributes to scientific work, please cite the software. A machine-readable citation is provided in [`CITATION.cff`](CITATION.cff).

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md).

## Issues and feedback

Bug reports and reproducible problems can be opened in the repository **Issues** section.

## Author

**Oscar Corzo**

Repository: https://github.com/Corzo2347/CZSpec
