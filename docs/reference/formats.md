# Supported formats

Every exporter requires exact package records for one resolved conda environment
and one platform. Each returns text ending with a newline.

| Output | `--format` | Aliases | Filename detection |
| --- | --- | --- | --- |
| CycloneDX 1.7 JSON | `cyclonedx-json-v1.7` | `cyclonedx-json`, `cyclonedx`, `cdx-json` | `*.cdx.json` |
| CycloneDX 1.7 XML | `cyclonedx-xml-v1.7` | `cyclonedx-xml`, `cdx-xml` | `*.cdx.xml` |
| CycloneDX 1.6 JSON | `cyclonedx-json-v1.6` | None | None, use `--format` |
| SPDX 3.0.1 JSON-LD | `spdx-jsonld-v3.0.1` | `spdx-jsonld` | `*.spdx3.json`, `*.spdx.jsonld` |

:::{note}
CycloneDX 1.7 JSON is available in released packages. The other three outputs
are unreleased and require a [source checkout](../how-to/install.md).
:::

## Selecting a format

The versioned names in the `--format` column pin the specification version.
Use them in automation or when a consumer requires an exact version.
Unversioned aliases can advance to a later supported specification.

Without `--format`, conda detects the format from the output filename.
An explicit `--format` takes precedence. `cyclonedx-json` and `.cdx.json`
filenames select 1.7. CycloneDX 1.6 JSON requires
`--format cyclonedx-json-v1.6` and has no aliases or filename patterns.

SPDX 2.3 is not supported. The `.spdx.json` filename pattern is not registered
because it is commonly used for SPDX 2 documents. Use `.spdx3.json` or
`.spdx.jsonld` for SPDX 3.0.1.

Each exporter renders the supplied conda records directly. See
[choose an output format](../how-to/choose-format.md) for selection examples.

## Python entry points

| Callback | Output |
| --- | --- |
| `conda_sboms.cyclonedx.export_cyclonedx_json` | CycloneDX 1.7 JSON |
| `conda_sboms.cyclonedx.export_cyclonedx_xml` | CycloneDX 1.7 XML |
| `conda_sboms.cyclonedx.export_cyclonedx_json_v1_6` | CycloneDX 1.6 JSON |
| `conda_sboms.spdx3.export_spdx_jsonld` | SPDX 3.0.1 JSON-LD |

Each callback accepts `environment` and the keyword-only arguments
`metadata=None` and `output_reproducible=False`. An explicit metadata object
replaces conda's active plugin settings for that call. Import `ExportMetadata`
from `conda_sboms.settings` for either format. It is an alias of the existing
`CycloneDXExportMetadata` class, with identical fields and validation.

See the [CycloneDX reference](cyclonedx-json.md) and
[SPDX reference](spdx-jsonld.md) for exact signatures, mappings, and errors.

## Implementation dependencies

CycloneDX uses `cyclonedx-python-lib` for its official version-specific models
and serializers. SPDX uses standard-library dictionaries and JSON
serialization, with the existing `license-expression` package to validate
known SPDX expressions. Supporting these outputs adds no new runtime package.

Schema and semantic validators are development dependencies. Export callbacks
do not download schemas, JSON-LD contexts, licenses, or package archives.
