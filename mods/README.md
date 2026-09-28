# CZSpec Community Modules

The `mods/` directory is the official location for optional community extensions that build on CZSpec without needing to become part of the core M1, M2, or M3 modules.

The goal is to keep useful scientific extensions easy to discover from one common repository while preserving clear authorship and compatibility information.

## How modules enter this directory

Community modules are proposed through a Pull Request to the official CZSpec repository.

A module is not merged automatically. It may be reviewed for:

- compatibility with CZSpec;
- basic code quality and safety;
- scientific documentation;
- dependency impact;
- authorship and licensing;
- reproducibility and scope.

Acceptance into `mods/` does not mean that Oscar Corzo authored the module, nor does it transfer authorship away from its contributor.

## Required module structure

A module should normally use:

```text
mods/
└── example_module/
    ├── README.md
    ├── manifest.toml
    └── ...
```

Additional source, tests, examples, or documentation may be included as needed.

## Required metadata

Each `manifest.toml` should provide at least:

```toml
name = "Example Module"
module_id = "example_module"
version = "1.0.0"
authors = ["Example Contributor"]
czspec_original_creator = "Oscar Corzo"
czspec_min_version = "1.0.0"
license = "GPL-3.0-only"
description = "Short description of the module."
```

If a module has additional Python dependencies, list and document them clearly.

## Module README

Each module README should explain:

- what the module does;
- who created and maintains it;
- which CZSpec versions it supports;
- how to install, enable, disable, and remove it;
- required dependencies;
- expected inputs and outputs;
- relevant equations, assumptions, units, and references for scientific methods;
- known limitations.

Recommended attribution:

> **Module author(s):** Name(s)  
> **For:** CZSpec  
> **CZSpec original creator:** Oscar Corzo

## Licensing

Modules accepted into this repository must use terms compatible with the official CZSpec distribution. Unless an exception is explicitly reviewed and documented, community modules should use **GPL-3.0-only**.

## Official versus community functionality

Core functionality is maintained inside CZSpec itself. A community module may be distributed from the official repository without becoming a core feature.

The module's own README must make its maintenance status clear.

## Future module manager

The project may later expose a module manager inside CZSpec so that, when Online mode is enabled, users can discover and install compatible modules from this directory. Offline mode would continue to use already installed modules without requiring Internet access.

That future interface does not change the contribution rules above.
