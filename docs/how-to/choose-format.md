# Choose an output format

Use the specification version and serialization your downstream consumer
accepts. A consumer that accepts SPDX 2.3 JSON does not necessarily accept
SPDX 3.0.1 JSON-LD. Support for CycloneDX JSON does not imply support
for CycloneDX XML or every specification version.

The [format overview](../reference/formats.md) lists every supported version,
alias, and filename pattern. CycloneDX 1.7 XML, CycloneDX 1.6 JSON, and SPDX
3.0.1 JSON-LD are unreleased. Run these examples from the
[source development environment](install.md).

## Use CycloneDX 1.7 JSON

Use the versioned name when pinning the output in automation:

```console
pixi run --locked -e dev conda export --name my-environment --from-history --format cyclonedx-json-v1.7 --file environment.cdx.json
```

The aliases `cyclonedx-json`, `cyclonedx`, and `cdx-json` currently select the
same output. A `.cdx.json` filename also detects this format automatically.

## Use CycloneDX 1.7 XML

```console
pixi run --locked -e dev conda export --name my-environment --from-history --format cyclonedx-xml-v1.7 --file environment.cdx.xml
```

The `cyclonedx-xml` and `cdx-xml` aliases select the same output, which describes
the same conda inventory as CycloneDX 1.7 JSON.

## Use CycloneDX 1.6 JSON for an older consumer

Select 1.6 explicitly:

```console
pixi run --locked -e dev conda export --name my-environment --from-history --format cyclonedx-json-v1.6 --file environment-1.6.cdx.json
```

The explicit format takes precedence over the filename. Without it, the
`.cdx.json` extension selects 1.7. The 1.6 exporter has no aliases.

## Use SPDX 3.0.1 JSON-LD

```console
pixi run --locked -e dev conda export --name my-environment --from-history --format spdx-jsonld-v3.0.1 --file environment.spdx.jsonld
```

The `spdx-jsonld` alias selects this output. Both `.spdx.jsonld` and
`.spdx3.json` filenames detect it. The `.spdx.json` extension is unregistered
because it is commonly associated with SPDX 2 documents.
SPDX 2.3 is not implemented.

## Check consumer compatibility

Check and record support, ingestion, and analysis separately:

1. Check that the consumer's current documentation lists the exact specification
   version and serialization.
2. Test whether the installed consumer accepts a real export from your environment.
3. Confirm that it recognizes conda package identities and performs the analysis
   you need.

Passing [schema validation](validate.md) establishes document structure. It
does not prove that an ingesting service recognizes conda PURLs or can find
vulnerabilities in conda packages. Services may also require provenance
metadata beyond the standard, such as
[GitLab's CycloneDX properties](https://docs.gitlab.com/development/sec/cyclonedx_property_taxonomy/).
The exporter does not add those service-specific properties.
