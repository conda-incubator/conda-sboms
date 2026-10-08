# CycloneDX exporters

The exporters accept one resolved conda environment and return a CycloneDX
document ending with a newline. The default remains CycloneDX 1.7 JSON.

## Format identity

| Field | Value |
| --- | --- |
| Distribution | `conda-sboms` |
| Conda plugin entry point | `conda-sboms` |
| Canonical format name | `cyclonedx-json-v1.7` |
| Aliases | `cyclonedx-json`, `cyclonedx`, `cdx-json` |
| Default filename pattern | `*.cdx.json` |
| Specification | CycloneDX 1.7 JSON |
| Platform support | One platform per document |

The canonical name is pinned to CycloneDX 1.7 and will not change meaning. The
unversioned `cyclonedx-json` alias may advance to a later supported CycloneDX
JSON version. Use the canonical name in automation that must remain on 1.7.

All four format names select the same exporter. A filename ending in
`.cdx.json` lets conda detect the format without `--format`:

```console
conda export --name my-environment --file my-environment.cdx.json
```

A custom filename requires the explicit format name:

```console
conda export --name my-environment \
  --format cyclonedx-json \
  --file inventory.json
```

Omit `--file` to write the document to standard output. `conda-sboms` does not
add a separate command-line interface.

### Additional outputs

The source version also provides these unreleased outputs:

| Specification | Canonical name | Aliases | Filename pattern |
| --- | --- | --- | --- |
| CycloneDX 1.7 XML | `cyclonedx-xml-v1.7` | `cyclonedx-xml`, `cdx-xml` | `*.cdx.xml` |
| CycloneDX 1.6 JSON | `cyclonedx-json-v1.6` | None | None, explicit format required |

The unversioned JSON aliases and `.cdx.json` detection continue to select
1.7. Selecting 1.6 invokes its version-specific serializer. It does not
relabel a 1.7 document. XML uses the same conda field mappings with CycloneDX's
XML representation.

## Input

The exporter receives one `conda.models.environment.Environment` through
conda's `conda_environment_exporters` hook. `explicit_packages` must contain at
least one exact `PackageRecord`. The callback does not solve an environment,
read a prefix, read a lockfile, or access the network.

Conda and other clients construct the `Environment` before invoking the
exporter. This is why installed prefixes and resolved workspace locks work but
an unresolved list of requirements does not.

## Python API

:::{versionadded} 0.2.0
The public object API and explicit per-call metadata.
:::

:::{versionadded} 0.3.0
The `output_reproducible` argument and exporter state.
:::

The object API consists of four public classes:

| Class | Responsibility |
| --- | --- |
| `CycloneDXExportMetadata(...)` | Validate caller-supplied product and author metadata |
| `CycloneDXPackage(record)` | Map one exact `PackageRecord` to a CycloneDX component |
| `CycloneDXDependencyGraph(packages)` | Build dependency edges and select product roots |
| `CycloneDXExporter(environment, *, metadata=None, output_reproducible=False, schema_version="1.7", serialization="json")` | Build and serialize the complete CycloneDX document |

The exact call signatures are:

```text
CycloneDXExportMetadata(
    product_name: str | None = None,
    product_version: str | None = None,
    product_manufacturer: str | None = None,
    product_manufacturer_url: str | None = None,
    author_name: str | None = None,
    author_email: str | None = None,
    author_organization: str | None = None,
    author_organization_url: str | None = None,
)
CycloneDXPackage(record: PackageRecord)
CycloneDXDependencyGraph(packages: list[CycloneDXPackage])
CycloneDXDependencyGraph.root_references(
    requested_packages: list[MatchSpec],
) -> list[BomRef]
CycloneDXExporter(
    environment: Environment,
    *,
    metadata: CycloneDXExportMetadata | None = None,
    output_reproducible: bool = False,
    schema_version: str = "1.7",
    serialization: str = "json",
)
CycloneDXExporter.export() -> str
```

Their public state is part of the API:

| Class | Public members |
| --- | --- |
| `CycloneDXExportMetadata` | `product_name`, `product_version`, `product_manufacturer`, `product_manufacturer_url`, `author_name`, `author_email`, `author_organization`, `author_organization_url` |
| `CycloneDXPackage` | `record`, `component` |
| `CycloneDXDependencyGraph` | `references_by_name`, `components_by_reference`, `edges`, `missing_edge_count`, `incomplete_references`, `root_references(requested_packages)` |
| `CycloneDXExporter` | `packages`, `graph`, `root_references`, `roots_inferred`, `root_completeness`, `metadata`, `root`, `output_reproducible`, `timestamp`, `schema_version`, `serialization`, `export()` |

`CycloneDXExportMetadata` instances are immutable. Construction strips
surrounding whitespace from string values and converts empty values to `None`.
The unreleased `ExportMetadata` name in `conda_sboms.settings` is an alias
of the same class for use by either SBOM format.

Use `CycloneDXExporter` directly when calling the exporter from Python:

```python
from conda_sboms.cyclonedx import CycloneDXExporter
from conda_sboms.settings import CycloneDXExportMetadata

document = CycloneDXExporter(
    environment,
    metadata=CycloneDXExportMetadata(
        product_name="Acme Runtime",
        product_version="2026.08",
    ),
).export()
```

The conda plugin hook uses the public callback with this signature:

```text
export_cyclonedx_json(
    environment: Environment,
    *,
    metadata: CycloneDXExportMetadata | None = None,
    output_reproducible: bool = False,
) -> str
```

The unreleased `export_cyclonedx_xml` and `export_cyclonedx_json_v1_6`
callbacks have the same arguments and select XML 1.7 and JSON 1.6,
respectively. `export_cyclonedx_json` remains pinned to JSON 1.7.

The object API accepts only the pairs `schema_version="1.7"` with
`serialization="json"` or `"xml"`, and `schema_version="1.6"` with
`serialization="json"`. Other combinations raise `CondaValueError`.

When `metadata` is `None`, the callback reads conda's active plugin settings.
An explicit `CycloneDXExportMetadata` object replaces those settings for that
call. `CycloneDXExporter` follows the same rule.

An exporter instance is a snapshot of its environment, metadata, and timestamp
policy. Construct a new instance after changing any of those inputs.

## Document metadata

| CycloneDX field | Source |
| --- | --- |
| `$schema` | Selected CycloneDX JSON schema URL |
| `bomFormat` | `CycloneDX` |
| `specVersion` | `1.7` or explicitly selected `1.6` |
| `version` | `1` for each newly generated document |
| `metadata.timestamp` | Current UTC time, `SOURCE_DATE_EPOCH`, or omitted in reproducible mode |
| `metadata.properties` | `cdx:reproducible=true` in reproducible mode |
| `metadata.tools.components` | `conda-sboms` and its installed version |
| `metadata.manufacturer` | Configured organization that authored the SBOM |
| `metadata.authors` | Configured person who authored the SBOM |
| `metadata.component` | The exported environment or configured product |

The optional `serialNumber` is omitted so unchanged inputs can produce
byte-for-byte identical output.

The author fields are omitted when their values are absent. They describe who
created the SBOM and remain separate from the `conda-sboms` generating tool.

XML expresses the selected version through the CycloneDX 1.7 namespace,
rather than JSON's `$schema`, `bomFormat`, and `specVersion` fields. The
serializer preserves equivalent metadata, package mappings, and composition
claims in its schema-defined elements. The complete serialized output is
validated against the official XSD in tests.

## Product metadata settings

:::{versionadded} 0.2.0
Conda plugin settings for product, manufacturer, and SBOM author metadata.
:::

The exporter reads these optional values from conda's plugin configuration:

| Conda setting | CycloneDX field |
| --- | --- |
| `plugins.conda_sboms_product_name` | `metadata.component.name` |
| `plugins.conda_sboms_product_version` | `metadata.component.version` |
| `plugins.conda_sboms_product_manufacturer` | `metadata.component.manufacturer.name` |
| `plugins.conda_sboms_product_manufacturer_url` | `metadata.component.manufacturer.url[]` |
| `plugins.conda_sboms_author_name` | `metadata.authors[].name` |
| `plugins.conda_sboms_author_email` | `metadata.authors[].email` |
| `plugins.conda_sboms_author_organization` | `metadata.manufacturer.name` |
| `plugins.conda_sboms_author_organization_url` | `metadata.manufacturer.url[]` |

The environment-variable form uppercases the setting and prefixes it with
`CONDA_PLUGINS_`. For example,
`plugins.conda_sboms_product_name` becomes
`CONDA_PLUGINS_CONDA_SBOMS_PRODUCT_NAME`.

Values are stripped of surrounding whitespace, and empty values are omitted.
The product name and version must be configured together, and a product
manufacturer requires both. An author email requires an author name. An
organization URL requires the corresponding organization name. URLs must use
HTTP or HTTPS and must not contain credentials, whitespace, query strings,
fragments, or malformed percent escapes. Product versions longer than 1024
characters are rejected to match the CycloneDX 1.7 component limit.

These settings are caller-owned data. The exporter never fills them from a
conda channel. See [Add product and author metadata](../how-to/set-product-metadata.md)
for commands and lifecycle guidance.

## Root component

The environment is an `application` component. When product name and version
are configured, they identify that component and its BOM reference. Otherwise a
safe logical environment name is preserved. A path-shaped name from
`conda export --prefix` becomes `conda-environment` so the document does not
expose the local prefix.

The root has these properties:

| Property | Meaning |
| --- | --- |
| `conda:environment:platform` | Conda subdir represented by the document |
| `conda:environment:scope` | Always `resolved-conda-packages` |
| `conda:environment:root-dependency-source` | `requested-packages` or `inferred-graph-roots` |
| `conda:environment:external-packages-omitted` | Count of known non-conda packages not represented |
| `conda:environment:virtual-packages-omitted` | Count of virtual packages not represented as components |
| `conda:environment:dependency-edges-omitted` | Count of declared dependency edges whose target is absent from the records |

The three omission properties appear only when their count is nonzero.

## Package components

Each exact conda package record becomes a `library` component.

| CycloneDX field | Conda record data |
| --- | --- |
| `name`, `version` | Package name and version |
| `bom-ref`, `purl` | Conda package URL with available build, channel, subdir, and archive type qualifiers |
| `hashes` | Available SHA-256 and MD5 archive hashes |
| `licenses` | Raw conda license text represented as a named license |
| `externalReferences` | Sanitized remote package URL with type `distribution` |
| `properties` | Build string, build number, subdir, canonical channel, filename, and archive size when available |

License text is not treated as an SPDX expression because legacy conda records
may contain arbitrary text. A channel is not treated as the package supplier,
producer, or manufacturer.

## Dependency graph

Package edges come from `PackageRecord.depends`. Each dependency MatchSpec is
matched by package name to the resolved record. `constrains` entries are not
dependencies and are not mapped.

The document contains one dependency entry for the root and one for every
package component. Known leaves have an explicit empty `dependsOn` array in
JSON, or a childless `<dependency ref="…"/>` element in XML.

When `requested_packages` is non-empty, names also present in the resolved
records become root dependencies. Requested names absent from the records are
silently omitted and do not currently produce an incompleteness marker.
Otherwise the exporter infers graph roots and adds a stable representative for
any disconnected cycle so every serialized component is reachable from the
root.

## Completeness

The root assembly composition is `unknown` when conda metadata cannot establish
whether all product constituents are represented. It is `incomplete` when the
input reports omitted external packages.

When roots are inferred, the root reference is also listed under `dependencies`
in the root composition. It uses the same aggregate as the assembly, normally
`unknown`, or `incomplete` when external packages were reported. A package with
a declared dependency absent from the resolved record set appears in a separate
`incomplete` dependency composition.

## Privacy behavior

The exporter removes basic authentication, Anaconda token path segments, query
strings, and fragments from remote distribution URLs. Channel identity comes
from conda's canonical channel name. Local file URLs, local file channels, and
local environment paths are omitted. Package filenames are reduced to their
basename before serialization.

## Errors

The exporter explicitly rejects:

- input without exact package records
- a supplied SHA-256 or MD5 value with the wrong length or non-hex data
- a product name or version is supplied without the other value
- a product manufacturer is supplied without product identity
- an author email or organization URL is supplied without its corresponding
  name
- a product version exceeds the CycloneDX 1024-character limit
- an author email is malformed
- an organization URL is not HTTP or HTTPS or contains credentials, whitespace,
  a query, a fragment, or malformed percent escapes
- `SOURCE_DATE_EPOCH` is negative, malformed, or outside the platform's
  supported timestamp range
- an unsupported specification and serialization pair is supplied to
  `CycloneDXExporter`

Failures occur before conda writes the output returned by the exporter.
