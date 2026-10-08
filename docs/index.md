# conda-sboms

`conda-sboms` adds software bill of materials (SBOM) export to `conda export`.
It writes CycloneDX or SPDX from the exact package records of one resolved
conda environment.

## Output formats

| Output | `--format` | Aliases | Filename detection |
| --- | --- | --- | --- |
| CycloneDX 1.7 JSON | `cyclonedx-json-v1.7` | `cyclonedx-json`, `cyclonedx`, `cdx-json` | `*.cdx.json` |
| CycloneDX 1.7 XML | `cyclonedx-xml-v1.7` | `cyclonedx-xml`, `cdx-xml` | `*.cdx.xml` |
| CycloneDX 1.6 JSON | `cyclonedx-json-v1.6` | None | None, use `--format` |
| SPDX 3.0.1 JSON-LD | `spdx-jsonld-v3.0.1` | `spdx-jsonld` | `*.spdx3.json`, `*.spdx.jsonld` |

:::{note}
CycloneDX 1.7 JSON is available in released packages. The other three outputs
are unreleased and require a [source checkout](how-to/install.md).
:::

Use a versioned name to keep the schema version fixed. `cyclonedx-json` and
`.cdx.json` filenames select 1.7. Use `--format cyclonedx-json-v1.6` to select
1.6 explicitly. SPDX 2.3 is not supported.

The [format selection guide](how-to/choose-format.md) has commands for each
output. The [format reference](reference/formats.md) covers aliases, filename
detection, and Python entry points.

## Quick start

This is alpha software. Install the
[conda-forge package](https://anaconda.org/conda-forge/conda-sboms) into the
environment that owns the `conda` executable by following the
[installation guide](how-to/install.md).

Export an installed environment by name:

```console
conda export --name my-environment --from-history \
  --format cyclonedx-json \
  --file my-environment.cdx.json
```

The output identifies each resolved conda package, its available hashes and
source metadata, and the dependency relationships recorded by conda. It does
not inspect package contents or claim complete product coverage.

## Where to start

::::{grid} 1 2 2 2
:gutter: 3

:::{grid-item-card} {octicon}`rocket` Tutorial
- [Generate your first CycloneDX SBOM](tutorials/getting-started.md)
- [Generate and inspect an SPDX SBOM](tutorials/spdx.md)
:::

:::{grid-item-card} {octicon}`tools` How-to guides

- [Install the plugin](how-to/install.md)
- [Choose an output format](how-to/choose-format.md)
- [Validate an SBOM](how-to/validate.md)
- [Add product and author metadata](how-to/set-product-metadata.md)
- [Export a conda-workspaces environment](how-to/conda-workspaces.md)
- [Produce reproducible output](how-to/reproducible-output.md)
:::

:::{grid-item-card} {octicon}`list-unordered` Reference
:link: reference/formats
:link-type: doc

Look up format names, fields, graph rules, errors, and privacy behavior.
:::

:::{grid-item-card} {octicon}`book` Explanation
:link: explanation/coverage-and-compliance
:link-type: doc

Understand the coverage limits, conda metadata limits, and relationship to CRA
requirements.
:::

::::

## What the output describes

The SBOM is an inventory of the resolved conda package graph supplied to the
exporter. It can contribute to product technical documentation. It does not
establish that every component in a product has been found or that the product
conforms to the Cyber Resilience Act.

```{toctree}
:hidden:
:caption: Tutorial

tutorials/getting-started
tutorials/spdx
```

```{toctree}
:hidden:
:caption: How-to guides

how-to/install
how-to/choose-format
how-to/validate
how-to/set-product-metadata
how-to/conda-workspaces
how-to/reproducible-output
```

```{toctree}
:hidden:
:caption: Reference

reference/formats
reference/cyclonedx-json
reference/spdx-jsonld
```

```{toctree}
:hidden:
:caption: Explanation

explanation/coverage-and-compliance
explanation/formats-and-relationships
```
