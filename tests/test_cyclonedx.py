from __future__ import annotations

import json
from xml.etree import ElementTree

import pytest
from conda.exceptions import CondaValueError
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
from conda.models.records import PackageRecord
from cyclonedx.schema import SchemaVersion

from conda_sboms.cyclonedx import (
    CycloneDXDependencyGraph,
    CycloneDXExporter,
    CycloneDXPackage,
    export_cyclonedx_json,
    export_cyclonedx_json_v1_6,
    export_cyclonedx_xml,
)
from conda_sboms.settings import CycloneDXExportMetadata

from .records import package_record
from .sbom_validation import validate_cyclonedx_json, validate_cyclonedx_xml


def component_named(document: dict, name: str) -> dict:
    return next(
        component for component in document["components"] if component["name"] == name
    )


def component_properties(component: dict) -> dict[str, str]:
    return {
        property_["name"]: property_["value"] for property_ in component["properties"]
    }


def dependency_map(document: dict) -> dict[str, list[str]]:
    return {
        dependency["ref"]: dependency["dependsOn"]
        for dependency in document["dependencies"]
    }


def test_public_object_api(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    record = package_record("example")
    package = CycloneDXPackage(record)
    graph = CycloneDXDependencyGraph([package])
    environment = Environment(
        name="demo",
        platform="linux-64",
        explicit_packages=[record],
        requested_packages=[MatchSpec("example")],
    )
    metadata = CycloneDXExportMetadata()
    reference = package.component.bom_ref
    exporter = CycloneDXExporter(environment, metadata=metadata)

    assert package.record is record
    assert graph.references_by_name == {record.name.lower(): reference}
    assert graph.components_by_reference == {reference: package.component}
    assert graph.edges == {reference: []}
    assert graph.missing_edge_count == 0
    assert graph.incomplete_references == set()
    assert graph.root_references(environment.requested_packages) == [reference]
    assert exporter.packages[0].record is record
    assert exporter.graph.edges == {reference: []}
    assert exporter.metadata is metadata
    assert exporter.root_references == [reference]
    assert exporter.roots_inferred is False
    assert exporter.root_completeness == "unknown"
    assert exporter.root.name == "demo"
    assert exporter.output_reproducible is False
    assert exporter.timestamp.isoformat() == "1970-01-01T00:00:00+00:00"
    assert exporter.export() == (export_cyclonedx_json(environment, metadata=metadata))


@pytest.mark.parametrize(
    ("export", "schema_version"),
    [
        (export_cyclonedx_json, SchemaVersion.V1_7),
        (export_cyclonedx_json_v1_6, SchemaVersion.V1_6),
    ],
)
def test_export_maps_resolved_environment(
    monkeypatch: pytest.MonkeyPatch, export, schema_version: SchemaVersion
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    openssl = package_record("openssl", sha256="c" * 64)
    python = package_record(
        "python",
        version="3.13.7",
        depends=("openssl >=3", "__linux >=6"),
        sha256="A" * 64,
        md5="b" * 32,
        license_name="PSF license and custom terms",
        channel="conda-forge/label/dev",
        url=(
            "https://user:password@conda.anaconda.org/t/secret/conda-forge/"
            "label/dev/linux-64/python-3.13.7-h123_0.conda?token=also-secret"
        ),
    )
    virtual = PackageRecord(
        name="__linux",
        version="6.0",
        build="0",
        build_number=0,
        channel="@",
        subdir="linux-64",
        depends=[],
    )
    environment = Environment(
        name="demo",
        prefix="/Users/alice/private-prefix",
        platform="linux-64",
        explicit_packages=[python, openssl],
        requested_packages=[MatchSpec("python")],
        external_packages={"pip": ["example==1"]},
        virtual_packages=[virtual],
    )

    output = export(environment, metadata=CycloneDXExportMetadata())
    document = json.loads(output)

    assert output.endswith("\n")
    assert document["bomFormat"] == "CycloneDX"
    assert document["specVersion"] == schema_version.to_version()
    assert document["version"] == 1
    assert "serialNumber" not in document
    assert document["metadata"]["timestamp"] == "1970-01-01T00:00:00+00:00"
    assert document["metadata"]["tools"]["components"][0]["name"] == "conda-sboms"
    assert "authors" not in document["metadata"]
    assert "manufacturer" not in document["metadata"]

    python_component = component_named(document, "python")
    assert python_component["purl"] == (
        "pkg:conda/python@3.13.7?build=h123_0&channel=conda-forge/label/dev"
        "&subdir=linux-64&type=conda"
    )
    assert python_component["hashes"] == [
        {"alg": "MD5", "content": "b" * 32},
        {"alg": "SHA-256", "content": "a" * 64},
    ]
    assert python_component["licenses"] == [
        {"license": {"name": "PSF license and custom terms"}}
    ]
    assert python_component["externalReferences"] == [
        {
            "type": "distribution",
            "url": (
                "https://conda.anaconda.org/conda-forge/label/dev/linux-64/"
                "python-3.13.7-h123_0.conda"
            ),
        }
    ]
    python_properties = component_properties(python_component)
    assert python_properties["conda:package:channel"] == "conda-forge/label/dev"
    assert python_properties["conda:package:filename"] == "python-3.13.7-h123_0.conda"

    root = document["metadata"]["component"]
    assert root["name"] == "demo"
    assert "version" not in root
    assert "manufacturer" not in root
    assert "/Users/alice/private-prefix" not in output
    root_properties = component_properties(root)
    assert root_properties["conda:environment:root-dependency-source"] == (
        "requested-packages"
    )
    assert root_properties["conda:environment:external-packages-omitted"] == "1"
    assert root_properties["conda:environment:virtual-packages-omitted"] == "1"
    assert root_properties["conda:environment:dependency-edges-omitted"] == "1"

    dependencies = dependency_map(document)
    assert dependencies[root["bom-ref"]] == [python_component["bom-ref"]]
    assert dependencies[python_component["bom-ref"]] == [
        component_named(document, "openssl")["bom-ref"]
    ]
    assert dependencies[component_named(document, "openssl")["bom-ref"]] == []
    assert document["compositions"] == [
        {
            "aggregate": "incomplete",
            "assemblies": [root["bom-ref"]],
        },
        {
            "aggregate": "incomplete",
            "dependencies": [python_component["bom-ref"]],
        },
    ]
    validate_cyclonedx_json(document)


def test_inferred_roots_cover_a_disconnected_cycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = Environment(
        platform="linux-64",
        explicit_packages=[
            package_record("root", depends=("leaf",)),
            package_record("leaf"),
            package_record("cycle-a", depends=("cycle-b",)),
            package_record("cycle-b", depends=("cycle-a",)),
        ],
    )

    document = json.loads(
        export_cyclonedx_json(environment, metadata=CycloneDXExportMetadata())
    )
    root = document["metadata"]["component"]
    dependencies = dependency_map(document)

    assert dependencies[root["bom-ref"]] == [
        component_named(document, "cycle-a")["bom-ref"],
        component_named(document, "root")["bom-ref"],
    ]
    assert component_properties(root)["conda:environment:root-dependency-source"] == (
        "inferred-graph-roots"
    )
    assert document["compositions"] == [
        {
            "aggregate": "unknown",
            "assemblies": [root["bom-ref"]],
            "dependencies": [root["bom-ref"]],
        }
    ]


@pytest.mark.parametrize(
    "export",
    [export_cyclonedx_json, export_cyclonedx_json_v1_6, export_cyclonedx_xml],
)
def test_export_is_deterministic_for_reordered_records(
    monkeypatch: pytest.MonkeyPatch,
    export,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "1720000000")
    first = package_record("first", depends=("second",))
    second = package_record("second")

    forward = Environment(
        platform="linux-64",
        explicit_packages=[first, second],
    )
    reverse = Environment(
        platform="linux-64",
        explicit_packages=[second, first],
    )

    assert export(forward, metadata=CycloneDXExportMetadata()) == export(
        reverse, metadata=CycloneDXExportMetadata()
    )


@pytest.mark.parametrize(
    ("export", "schema_version"),
    [
        (export_cyclonedx_json, SchemaVersion.V1_7),
        (export_cyclonedx_json_v1_6, SchemaVersion.V1_6),
    ],
)
def test_output_reproducible_omits_timestamp(
    monkeypatch: pytest.MonkeyPatch,
    export,
    schema_version: SchemaVersion,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "invalid")
    environment = Environment(
        name="demo",
        platform="linux-64",
        explicit_packages=[package_record("example")],
    )
    exporter = CycloneDXExporter(
        environment,
        metadata=CycloneDXExportMetadata(),
        output_reproducible=True,
        schema_version=schema_version.to_version(),
    )

    output = exporter.export()
    document = json.loads(output)

    assert exporter.output_reproducible is True
    assert exporter.timestamp is None
    assert "timestamp" not in document["metadata"]
    assert document["metadata"]["properties"] == [
        {"name": "cdx:reproducible", "value": "true"}
    ]
    assert output == export(
        environment,
        metadata=CycloneDXExportMetadata(),
        output_reproducible=True,
    )
    validate_cyclonedx_json(document)


def test_local_source_paths_are_not_serialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    posix_path = "/Users/alice/private-channel"
    windows_path = "C:\\Users\\alice\\private-channel"
    relative_path = "./relative/private-channel"
    posix_filename = "private-posix-1.0-h123_0.conda"
    windows_filename = "private-windows-1.0-h123_0.conda"
    relative_filename = "private-relative-1.0-h123_0.conda"
    environment = Environment(
        platform="linux-64",
        explicit_packages=[
            package_record(
                "private-posix",
                channel=f"file://{posix_path}",
                url=f"file://{posix_path}/linux-64/{posix_filename}",
                filename=f"{posix_path}/{posix_filename}",
            ),
            package_record(
                "private-windows",
                channel=windows_path,
                url=f"{windows_path}\\{windows_filename}",
                filename=f"{windows_path}\\{windows_filename}",
            ),
            package_record(
                "private-relative",
                channel=relative_path,
                url=f"{relative_path}/{relative_filename}",
                filename=f"{relative_path}/{relative_filename}",
            ),
        ],
    )

    output = export_cyclonedx_json(environment, metadata=CycloneDXExportMetadata())
    document = json.loads(output)

    assert posix_path not in output
    assert windows_path not in output
    assert relative_path not in output
    for name in ("private-posix", "private-windows", "private-relative"):
        component = component_named(document, name)
        assert component_properties(component)["conda:package:filename"] == (
            f"{name}-1.0-h123_0.conda"
        )
        assert "channel=" not in component["purl"]
        assert "externalReferences" not in component


@pytest.mark.parametrize(
    "name",
    [
        "/Users/alice/private-environment",
        "C:\\Users\\alice\\private-environment",
        "../private-environment",
    ],
)
def test_local_environment_names_are_not_serialized(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = Environment(
        name=name,
        prefix=name,
        platform="linux-64",
        explicit_packages=[package_record("example")],
    )

    output = export_cyclonedx_json(environment, metadata=CycloneDXExportMetadata())
    root = json.loads(output)["metadata"]["component"]

    assert "private-environment" not in output
    assert root["name"] == "conda-environment"
    assert root["bom-ref"] == "conda-environment:conda-environment?platform=linux-64"


@pytest.mark.parametrize("epoch", ["tomorrow", "-1"])
def test_invalid_source_date_epoch_fails(
    monkeypatch: pytest.MonkeyPatch,
    epoch: str,
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", epoch)
    environment = Environment(
        platform="linux-64",
        explicit_packages=[package_record("example")],
    )

    with pytest.raises(CondaValueError, match="SOURCE_DATE_EPOCH"):
        export_cyclonedx_json(environment, metadata=CycloneDXExportMetadata())


def test_invalid_hash_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = Environment(
        platform="linux-64",
        explicit_packages=[package_record("example", sha256="not-a-sha256")],
    )

    with pytest.raises(CondaValueError, match="Invalid SHA-256 hash"):
        export_cyclonedx_json(environment, metadata=CycloneDXExportMetadata())


def test_export_requires_exact_records() -> None:
    environment = Environment(
        platform="linux-64",
        requested_packages=[MatchSpec("python")],
    )

    with pytest.raises(CondaValueError, match="requires exact package records"):
        export_cyclonedx_json(environment, metadata=CycloneDXExportMetadata())


@pytest.mark.parametrize(
    ("schema_version", "serialization"),
    [("1.5", "json"), ("1.6", "xml"), ("1.7", "yaml"), ("1.7", "JSON")],
)
def test_unsupported_serialization_fails(
    schema_version: str, serialization: str
) -> None:
    environment = Environment(
        platform="linux-64", explicit_packages=[package_record("example")]
    )

    with pytest.raises(CondaValueError, match="Unsupported CycloneDX"):
        CycloneDXExporter(
            environment,
            schema_version=schema_version,
            serialization=serialization,
            metadata=CycloneDXExportMetadata(),
        )


def test_json_versions_preserve_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = Environment(
        platform="linux-64", explicit_packages=[package_record("example")]
    )
    metadata = CycloneDXExportMetadata(
        product_name="Acme Runtime",
        product_version="2026.08",
        product_manufacturer="Acme GmbH",
        product_manufacturer_url="https://acme.example/products/runtime",
        author_name="Alice Example",
        author_email="alice@acme.example",
        author_organization="Acme Product Security",
        author_organization_url="https://acme.example/security",
    )
    current = json.loads(export_cyclonedx_json(environment, metadata=metadata))
    older = json.loads(export_cyclonedx_json_v1_6(environment, metadata=metadata))

    assert older.pop("specVersion") == "1.6"
    assert current.pop("specVersion") == "1.7"
    assert older.pop("$schema").endswith("bom-1.6.schema.json")
    assert current.pop("$schema").endswith("bom-1.7.schema.json")
    assert older == current


@pytest.mark.parametrize("requested", [False, True])
@pytest.mark.parametrize("reproducible", [False, True])
def test_xml_maps_metadata_packages_and_compositions(
    monkeypatch: pytest.MonkeyPatch, requested: bool, reproducible: bool
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "invalid" if reproducible else "0")
    environment = Environment(
        name="demo",
        prefix="/Users/alice/private-prefix",
        platform="linux-64",
        explicit_packages=[
            package_record("leaf"),
            package_record(
                "example",
                depends=("leaf", "missing"),
                sha256="A" * 64,
                md5="b" * 32,
                license_name="Legacy terms",
                url="https://user:secret@example.org/t/token/example.conda?token=secret",
            ),
        ],
        requested_packages=[MatchSpec("example")] if requested else [],
        external_packages={"pip": ["omitted==1"]},
    )
    metadata = CycloneDXExportMetadata(
        product_name="Acme & Runtime",
        product_version="2026.08",
        product_manufacturer="Acme GmbH",
        product_manufacturer_url="https://acme.example/products/runtime",
        author_name="Alice Example",
        author_email="alice@acme.example",
        author_organization="Acme Security",
        author_organization_url="https://acme.example/security",
    )

    output = export_cyclonedx_xml(
        environment, metadata=metadata, output_reproducible=reproducible
    )
    document = ElementTree.fromstring(output)
    ns = {"c": "http://cyclonedx.org/schema/bom/1.7"}
    root = document.find("c:metadata/c:component", ns)
    example = document.find("c:components/c:component[c:name='example']", ns)
    leaf = document.find("c:components/c:component[c:name='leaf']", ns)

    assert output.endswith("\n")
    assert document.tag == "{http://cyclonedx.org/schema/bom/1.7}bom"
    assert document.attrib == {"version": "1"}
    assert "private-prefix" not in output
    assert "secret" not in output
    assert "token" not in output
    assert root.findtext("c:name", namespaces=ns) == "Acme & Runtime"
    assert root.findtext("c:version", namespaces=ns) == "2026.08"
    assert root.findtext("c:manufacturer/c:name", namespaces=ns) == "Acme GmbH"
    assert root.findtext("c:manufacturer/c:url", namespaces=ns) == (
        "https://acme.example/products/runtime"
    )
    assert (
        document.findtext("c:metadata/c:manufacturer/c:name", namespaces=ns)
        == "Acme Security"
    )
    assert (
        document.findtext("c:metadata/c:authors/c:author/c:email", namespaces=ns)
        == "alice@acme.example"
    )
    timestamp = document.find("c:metadata/c:timestamp", ns)
    if reproducible:
        assert timestamp is None
        assert (
            document.findtext(
                "c:metadata/c:properties/c:property[@name='cdx:reproducible']",
                namespaces=ns,
            )
            == "true"
        )
    else:
        assert timestamp.text == "1970-01-01T00:00:00+00:00"
    assert example.findtext("c:purl", namespaces=ns) == example.attrib["bom-ref"]
    assert example.findtext("c:hashes/c:hash[@alg='SHA-256']", namespaces=ns) == (
        "a" * 64
    )
    assert example.findtext("c:hashes/c:hash[@alg='MD5']", namespaces=ns) == "b" * 32
    assert example.findtext("c:licenses/c:license/c:name", namespaces=ns) == (
        "Legacy terms"
    )
    assert (
        example.findtext(
            "c:externalReferences/c:reference[@type='distribution']/c:url",
            namespaces=ns,
        )
        == "https://example.org/example.conda"
    )
    assert (
        example.findtext(
            "c:properties/c:property[@name='conda:package:filename']", namespaces=ns
        )
        == "example-1.0-h123_0.conda"
    )
    dependencies = {
        entry.attrib["ref"]: [child.attrib["ref"] for child in entry]
        for entry in document.find("c:dependencies", ns)
    }
    assert dependencies == {
        root.attrib["bom-ref"]: [example.attrib["bom-ref"]],
        example.attrib["bom-ref"]: [leaf.attrib["bom-ref"]],
        leaf.attrib["bom-ref"]: [],
    }
    compositions = document.findall("c:compositions/c:composition", ns)
    assert len(compositions) == 2
    assert compositions[0].findtext("c:aggregate", namespaces=ns) == "incomplete"
    assert compositions[0].find("c:assemblies/c:assembly", ns).attrib == {
        "ref": root.attrib["bom-ref"]
    }
    inferred = compositions[0].find("c:dependencies/c:dependency", ns)
    if requested:
        assert inferred is None
    else:
        assert inferred.attrib == {"ref": root.attrib["bom-ref"]}
    assert compositions[1].findtext("c:aggregate", namespaces=ns) == "incomplete"
    assert compositions[1].find("c:dependencies/c:dependency", ns).attrib == {
        "ref": example.attrib["bom-ref"]
    }
    validate_cyclonedx_xml(output)
