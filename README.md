# conda-sboms

Generate a CycloneDX software bill of materials (SBOM) for an existing conda
environment.

`conda-sboms` is an exporter plugin for `conda`. It adds the `cyclonedx-json`
format to `conda export` and writes conda's exact package records and dependency
graph as CycloneDX 1.7 JSON. Because it uses conda's standard exporter hook,
clients such as conda-workspaces can use the same format.

The project is alpha software. Questions, bug reports, and contributions are
[welcome on GitHub](https://github.com/conda-incubator/conda-sboms).

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
The [installation guide](https://conda-incubator.github.io/conda-sboms/how-to/install/)
also covers source checkouts.

## What the SBOM contains

The environment is represented as the root application and each resolved conda
package as a library component. When available, the SBOM includes package
hashes, build and platform data, license text, sanitized distribution URLs,
conda package URLs, and dependency relationships.

## Scope and limitations

The exporter does not inspect package contents, discover vendored or statically
linked software, include packages from other ecosystems, infer a manufacturer,
scan for vulnerabilities, or establish Cyber Resilience Act conformity. The
root composition marks overall coverage as unproven.
Conda-specific properties record known external-package, virtual-package, and
missing-dependency counts supplied by the input.

Read the [documentation](https://conda-incubator.github.io/conda-sboms/) for product
metadata, the format reference, conda-workspaces integration, reproducible
output, and coverage limits.

## Development

Install the locked development environment and confirm that conda discovers the
exporter:

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
