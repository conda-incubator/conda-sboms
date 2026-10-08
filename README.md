# conda-sboms

Generate a software bill of materials (SBOM) for an existing conda
environment.

`conda-sboms` adds CycloneDX and SPDX export to `conda export`. It writes the
exact package records and dependency graph of one resolved conda environment.
Clients such as conda-workspaces can use the same exporters through conda's
plugin hook.

The project is alpha software. Questions, bug reports, and contributions are
[welcome on GitHub](https://github.com/conda-incubator/conda-sboms).

## Output formats

| Output | `--format` | Aliases | Filename detection |
| --- | --- | --- | --- |
| CycloneDX 1.7 JSON | `cyclonedx-json-v1.7` | `cyclonedx-json`, `cyclonedx`, `cdx-json` | `*.cdx.json` |
| CycloneDX 1.7 XML | `cyclonedx-xml-v1.7` | `cyclonedx-xml`, `cdx-xml` | `*.cdx.xml` |
| CycloneDX 1.6 JSON | `cyclonedx-json-v1.6` | None | None, use `--format` |
| SPDX 3.0.1 JSON-LD | `spdx-jsonld-v3.0.1` | `spdx-jsonld` | `*.spdx3.json`, `*.spdx.jsonld` |

CycloneDX 1.7 JSON is available in released packages. The other three outputs
are unreleased and require a
[source checkout](https://conda-incubator.github.io/conda-sboms/how-to/install/).

Use a versioned name in automation to keep the schema version fixed. Aliases
can advance to a later supported version. `cyclonedx-json` and `.cdx.json`
filenames select 1.7. Select 1.6 explicitly with `--format cyclonedx-json-v1.6`,
which takes precedence over filename detection. SPDX 2.3 is not supported.

See the [format selection guide](https://conda-incubator.github.io/conda-sboms/how-to/choose-format/)
for export commands and consumer compatibility checks, or the
[format reference](https://conda-incubator.github.io/conda-sboms/reference/formats/)
for Python entry points.

## Quick start

`conda-sboms` requires conda 26.3 or newer. For a standard conda installation,
activate `base` and install the
[conda-forge package](https://anaconda.org/conda-forge/conda-sboms):

```console
conda activate base
conda install --channel conda-forge "conda-sboms>=0.3.0"
```

The [installation guide](https://conda-incubator.github.io/conda-sboms/how-to/install/)
also covers the PyPI wheel and source checkouts.

Generate an SBOM for an installed environment:

```console
conda export --name my-environment --from-history \
  --format cyclonedx-json \
  --file my-environment.cdx.json
```

`--from-history` asks conda to preserve the requested package roots when its
history contains them. The SBOM still contains every resolved conda package.

With `conda-sboms` 0.2.0 or newer, use the
[product metadata guide](https://conda-incubator.github.io/conda-sboms/how-to/set-product-metadata/)
to identify a shipped product, its manufacturer, and the person or organization
that authored the SBOM.

For a disposable example, follow the
[getting-started tutorial](https://conda-incubator.github.io/conda-sboms/tutorials/getting-started/).

## What the SBOM contains

The environment is represented as the root application and each resolved conda
package as a library component. When available, the SBOM includes package
hashes, build and platform data, license text, sanitized distribution URLs,
conda package URLs, and dependency relationships.

## Scope and limitations

The exporter does not inspect package contents, discover vendored or statically
linked software, include packages from other ecosystems, infer a manufacturer,
scan for vulnerabilities, or establish Cyber Resilience Act conformity. The
document marks overall coverage as unproven.
Conda-specific properties record known external-package, virtual-package, and
missing-dependency counts supplied by the input.

Read the [documentation](https://conda-incubator.github.io/conda-sboms/) for product
metadata, the format reference, conda-workspaces integration, reproducible
output, and coverage limits.

## Development

SPDX support reuses existing runtime packages and serializes documents with
Python's `json` module. It adds no new runtime package. Schema and semantic
validators are development dependencies.

Install the locked development environment and confirm that conda discovers the
exporters:

```console
pixi install --locked -e dev
pixi run --locked -e dev conda export --help
```

Run the checks and documentation build:

```console
pixi run --locked -e dev check
pixi run --locked -e docs docs
```

## License

BSD-3-Clause. See [LICENSE](LICENSE).
