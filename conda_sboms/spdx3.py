from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from conda.exceptions import CondaValueError
from license_expression import ExpressionError, get_spdx_licensing

from . import __version__
from ._conda import (
    package_dependency_graph,
    package_identity,
    root_dependency_references,
    validated_hashes,
)
from .settings import ExportMetadata

if TYPE_CHECKING:
    from conda.models.environment import Environment

FORMAT = "spdx-jsonld-v3.0.1"
ALIASES = ("spdx-jsonld",)
DEFAULT_FILENAMES = ("*.spdx3.json", "*.spdx.jsonld")
DESCRIPTION = "SPDX 3.0.1 JSON-LD software bill of materials"
CONTEXT = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
NO_ASSERTION_ELEMENT = "https://spdx.org/rdf/3.0.1/terms/Core/NoAssertionElement"
NO_ASSERTION_LICENSE = (
    "https://spdx.org/rdf/3.0.1/terms/ExpandedLicensing/NoAssertionLicense"
)


def _properties(values: dict[str, str]) -> list[dict]:
    """Map conda metadata to SPDX's standard key/value extension."""
    return [
        {
            "type": "extension_CdxPropertiesExtension",
            "extension_cdxProperty": [
                {
                    "type": "extension_CdxPropertyEntry",
                    "extension_cdxPropName": name,
                    "extension_cdxPropValue": value,
                }
                for name, value in sorted(values.items())
            ],
        }
    ]


def export_spdx_jsonld(
    environment: Environment,
    *,
    metadata: ExportMetadata | None = None,
    output_reproducible: bool = False,
) -> str:
    """Render the resolved conda inventory as SPDX 3.0.1 JSON-LD."""
    if not environment.explicit_packages:
        raise CondaValueError(
            "SPDX export requires exact package records. Export an installed "
            "environment or a resolved lockfile."
        )
    metadata = metadata if metadata is not None else ExportMetadata.from_context()
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch is None:
        if output_reproducible:
            raise CondaValueError("Reproducible SPDX output requires SOURCE_DATE_EPOCH")
        timestamp = datetime.now(timezone.utc)
    else:
        try:
            value = int(epoch)
            if value < 0:
                raise ValueError
            timestamp = datetime.fromtimestamp(value, timezone.utc)
        except (ValueError, OverflowError, OSError) as error:
            raise CondaValueError(
                "SOURCE_DATE_EPOCH must be a non-negative integer within "
                "the supported datetime range"
            ) from error

    records = sorted(environment.explicit_packages, key=lambda record: record.name)
    references = {
        record.name.lower(): f"package-{i}" for i, record in enumerate(records)
    }
    edges, missing_count, incomplete = package_dependency_graph(
        ((record, references[record.name.lower()]) for record in records), references
    )
    roots = root_dependency_references(
        environment.requested_packages, edges, references
    )
    name = metadata.product_name or str(environment.name or "")
    if not metadata.product_name and (not name or "/" in name or "\\" in name):
        name = "conda-environment"
    omitted_external = sum(
        len(items) for items in environment.external_packages.values()
    )
    root_properties = {
        "conda:environment:platform": environment.platform,
        "conda:environment:scope": "resolved-conda-packages",
        "conda:environment:root-dependency-source": (
            "requested-packages"
            if environment.requested_packages
            else "inferred-graph-roots"
        ),
    }
    for key, count in (
        ("external-packages-omitted", omitted_external),
        ("virtual-packages-omitted", len(environment.virtual_packages)),
        ("dependency-edges-omitted", missing_count),
    ):
        if count:
            root_properties[f"conda:environment:{key}"] = str(count)

    root = {
        "type": "software_Package",
        "spdxId": "environment",
        "name": name,
        "software_primaryPurpose": "application",
        "extension": _properties(root_properties),
        "comment": (
            "Resolved conda packages only. Coverage of vendored content, statically "
            "linked libraries, operating-system components, virtual packages, and "
            "external package ecosystems cannot be established from conda records."
        ),
    }
    if metadata.product_version:
        root["software_packageVersion"] = metadata.product_version
    graph = [
        {
            "type": "CreationInfo",
            "@id": "creation",
            "specVersion": "3.0.1",
            "created": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "createdBy": ["tool"],
        },
        {
            "type": "SoftwareAgent",
            "spdxId": "tool",
            "name": f"conda-sboms {__version__}",
        },
        root,
    ]
    for identifier, agent_type, agent_name, url in (
        (
            "manufacturer",
            "Organization",
            metadata.product_manufacturer,
            metadata.product_manufacturer_url,
        ),
        ("author", "Person", metadata.author_name, None),
        (
            "author-organization",
            "Organization",
            metadata.author_organization,
            metadata.author_organization_url,
        ),
    ):
        if not agent_name:
            continue
        agent = {"type": agent_type, "spdxId": identifier, "name": agent_name}
        if url:
            agent["externalRef"] = [
                {
                    "type": "ExternalRef",
                    "externalRefType": "altWebPage",
                    "locator": [url],
                }
            ]
        if identifier == "author" and metadata.author_email:
            agent["externalIdentifier"] = [
                {
                    "type": "ExternalIdentifier",
                    "externalIdentifierType": "email",
                    "identifier": metadata.author_email,
                }
            ]
        if identifier == "manufacturer":
            root["originatedBy"] = [identifier]
        else:
            graph[0]["createdBy"].append(identifier)
        graph.append(agent)

    licensing = get_spdx_licensing()
    for record in records:
        identifier = references[record.name.lower()]
        purl, properties, url = package_identity(record)
        package = {
            "type": "software_Package",
            "spdxId": identifier,
            "name": record.name,
            "software_primaryPurpose": "library",
            "software_packageVersion": record.version,
            "software_packageUrl": str(purl),
        }
        if url:
            package["software_downloadLocation"] = url
        hashes = validated_hashes(record)
        if hashes:
            package["verifiedUsing"] = [
                {
                    "type": "Hash",
                    "algorithm": algorithm.lower().replace("-", ""),
                    "hashValue": value,
                }
                for algorithm, value in hashes
            ]
        license_text = record.license
        license_id = NO_ASSERTION_LICENSE
        try:
            expression = licensing.parse(license_text, validate=True, strict=True)
        except ExpressionError:
            expression = None
        if expression is not None:
            license_id = f"{identifier}-license"
            graph.append(
                {
                    "type": "simplelicensing_LicenseExpression",
                    "spdxId": license_id,
                    "simplelicensing_licenseExpression": str(expression),
                }
            )
        elif license_text:
            properties["conda:package:license"] = license_text
        package["extension"] = _properties(properties)
        graph.extend(
            [
                package,
                {
                    "type": "Relationship",
                    "spdxId": f"{identifier}-declared-license",
                    "from": identifier,
                    "relationshipType": "hasDeclaredLicense",
                    "to": [license_id],
                    **(
                        {
                            "comment": (
                                "The original conda license label is retained as "
                                "metadata. It is not a validated SPDX expression."
                            )
                        }
                        if license_text and license_id == NO_ASSERTION_LICENSE
                        else {}
                    ),
                },
            ]
        )
    for identifier, targets in [("environment", roots), *sorted(edges.items())]:
        relationship = {
            "type": "Relationship",
            "spdxId": f"{identifier}-dependencies",
            "from": identifier,
            "relationshipType": "dependsOn",
            "to": targets or [NO_ASSERTION_ELEMENT],
            "completeness": "incomplete" if identifier in incomplete else "noAssertion",
        }
        if not targets:
            relationship["comment"] = (
                "Declared dependencies have no resolved target in this inventory."
                if identifier in incomplete
                else "No conda dependency targets were identified. "
                "Other dependency coverage is unknown."
            )
        graph.append(relationship)
    graph.extend(
        [
            {
                "type": "Relationship",
                "spdxId": "environment-contains",
                "from": "environment",
                "relationshipType": "contains",
                "to": sorted(references.values()),
                "completeness": "incomplete" if omitted_external else "noAssertion",
            },
            {
                "type": "simplelicensing_LicenseExpression",
                "spdxId": "data-license",
                "simplelicensing_licenseExpression": "CC0-1.0",
            },
        ]
    )
    graph.append(
        {
            "type": "software_Sbom",
            "spdxId": "sbom",
            "rootElement": ["environment"],
            "element": sorted(node["spdxId"] for node in graph if "spdxId" in node),
        }
    )
    graph.append(
        {
            "type": "SpdxDocument",
            "spdxId": "document",
            "dataLicense": "data-license",
            "rootElement": ["sbom"],
            "element": sorted(node["spdxId"] for node in graph if "spdxId" in node),
        }
    )
    for node in graph[1:]:
        node["creationInfo"] = "creation"
    # Hash sanitized content before assigning identifiers to avoid a circular digest.
    digest = hashlib.sha256(
        json.dumps(graph, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    namespace = f"https://conda-incubator.github.io/conda-sboms/spdx/{digest}/"
    identifiers = {node.get("spdxId", node.get("@id")) for node in graph}
    for node in graph:
        for key in ("spdxId", "@id", "creationInfo", "from", "dataLicense"):
            if key in node and node[key] in identifiers:
                node[key] = namespace + node[key]
        for key in ("createdBy", "originatedBy", "to", "element", "rootElement"):
            if key in node:
                node[key] = [
                    namespace + value if value in identifiers else value
                    for value in node[key]
                ]
    return (
        json.dumps({"@context": CONTEXT, "@graph": graph}, indent=2, sort_keys=True)
        + "\n"
    )
