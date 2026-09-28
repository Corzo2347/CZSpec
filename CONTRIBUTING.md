# Contributing to CZSpec

Thank you for helping improve CZSpec.

CZSpec is intended to remain a scientifically useful, reproducible, and community-extensible project. Contributions may include bug fixes, documentation, tests, translations, scientific methods, user-interface improvements, catalog support, or optional community modules.

## Before contributing

Please:

1. Check existing Issues and Pull Requests to avoid duplicate work.
2. Open an Issue for substantial new features, scientific methods, or architectural changes before investing significant development time.
3. Keep scientific assumptions explicit and document references, equations, units, limitations, and expected inputs/outputs when a contribution changes scientific calculations.

## Contribution workflow

1. Fork `Corzo2347/CZSpec`.
2. Create a focused branch for the change.
3. Make and test the change.
4. Update documentation when behavior changes.
5. Open a Pull Request against the official repository.
6. Clearly describe:
   - what changed;
   - why it is useful;
   - how it was tested;
   - any new dependencies;
   - any scientific assumptions or references.

The maintainer may request revisions before merging.

## Licensing of contributions

CZSpec is licensed under **GNU GPL-3.0-only**.

By submitting a contribution for inclusion in the official repository, you represent that you have the right to submit it and agree that the accepted contribution will be distributed under **GPL-3.0-only** as part of CZSpec.

Do not submit code, data, images, documentation, or other material that you do not have permission to redistribute under compatible terms.

## Authorship and credit

CZSpec's original creator is **Oscar Corzo**.

Contributors retain credit for the work they actually create. Accepted contributions should preserve accurate authorship rather than assigning co-authorship to people who did not participate in that specific work.

For community modules, the module author(s) must be listed explicitly. See `AUTHORS.md` and `mods/README.md`.

## Scientific contributions

For changes to scientific calculations, please include enough information for review and reproducibility, ideally including:

- method name and purpose;
- governing equations or algorithm;
- units and conventions;
- literature reference(s), where applicable;
- assumptions and validity regime;
- test case or comparison against a known result when practical.

A contribution may be technically correct software yet still require scientific revision before it is accepted into the official CZSpec repository.

## Community modules

Optional extensions should normally be proposed under `mods/` when they are useful but do not belong in the core M1/M2/M3 application.

Each module must include at least:

- its own `README.md`;
- a `manifest.toml`;
- author(s);
- module version;
- compatible CZSpec version(s);
- dependencies;
- installation/use instructions;
- scientific description and references when applicable;
- GPL-compatible licensing information.

See `mods/README.md` for the module format.

## Code and project hygiene

Please keep Pull Requests focused. Avoid committing generated scientific outputs, local environments, credentials, temporary files, installers, or release binaries unless the maintainer explicitly requests them.

Do not commit private observational data without permission.

## Conduct and review

Be constructive and specific when reporting problems or reviewing scientific or technical work. Disagreement about implementation or scientific interpretation should be resolved through evidence, reproducible examples, and references whenever possible.

## Citation

If CZSpec contributes to research that leads to a publication, please cite the software using `CITATION.cff`.
