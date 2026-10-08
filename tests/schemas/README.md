# Offline SBOM validation resources

These unmodified resources are used only by tests and repository validation
examples. They are not used by exporter callbacks.

The SPDX Working Group publishes the SPDX 3.0.1 context, JSON Schema and
OWL/SHACL model. The specification is licensed under Community-Spec-1.0, with
pre-existing portions under CC-BY-3.0 as described in the accompanying LICENSE.

The CycloneDX project publishes the corrected 1.7 schemas in release 1.7.2
under Apache-2.0. Its JSON references and SPDX XML import are included so
validation does not retrieve additional schemas. CycloneDX 1.6 JSON validation
uses the schema already bundled with cyclonedx-python-lib.

Retrieved on 2026-10-08. The URLs identify upstream versions and the SHA-256
values pin the exact downloaded bytes. Update the assets and these hashes
together when deliberately changing validation resources.

| Local resource | Upstream source | SHA-256 |
| --- | --- | --- |
| `spdx-3.0.1/spdx-context.jsonld` | [Source](https://spdx.org/rdf/3.0.1/spdx-context.jsonld) | `c72b0928f094c83e5c127784edb1ebca2af74a104fcacc007c332b23cbc788bd` |
| `spdx-3.0.1/spdx-json-schema.json` | [Source](https://spdx.org/schema/3.0.1/spdx-json-schema.json) | `582c64e809d5b3ef9bd0c4de13a32391b47b0284a3e8d199569fb96f649234b1` |
| `spdx-3.0.1/spdx-model.ttl` | [Source](https://spdx.org/rdf/3.0.1/spdx-model.ttl) | `30ebb4af2d70a9809044ef46f44cc3dc5125226d70f818a50ed2e1d5f404c593` |
| `spdx-3.0.1/LICENSE` | [Source](https://raw.githubusercontent.com/spdx/spdx-spec/3.0.1/LICENSE) | `8b9e88199429dc9fc3c87604bdb9008c640829a3b5f6b8bd40ba3d0e8b5ca987` |
| `cyclonedx-1.7.2/bom-1.7.schema.json` | [Source](https://raw.githubusercontent.com/CycloneDX/specification/1.7.2/schema/bom-1.7.schema.json) | `73308edec3ab2d38bfffd993e96a042b594314143b6971a6e9ed98bbb6bd76ce` |
| `cyclonedx-1.7.2/bom-1.7.xsd` | [Source](https://raw.githubusercontent.com/CycloneDX/specification/1.7.2/schema/bom-1.7.xsd) | `c1da1a8d42c4022c5a6decd6ba9541081fdbaa2a0715f8fbb4b825411b25cdda` |
| `cyclonedx-1.7.2/spdx.schema.json` | [Source](https://raw.githubusercontent.com/CycloneDX/specification/1.7.2/schema/spdx.schema.json) | `4b345e2329f209f34e960ae2a8e7cb46a166907e6a45e94978565925dc47b359` |
| `cyclonedx-1.7.2/spdx.xsd` | [Source](https://raw.githubusercontent.com/CycloneDX/specification/1.7.2/schema/spdx.xsd) | `cce0672755fac029279801a0244112345e493ec6e6e1b91f496c286753c11ef4` |
| `cyclonedx-1.7.2/jsf-0.82.schema.json` | [Source](https://raw.githubusercontent.com/CycloneDX/specification/1.7.2/schema/jsf-0.82.schema.json) | `8bae002c25e723db7ee1f26afde680ae1a2b1a8f6b4b4b0fd65dc3becb090aae` |
| `cyclonedx-1.7.2/cryptography-defs.schema.json` | [Source](https://raw.githubusercontent.com/CycloneDX/specification/1.7.2/schema/cryptography-defs.schema.json) | `027b059a729a06d591bac79a584ef04f83fc32d91a826fdba6ad3c98a10e5b44` |
| `cyclonedx-1.7.2/LICENSE` | [Source](https://raw.githubusercontent.com/CycloneDX/specification/1.7.2/LICENSE) | `6c29f22a4a7385285c6f579ec9f33c5e989f00739d6b257243a0b082ec9447ae` |
