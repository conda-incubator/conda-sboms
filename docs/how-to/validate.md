# Validate an SBOM

Validate the final serialized document with the official resources for its
exact specification version. The source checkout includes validators and
pinned schemas used by the test suite. These are development tools, not an
installed `conda-sboms` command or a supported public Python API.

## Prepare the development environment

Follow [source installation](install.md), then run
these commands from the repository root:

```console
pixi install --locked -e dev
```

Installing the environment can require network access. Once it is installed,
the validation calls below use only local schemas and contexts.

## Validate CycloneDX JSON

This command handles both supported JSON specification versions:

```console
pixi run --locked -e dev python -c "import json, pathlib; from tests.sbom_validation import validate_cyclonedx_json; validate_cyclonedx_json(json.loads(pathlib.Path('environment.cdx.json').read_text(encoding='utf-8'))); print('CycloneDX JSON validation passed')"
```

The validator reads `specVersion` and selects the corresponding official
JSON Schema. The 1.7 checks use the corrected schemas from the CycloneDX 1.7.2
schema release. The specification version inside the document remains `1.7`.

## Validate CycloneDX XML

```console
pixi run --locked -e dev python -c "import pathlib; from tests.sbom_validation import validate_cyclonedx_xml; validate_cyclonedx_xml(pathlib.Path('environment.cdx.xml').read_text(encoding='utf-8')); print('CycloneDX XML validation passed')"
```

This validates the complete XML output against the CycloneDX 1.7 XSD,
including its locally stored schema imports.

## Validate SPDX 3.0.1 JSON-LD

```console
pixi run --locked -e dev python -c "import json, pathlib; from tests.sbom_validation import validate_spdx; validate_spdx(json.loads(pathlib.Path('environment.spdx.jsonld').read_text(encoding='utf-8'))); print('SPDX JSON Schema and SHACL validation passed')"
```

The validator first checks JSON Schema, then expands JSON-LD into RDF and
checks the official model with SHACL. It substitutes the pinned local JSON-LD
context in a copy of the document. It does not change the exported file or
fetch the context URI over the network.

SPDX JSON Schema alone cannot validate every relationship and model rule.
Run both checks. The test suite includes a deliberately invalid semantic
document to confirm that SHACL validation rejects missing required data.

## Interpret the result

Each command exits unsuccessfully if validation fails. A passing result
confirms the document's schema or model validity. It does not prove complete
product coverage, truthful caller-supplied metadata, legal conformity, or
compatibility with a particular vulnerability scanner.

See [consumer compatibility](choose-format.md)
and [coverage and compliance](../explanation/coverage-and-compliance.md) for
the separate checks needed for those claims.
