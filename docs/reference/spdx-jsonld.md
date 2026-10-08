# SPDX JSON-LD exporter

The exporter accepts one resolved conda environment and returns an SPDX 3.0.1
JSON-LD document ending with a newline.

:::{note}
This exporter is unreleased and requires a
[source checkout](../how-to/install.md).
It does not emit SPDX 2.3 JSON.
:::

## Format identity

| Field | Value |
| --- | --- |
| Distribution and conda plugin entry point | `conda-sboms` |
| Canonical format name | `spdx-jsonld-v3.0.1` |
| Alias | `spdx-jsonld` |
| Default filename patterns | `*.spdx3.json`, `*.spdx.jsonld` |
| Specification | SPDX 3.0.1 JSON-LD |
| Platform support | One platform per document |

Use the canonical name to keep an integration pinned to 3.0.1. The unversioned
alias may advance to a later supported SPDX version. The document contains
the official versioned JSON-LD context URI. Exporting does not fetch that URI.

## Input and Python API

The exporter receives one `conda.models.environment.Environment` with at
least one `PackageRecord` in `explicit_packages`. It does not solve, read a
prefix or lockfile, download package archives, or access the network.

```python
from conda_sboms.settings import ExportMetadata
from conda_sboms.spdx3 import export_spdx_jsonld

document = export_spdx_jsonld(
    environment,
    metadata=ExportMetadata(
        product_name="Acme Runtime",
        product_version="2026.08",
    ),
)
```

The callback signature is:

```text
export_spdx_jsonld(
    environment: Environment,
    *,
    metadata: ExportMetadata | None = None,
    output_reproducible: bool = False,
) -> str
```

`ExportMetadata` is an alias of `CycloneDXExportMetadata` with the
[same fields and validation](cyclonedx-json.md),
including the 1,024-character product-version limit. An explicit instance
replaces plugin configuration for that call. Otherwise the exporter reads the
active `conda_sboms_*` settings.

## Document elements

Elements appear in the document's `@graph` collection and link to one another
through identifiers.

| Element | Meaning |
| --- | --- |
| `SpdxDocument` | Groups the document's elements |
| `software_Sbom` | Identifies the environment as the SBOM root |
| `software_Package` with purpose `application` | The environment or configured product |
| `software_Package` with purpose `library` | One resolved conda package |
| `SoftwareAgent` | The generating `conda-sboms` tool and version |
| `Person`, `Organization` | Explicitly configured authors and product manufacturer |
| `Relationship` | Inventory membership, dependencies, and declared licenses |
| `simplelicensing_LicenseExpression` | A validated SPDX license expression |

Every emitted element refers to creation information containing the SPDX
version, UTC creation time, and creator identity. The exporter does not infer
a build or deployment lifecycle from the supplied environment.
The SPDX document declares `CC0-1.0` as its data license. This describes the
SBOM data, not the licenses of the packages it lists.

## Package mapping

| SPDX field or relationship | Conda source |
| --- | --- |
| `name`, `software_packageVersion` | Exact name and version |
| `software_primaryPurpose` | `application` for the environment, `library` for packages |
| `software_packageUrl` | Conda PURL with available build, channel, subdir, and archive-type qualifiers |
| `software_downloadLocation` | Sanitized remote distribution URL, when available |
| `verifiedUsing` | Available SHA-256 and MD5 archive hashes |
| `extension` | Conda properties stored through the standard `CdxPropertiesExtension` |
| `hasDeclaredLicense` | Validated license expression or `NoAssertionLicense` |

Conda properties retain build string, build number, subdir, canonical channel,
archive filename and size where available. Root properties retain platform,
scope, root-selection source, and known omission counts. Channel identity
does not establish a supplier, author, producer, or manufacturer.

The environment name is replaced by `conda-environment` when it is a local
path. Remote URLs lose credentials, tokens, query strings, and fragments.
Local file URLs and channels are omitted, and filenames are reduced to their
basename. These rules also apply to the facts used to generate identifiers.

## Product and author metadata

Configured product name and version identify the environment package. A
configured product manufacturer becomes an organization referenced as that
package's originator. Configured SBOM authors become creator agents. The
generating software agent remains separate from these supplied identities.

Contact email and organization URLs are preserved in agent metadata. The
[metadata guide](../how-to/set-product-metadata.md) describes configuration
precedence and validation shared with CycloneDX.

## Licenses

The exporter validates license expression syntax and known SPDX identifiers
before emitting a `simplelicensing_LicenseExpression` linked by
`hasDeclaredLicense`. It does not assign a concluded license.

An unrecognized conda license label is preserved exactly as
`conda:package:license` metadata. The declared-license relationship targets
the standard `NoAssertionLicense` element, with an explanation. Missing
license metadata also makes no declared-license assertion. The exporter does
not fabricate full text for a custom license from a short label.

## Relationships and completeness

The environment `contains` every supplied resolved conda package, separately
from dependency edges. Its `dependsOn` relationship points to resolved
requested roots when available. Otherwise the same deterministic inference
used by CycloneDX covers graph roots and disconnected cycles. The root source
property distinguishes requested packages from inferred graph roots.

Package `dependsOn` targets come from `depends` entries interpreted as
`MatchSpec` values. `constrains` does not add dependency edges. Names absent
from the resolved records are not fabricated as packages.

Relationship completeness is `noAssertion` when conda metadata cannot prove
the full set. Known omitted constituents or missing dependency targets use
`incomplete`. Empty or wholly unresolved dependency target sets use the
standard `NoAssertionElement`. Conda metadata distinguishes no declared
dependencies from declarations with missing targets. An empty conda
declaration is not proof that a package has no vendored dependencies.

Known external-package, virtual-package, and missing-dependency counts remain
in conda properties. Requested names absent from resolved records are omitted,
matching the existing CycloneDX root-selection behavior.

## Identifiers and timestamps

Identifiers derive from a digest of sanitized document content, including the
format, tool version, metadata, creation timestamp, package inventory, and
relationships. The digest is calculated before identifiers are assigned.
Changes to this content change the document identifiers. Collections have
deterministic ordering.

By default, creation information uses the current UTC time. Setting
`SOURCE_DATE_EPOCH` uses that non-negative integer Unix timestamp instead.
`output_reproducible=True` requires a valid `SOURCE_DATE_EPOCH`, because SPDX
creation information requires a timestamp. It does not omit the timestamp.

See [reproducible output](../how-to/reproducible-output.md) for examples and
the different CycloneDX timestamp policy.

## Errors and validation

Export fails for missing explicit package records, invalid archive hashes,
invalid product or author settings, and malformed, negative, or
unrepresentable `SOURCE_DATE_EPOCH` values. Explicit reproducible mode also
fails when no epoch is supplied.

The test suite checks both official JSON Schema and OWL/SHACL model rules
using pinned local resources. Export itself does not run a semantic validator.
See [validate an SBOM](../how-to/validate.md) for the development validation
commands and [SPDX 3.0.1](https://spdx.github.io/spdx-spec/v3.0.1/) for the
specification.
