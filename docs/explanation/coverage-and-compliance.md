# Coverage and compliance

`conda-sboms` describes the resolved conda package graph supplied to an
exporter. That is useful evidence, but it is narrower than the complete
software composition of many products.

## What conda records establish

An exact conda package record identifies one selected package artifact. It can
carry the package name, version, build, platform, archive filename, hashes,
license text, distribution URL, and direct runtime requirements. The exporter
maps that information without opening the archive or contacting its channel.

This produces a metadata-derived inventory of the conda artifacts selected for
one environment and platform. Byte-for-byte repeatability requires a fixed
`SOURCE_DATE_EPOCH`, unchanged complete input, and the same serializer
environment. Dependency edges represent declared `depends` entries whose
target name exists in the supplied records.

## What conda records do not establish

Package metadata alone does not reveal every constituent inside an archive. A
package may contain vendored source, a statically linked library, or generated
assets that do not appear as separate conda dependencies. The open
[conda SBOM discussion](https://github.com/conda/ceps/issues/127) tracks
package-build metadata for that gap.

The exporter also omits:

- packages from pip and other external ecosystems
- virtual packages and operating-system components
- supplier and creator identities for individual package components
- product manufacturer and SBOM author identities unless supplied by the caller
- vulnerability, VEX, signature, and attestation data

CycloneDX root compositions and SPDX relationship completeness mark overall
coverage as unproven. Conda-specific
properties record known external-package, virtual-package, and missing-edge
counts supplied by the input. These signals do not fill the missing inventory.

## Requested roots and inferred roots

Top-level dependencies describe user intent. The resolved graph does not always
preserve that intent.

When a client supplies `Environment.requested_packages`, the exporter connects
the root application to those resolved packages. `conda export --from-history`
can preserve this information when the prefix history contains it. When
requested packages are absent, the exporter must infer root edges. The
[CycloneDX reference](../reference/cyclonedx-json.md)
defines that algorithm, which is also used by the SPDX exporter.

Conda 26.7 populates `requested_packages` with every installed conda package
when a prefix is exported without `--from-history`. In that case,
`requested-packages` is not an authoritative list of user-requested roots. With
`--from-history`, conda uses history for requested packages but does not populate
`external_packages`. Conda may warn about detected pip packages without passing
them to the exporter, so those packages do not produce an omission count or
make the root composition `incomplete`.

## Cyber Resilience Act requirements

Part II, point 1 of Annex I to the EU
[Cyber Resilience Act](https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng)
sets a requirement, applicable from 11 December 2027, for manufacturers of
products in scope to identify and document vulnerabilities and components. The
documentation includes an SBOM in a commonly used, machine-readable format
that covers at least top-level dependencies.

CycloneDX and SPDX are machine-readable formats supported by this project.
The regulation itself does not prescribe either format. Article 13(24)
allows the European Commission to specify SBOM formats and elements through
implementing acts.

A schema-valid SBOM does not establish product conformity. A manufacturer must
determine which components belong to the product, supply truthful product and organization
metadata, address components outside conda, maintain the inventory for the
relevant release, and meet the CRA's other requirements. The output from
`conda-sboms` can contribute to that technical documentation.

## Conda standards status

No accepted conda Enhancement Proposal currently defines an SBOM format or CRA
profile. The exporters follow the selected
[CycloneDX specification](https://cyclonedx.org/specification/overview/) or
[SPDX 3.0.1 specification](https://spdx.github.io/spdx-spec/v3.0.1/) and the published
[package-url conda type](https://github.com/package-url/purl-spec/blob/main/docs/types/definitions/conda-definition.md).

The open [conda PURL proposal](https://github.com/conda/ceps/pull/159) may
change conda package URL conventions if accepted. Available hashes, sanitized
distribution URLs, and conda properties remain in the document so identity
does not depend on the PURL alone.
