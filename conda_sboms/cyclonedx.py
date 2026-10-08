from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from urllib.parse import quote
from uuid import UUID
from xml.dom import minidom

from conda.exceptions import CondaValueError
from cyclonedx.model import (
    ExternalReference,
    ExternalReferenceType,
    HashAlgorithm,
    HashType,
    Property,
    XsUri,
)
from cyclonedx.model.bom import Bom, BomMetaData
from cyclonedx.model.component import Component, ComponentType
from cyclonedx.model.contact import OrganizationalContact, OrganizationalEntity
from cyclonedx.model.license import DisjunctiveLicense
from cyclonedx.model.tool import ToolRepository
from cyclonedx.output import make_outputter
from cyclonedx.schema import OutputFormat, SchemaVersion
from packageurl import PackageURL

from . import __version__
from ._conda import (
    package_dependency_graph,
    package_identity,
    root_dependency_references,
    validated_hashes,
)
from .settings import CycloneDXExportMetadata

if TYPE_CHECKING:
    from typing import Final

    from conda.models.environment import Environment
    from conda.models.match_spec import MatchSpec
    from conda.models.records import PackageRecord
    from cyclonedx.model.bom_ref import BomRef

FORMAT: Final = "cyclonedx-json-v1.7"
ALIASES: Final = ("cyclonedx-json", "cyclonedx", "cdx-json")
DEFAULT_FILENAMES: Final = ("*.cdx.json",)
DESCRIPTION: Final = "CycloneDX 1.7 JSON software bill of materials"


class CycloneDXPackage:
    """A resolved conda package represented as a CycloneDX component."""

    def __init__(self, record: PackageRecord) -> None:
        self.record = record

        purl, properties, url = package_identity(record)
        hashes = [
            HashType(alg=HashAlgorithm(algorithm), content=value)
            for algorithm, value in validated_hashes(record)
        ]
        external_references = (
            [
                ExternalReference(
                    type=ExternalReferenceType.DISTRIBUTION,
                    url=XsUri(url),
                )
            ]
            if url
            else []
        )

        licenses = []
        if record.license:
            licenses.append(DisjunctiveLicense(name=record.license))

        self.component = Component(
            type=ComponentType.LIBRARY,
            name=str(record.name),
            version=str(record.version),
            bom_ref=purl.to_string(),
            purl=purl,
            hashes=hashes,
            licenses=licenses,
            external_references=external_references,
            properties=[
                Property(name=name, value=value) for name, value in properties.items()
            ],
        )


class CycloneDXDependencyGraph:
    """Dependency state derived from the resolved conda packages."""

    def __init__(self, packages: list[CycloneDXPackage]) -> None:
        self.references_by_name = {
            package.record.name.lower(): package.component.bom_ref
            for package in packages
        }
        self.components_by_reference = {
            package.component.bom_ref: package.component for package in packages
        }
        self.edges, self.missing_edge_count, self.incomplete_references = (
            package_dependency_graph(
                ((package.record, package.component.bom_ref) for package in packages),
                self.references_by_name,
            )
        )

    def root_references(self, requested_packages: list[MatchSpec]) -> list[BomRef]:
        """Choose requested roots or infer roots that cover the whole graph."""
        return root_dependency_references(
            requested_packages, self.edges, self.references_by_name
        )


class CycloneDXExporter:
    """Build a CycloneDX document from a resolved conda environment."""

    def __init__(
        self,
        environment: Environment,
        *,
        metadata: CycloneDXExportMetadata | None = None,
        output_reproducible: bool = False,
        schema_version: str = "1.7",
        serialization: str = "json",
    ) -> None:
        if (schema_version, serialization) not in {
            ("1.7", "json"),
            ("1.6", "json"),
            ("1.7", "xml"),
        }:
            raise CondaValueError(
                f"Unsupported CycloneDX output: {schema_version} {serialization}. "
                "Choose JSON 1.7, JSON 1.6, or XML 1.7."
            )
        self.schema_version = schema_version
        self.serialization = serialization
        if not environment.explicit_packages:
            raise CondaValueError(
                "CycloneDX export requires exact package records. Export an installed "
                "environment or a resolved lockfile."
            )

        records = sorted(
            environment.explicit_packages,
            key=lambda record: (
                record.name.lower(),
                str(record.version),
                record.build,
                record.subdir,
            ),
        )
        self.packages = [CycloneDXPackage(record) for record in records]
        self.graph = CycloneDXDependencyGraph(self.packages)
        self.root_references = self.graph.root_references(
            environment.requested_packages
        )
        self.roots_inferred = not environment.requested_packages
        self.root_completeness = (
            "incomplete" if any(environment.external_packages.values()) else "unknown"
        )

        self.metadata = (
            metadata if metadata is not None else CycloneDXExportMetadata.from_context()
        )
        name = self.metadata.product_name or str(environment.name or "")
        if not self.metadata.product_name and (not name or "/" in name or "\\" in name):
            name = "conda-environment"
        root_source = (
            "inferred-graph-roots" if self.roots_inferred else "requested-packages"
        )
        properties = [
            Property(name="conda:environment:platform", value=environment.platform),
            Property(name="conda:environment:scope", value="resolved-conda-packages"),
            Property(
                name="conda:environment:root-dependency-source",
                value=root_source,
            ),
        ]
        omitted_external = sum(
            len(packages) for packages in environment.external_packages.values()
        )
        if omitted_external:
            properties.append(
                Property(
                    name="conda:environment:external-packages-omitted",
                    value=str(omitted_external),
                )
            )
        if environment.virtual_packages:
            properties.append(
                Property(
                    name="conda:environment:virtual-packages-omitted",
                    value=str(len(environment.virtual_packages)),
                )
            )
        if self.graph.missing_edge_count:
            properties.append(
                Property(
                    name="conda:environment:dependency-edges-omitted",
                    value=str(self.graph.missing_edge_count),
                )
            )
        identity = quote(name, safe="")
        if self.metadata.product_version:
            identity += f"@{quote(self.metadata.product_version, safe='')}"
        self.root = Component(
            type=ComponentType.APPLICATION,
            name=name,
            version=self.metadata.product_version,
            bom_ref=(
                f"conda-environment:{identity}"
                f"?platform={quote(environment.platform, safe='')}"
            ),
            manufacturer=(
                OrganizationalEntity(
                    name=self.metadata.product_manufacturer,
                    urls=(
                        [XsUri(self.metadata.product_manufacturer_url)]
                        if self.metadata.product_manufacturer_url
                        else None
                    ),
                )
                if self.metadata.product_manufacturer
                else None
            ),
            properties=properties,
        )

        self.output_reproducible = output_reproducible
        epoch = os.environ.get("SOURCE_DATE_EPOCH")
        if output_reproducible:
            self.timestamp = None
        elif epoch is None:
            self.timestamp = datetime.now(timezone.utc)
        else:
            try:
                value = int(epoch)
                if value < 0:
                    raise ValueError
                self.timestamp = datetime.fromtimestamp(value, timezone.utc)
            except (OverflowError, OSError, ValueError) as error:
                raise CondaValueError(
                    "SOURCE_DATE_EPOCH must be a non-negative integer"
                ) from error

    def export(self) -> str:
        """Serialize the environment with the selected version and encoding."""
        tool = Component(
            type=ComponentType.APPLICATION,
            name="conda-sboms",
            version=__version__,
            bom_ref=f"tool:conda-sboms@{quote(__version__, safe='')}",
            purl=PackageURL(type="pypi", name="conda-sboms", version=__version__),
        )
        components = [package.component for package in self.packages]
        # cyclonedx-python-lib requires a UUID and supplies a missing timestamp.
        # Remove these optional values from the serialized document as requested below.
        bom = Bom(
            serial_number=UUID("00000000-0000-4000-8000-000000000000"),
            metadata=BomMetaData(
                timestamp=self.timestamp,
                tools=ToolRepository(components=[tool]),
                component=self.root,
                manufacturer=(
                    OrganizationalEntity(
                        name=self.metadata.author_organization,
                        urls=(
                            [XsUri(self.metadata.author_organization_url)]
                            if self.metadata.author_organization_url
                            else None
                        ),
                    )
                    if self.metadata.author_organization
                    else None
                ),
                authors=(
                    [
                        OrganizationalContact(
                            name=self.metadata.author_name,
                            email=self.metadata.author_email,
                        )
                    ]
                    if self.metadata.author_name
                    else None
                ),
                properties=(
                    [Property(name="cdx:reproducible", value="true")]
                    if self.output_reproducible
                    else None
                ),
            ),
            components=components,
        )
        for component in components:
            bom.register_dependency(
                component,
                [
                    self.graph.components_by_reference[reference]
                    for reference in self.graph.edges[component.bom_ref]
                ],
            )
        bom.register_dependency(
            self.root,
            [
                self.graph.components_by_reference[reference]
                for reference in self.root_references
            ],
        )

        serialized = make_outputter(
            bom,
            output_format=(
                OutputFormat.JSON if self.serialization == "json" else OutputFormat.XML
            ),
            schema_version=(
                SchemaVersion.V1_7
                if self.schema_version == "1.7"
                else SchemaVersion.V1_6
            ),
        ).output_as_string()
        root_composition = {
            "aggregate": self.root_completeness,
            "assemblies": [self.root.bom_ref.value],
        }
        if self.roots_inferred:
            root_composition["dependencies"] = [self.root.bom_ref.value]
        compositions = [root_composition]
        if self.graph.incomplete_references:
            compositions.append(
                {
                    "aggregate": "incomplete",
                    "dependencies": sorted(
                        reference.value
                        for reference in self.graph.incomplete_references
                    ),
                }
            )
        if self.serialization == "json":
            document = json.loads(serialized)
            document.pop("serialNumber")
            if self.output_reproducible:
                document["metadata"].pop("timestamp")
            for dependency in document["dependencies"]:
                dependency.setdefault("dependsOn", [])
            document["compositions"] = compositions
            return json.dumps(document, indent=2, sort_keys=True) + "\n"

        document = minidom.parseString(serialized)
        root = document.documentElement
        namespace = root.namespaceURI
        root.removeAttribute("serialNumber")
        if self.output_reproducible:
            metadata = root.getElementsByTagNameNS(namespace, "metadata")[0]
            timestamp = metadata.getElementsByTagNameNS(namespace, "timestamp")[0]
            metadata.removeChild(timestamp)
        elements = document.createElementNS(namespace, "compositions")
        for composition in compositions:
            element = document.createElementNS(namespace, "composition")
            aggregate = document.createElementNS(namespace, "aggregate")
            aggregate.appendChild(document.createTextNode(composition["aggregate"]))
            element.appendChild(aggregate)
            for collection, name in (
                ("assemblies", "assembly"),
                ("dependencies", "dependency"),
            ):
                if collection not in composition:
                    continue
                references = document.createElementNS(namespace, collection)
                for reference in composition[collection]:
                    child = document.createElementNS(namespace, name)
                    child.setAttribute("ref", reference)
                    references.appendChild(child)
                element.appendChild(references)
            elements.appendChild(element)
        dependencies = next(
            child
            for child in root.childNodes
            if child.namespaceURI == namespace and child.localName == "dependencies"
        )
        root.insertBefore(elements, dependencies.nextSibling)
        return document.toprettyxml(indent="  ")


def export_cyclonedx_json(
    environment: Environment,
    *,
    metadata: CycloneDXExportMetadata | None = None,
    output_reproducible: bool = False,
) -> str:
    """Export a resolved conda environment as CycloneDX 1.7 JSON."""
    return CycloneDXExporter(
        environment,
        metadata=metadata,
        output_reproducible=output_reproducible,
    ).export()


def export_cyclonedx_json_v1_6(
    environment: Environment,
    *,
    metadata: CycloneDXExportMetadata | None = None,
    output_reproducible: bool = False,
) -> str:
    """Export a resolved conda environment as CycloneDX 1.6 JSON."""
    return CycloneDXExporter(
        environment,
        metadata=metadata,
        output_reproducible=output_reproducible,
        schema_version="1.6",
    ).export()


def export_cyclonedx_xml(
    environment: Environment,
    *,
    metadata: CycloneDXExportMetadata | None = None,
    output_reproducible: bool = False,
) -> str:
    """Export a resolved conda environment as CycloneDX 1.7 XML."""
    return CycloneDXExporter(
        environment,
        metadata=metadata,
        output_reproducible=output_reproducible,
        serialization="xml",
    ).export()
