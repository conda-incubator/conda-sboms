# Formats, inventory, and dependencies

CycloneDX and SPDX can describe the same resolved conda packages, but they
represent the facts differently. Selecting an output changes its serialization
and vocabulary. It does not expand the source data available to the exporter.

## Inventory membership is separate from dependencies

An inventory answers which packages were supplied in
`Environment.explicit_packages`. Dependency relationships answer which
packages another package declares through `PackageRecord.depends`.

SPDX makes the distinction explicit. The environment `contains` every
resolved conda package, while `dependsOn` connects it to requested or inferred
roots and connects packages to their resolved dependencies. A package can be
in the inventory even when the user did not request it directly.

CycloneDX lists packages under `components` and the package graph under
`dependencies`. Root assembly and dependency compositions record coverage
limitations. Every package has a dependency entry, including known leaves.

## The source determines which roots are known

Requested packages preserve user intent when the client supplies them from
history or an authoritative manifest. Without them, graph inference selects
packages with no incoming dependencies and adds a stable representative for
disconnected cycles. These inferred roots make every component reachable, but
do not establish which packages the user chose.

The [workspace guide](../how-to/conda-workspaces.md) explains why generic
lockfile export and the dedicated workspace SBOM command may supply different
requested roots.

## License labels are not full licenses

Conda license metadata may be an SPDX expression such as `BSD-3-Clause`, a
legacy label, or arbitrary text. CycloneDX preserves the original value as a
named license.

SPDX declared-license relationships require a license element. The exporter
validates known SPDX identifiers and expression syntax before creating a
license expression. An unrecognized value stays in `conda:package:license`
metadata and produces no declared-license assertion. Constructing a custom
SPDX license would require full license text, which a short conda label does
not supply. The exporter does not infer a concluded license from the label.

## Coverage claims differ by format

CycloneDX uses `unknown` when the inventory cannot establish completeness and
`incomplete` when input identifies omitted members. SPDX relationships use
`noAssertion` and `incomplete` for those cases. A declared dependency with no
resolved target is evidence of an omission, while a package with no declared
dependencies is not proof that it contains no vendored software.

Conversion between standards may lose distinctions or metadata. Generate the
needed output directly from the resolved conda environment whenever possible,
and review [coverage and compliance](coverage-and-compliance.md) before making
product-level claims.
