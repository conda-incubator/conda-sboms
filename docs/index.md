# conda-sboms

`conda-sboms` adds CycloneDX software bill of materials (SBOM) export to
`conda export`. The current exporter writes CycloneDX 1.7 JSON from the exact
package records of one resolved conda environment.

This is alpha software. Install the
[conda-forge package](https://anaconda.org/conda-forge/conda-sboms) into the
environment that owns the `conda` executable by following the
[installation guide](how-to/install.md).

After the plugin is installed in the environment that owns `conda`, export an
installed environment by name:

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
:link: tutorials/getting-started
:link-type: doc

Generate and inspect a CycloneDX SBOM from a small conda environment.
:::

:::{grid-item-card} {octicon}`tools` How-to guides

- [Install the plugin](how-to/install.md)
- [Add product and author metadata](how-to/set-product-metadata.md)
- [Export a conda-workspaces environment](how-to/conda-workspaces.md)
- [Produce reproducible output](how-to/reproducible-output.md)
:::

:::{grid-item-card} {octicon}`list-unordered` Reference
:link: reference/cyclonedx-json
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
```

```{toctree}
:hidden:
:caption: How-to guides

how-to/install
how-to/set-product-metadata
how-to/conda-workspaces
how-to/reproducible-output
```

```{toctree}
:hidden:
:caption: Reference

reference/cyclonedx-json
```

```{toctree}
:hidden:
:caption: Explanation

explanation/coverage-and-compliance
```
