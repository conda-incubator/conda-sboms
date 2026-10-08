from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
from dataclasses import replace
from datetime import datetime, timezone

import pytest
from conda.exceptions import CondaValueError
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec

from conda_sboms.settings import ExportMetadata
from conda_sboms.spdx3 import export_spdx_jsonld
from tests.records import package_record
from tests.sbom_validation import validate_spdx


@pytest.fixture(autouse=True)
def deny_network(monkeypatch) -> None:
    def fail(*args, **kwargs):
        pytest.fail("SPDX export or validation attempted network access")

    monkeypatch.setattr(socket.socket, "connect", fail)


def named(document: dict, name: str) -> dict:
    return next(node for node in document["@graph"] if node.get("name") == name)


def properties(node: dict) -> dict[str, str]:
    return {
        entry["extension_cdxPropName"]: entry["extension_cdxPropValue"]
        for extension in node.get("extension", [])
        for entry in extension["extension_cdxProperty"]
    }


def relationship(document: dict, source: dict, kind: str) -> dict:
    return next(
        node
        for node in document["@graph"]
        if node.get("type") == "Relationship"
        and node["from"] == source["spdxId"]
        and node["relationshipType"] == kind
    )


def test_export_preserves_conda_inventory_and_validates_offline(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = Environment(
        name="demo",
        platform="linux-64",
        explicit_packages=[
            package_record(
                "python",
                version="3.13",
                depends=("openssl >=3", "__linux"),
                sha256="A" * 64,
                md5="B" * 32,
                license_name="MIT OR Apache-2.0",
                url="https://user:secret@repo.example/t/token/linux-64/python.conda?signature=secret#secret",
            ),
            package_record("openssl", license_name="BSD-like terms"),
        ],
        requested_packages=[MatchSpec("python")],
        external_packages={"pip": ["other==1"]},
    )
    output = export_spdx_jsonld(environment, metadata=ExportMetadata())
    document = json.loads(output)
    validate_spdx(document)
    assert output.endswith("\n")
    assert document["@context"] == "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
    root = named(document, "demo")
    python = named(document, "python")
    openssl = named(document, "openssl")
    assert root["software_primaryPurpose"] == "application"
    assert python["software_primaryPurpose"] == "library"
    assert python["software_packageVersion"] == "3.13"
    assert (
        python["software_packageUrl"] == "pkg:conda/python@3.13?build=h123_0"
        "&channel=conda-forge&subdir=linux-64&type=conda"
    )
    assert (
        python["software_downloadLocation"]
        == "https://repo.example/linux-64/python.conda"
    )
    assert {
        item["algorithm"]: item["hashValue"] for item in python["verifiedUsing"]
    } == {"sha256": "a" * 64, "md5": "b" * 32}
    assert properties(python)["conda:package:build"] == "h123_0"
    assert properties(python)["conda:package:filename"] == "python-3.13-h123_0.conda"
    assert properties(root)["conda:environment:external-packages-omitted"] == "1"
    assert properties(root)["conda:environment:dependency-edges-omitted"] == "1"
    assert (
        properties(root)["conda:environment:root-dependency-source"]
        == "requested-packages"
    )
    assert relationship(document, root, "contains")["completeness"] == "incomplete"
    assert set(relationship(document, root, "contains")["to"]) == {
        python["spdxId"],
        openssl["spdxId"],
    }
    assert relationship(document, root, "dependsOn")["to"] == [python["spdxId"]]
    assert relationship(document, python, "dependsOn")["completeness"] == "incomplete"
    assert relationship(document, python, "dependsOn")["to"] == [openssl["spdxId"]]
    assert relationship(document, openssl, "dependsOn")["to"] == [
        "https://spdx.org/rdf/3.0.1/terms/Core/NoAssertionElement"
    ]
    assert properties(openssl)["conda:package:license"] == "BSD-like terms"
    assert relationship(document, openssl, "hasDeclaredLicense")["to"] == [
        "https://spdx.org/rdf/3.0.1/terms/ExpandedLicensing/NoAssertionLicense"
    ]
    declared_license = relationship(document, python, "hasDeclaredLicense")["to"][0]
    assert (
        next(
            node
            for node in document["@graph"]
            if node.get("spdxId") == declared_license
        )["simplelicensing_licenseExpression"]
        == "MIT OR Apache-2.0"
    )
    assert "secret" not in output
    creation = next(
        node for node in document["@graph"] if node["type"] == "CreationInfo"
    )
    assert creation["created"] == "1970-01-01T00:00:00Z"
    for node in document["@graph"]:
        if node["type"] != "CreationInfo":
            assert node["creationInfo"] == creation["@id"]


def test_spdx_metadata_and_content_identity(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "123")
    environment = Environment(
        name="demo", platform="linux-64", explicit_packages=[package_record("leaf")]
    )
    metadata = ExportMetadata(
        product_name="App",
        product_version="2",
        product_manufacturer="Maker",
        product_manufacturer_url="https://maker.example",
        author_name="Author",
        author_email="author@example.org",
        author_organization="Team",
        author_organization_url="https://team.example",
    )
    document = json.loads(export_spdx_jsonld(environment, metadata=metadata))
    validate_spdx(document)
    root = named(document, "App")
    assert root["software_packageVersion"] == "2"
    assert root["originatedBy"] == [named(document, "Maker")["spdxId"]]
    assert named(document, "Author")["externalIdentifier"] == [
        {
            "type": "ExternalIdentifier",
            "externalIdentifierType": "email",
            "identifier": "author@example.org",
        }
    ]
    creation = next(
        node for node in document["@graph"] if node["type"] == "CreationInfo"
    )
    assert {
        named(document, "Author")["spdxId"],
        named(document, "Team")["spdxId"],
    } <= set(creation["createdBy"])
    changed = json.loads(
        export_spdx_jsonld(environment, metadata=replace(metadata, product_version="3"))
    )
    assert named(changed, "App")["spdxId"] != root["spdxId"]


def test_spdx_inferred_roots_cover_disconnected_cycle(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    records = [
        package_record("root", depends=("leaf",)),
        package_record("leaf"),
        package_record("cycle-a", depends=("cycle-b",)),
        package_record("cycle-b", depends=("cycle-a",)),
    ]
    environment = Environment(
        name="demo", platform="linux-64", explicit_packages=records
    )
    output = export_spdx_jsonld(environment, metadata=ExportMetadata())
    document = json.loads(output)
    root = named(document, "demo")
    assert set(relationship(document, root, "dependsOn")["to"]) == {
        named(document, "root")["spdxId"],
        named(document, "cycle-a")["spdxId"],
    }
    assert relationship(document, root, "dependsOn")["completeness"] == "noAssertion"
    reordered = Environment(
        name="demo", platform="linux-64", explicit_packages=list(reversed(records))
    )
    assert output == export_spdx_jsonld(reordered, metadata=ExportMetadata())


@pytest.mark.parametrize("epoch", [None, "tomorrow", "-1", "9999999999999999999999"])
def test_reproducible_spdx_requires_valid_epoch(monkeypatch, epoch) -> None:
    if epoch is None:
        monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    else:
        monkeypatch.setenv("SOURCE_DATE_EPOCH", epoch)
    environment = Environment(
        platform="linux-64", explicit_packages=[package_record("leaf")]
    )
    with pytest.raises(CondaValueError, match="SOURCE_DATE_EPOCH"):
        export_spdx_jsonld(
            environment, metadata=ExportMetadata(), output_reproducible=True
        )


@pytest.mark.parametrize(
    "algorithm,value",
    [("sha256", "x" * 64), ("sha256", "a" * 63), ("md5", "y" * 32), ("md5", "a" * 31)],
)
def test_spdx_rejects_invalid_archive_hashes(algorithm, value) -> None:
    record = package_record("leaf", **{algorithm: value})
    with pytest.raises(CondaValueError, match="Invalid .* hash"):
        export_spdx_jsonld(
            Environment(platform="linux-64", explicit_packages=[record]),
            metadata=ExportMetadata(),
        )


def test_spdx_requires_resolved_records() -> None:
    with pytest.raises(CondaValueError, match="requires exact package records"):
        export_spdx_jsonld(Environment(platform="linux-64"), metadata=ExportMetadata())


@pytest.mark.parametrize(
    "license_name",
    [None, "", "LicenseRef-unknown", "BSD-like terms", "MIT AND", "MIT OR", "MIT WITH"],
)
def test_spdx_unknown_license_is_not_invented(license_name, monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = Environment(
        platform="linux-64",
        explicit_packages=[package_record("leaf", license_name=license_name)],
    )
    document = json.loads(export_spdx_jsonld(environment, metadata=ExportMetadata()))
    validate_spdx(document)
    package = named(document, "leaf")
    relation = relationship(document, package, "hasDeclaredLicense")
    assert relation["to"] == [
        "https://spdx.org/rdf/3.0.1/terms/ExpandedLicensing/NoAssertionLicense"
    ]
    if license_name:
        assert properties(package)["conda:package:license"] == license_name
        assert "not a validated SPDX expression" in relation["comment"]
    assert not any(
        node["type"] == "expandedlicensing_CustomLicense" for node in document["@graph"]
    )


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("mit", "MIT"),
        ("MIT Or Apache-2.0", "MIT OR Apache-2.0"),
        ("GPL-2.0+", "GPL-2.0-or-later"),
    ],
)
def test_spdx_license_expression_uses_canonical_identifiers(raw, expected, monkeypatch):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = Environment(
        platform="linux-64",
        explicit_packages=[package_record("leaf", license_name=raw)],
    )
    document = json.loads(export_spdx_jsonld(environment, metadata=ExportMetadata()))
    target = relationship(document, named(document, "leaf"), "hasDeclaredLicense")[
        "to"
    ][0]
    expression = next(
        node for node in document["@graph"] if node.get("spdxId") == target
    )
    assert expression["simplelicensing_licenseExpression"] == expected


def test_spdx_local_paths_and_credentials_do_not_affect_identity(monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")

    def render(secret):
        return export_spdx_jsonld(
            Environment(
                name=f"/private/{secret}/environment",
                platform="linux-64",
                explicit_packages=[
                    package_record(
                        "leaf",
                        channel=f"file:///private/{secret}",
                        url=f"file:///private/{secret}/leaf.conda",
                    )
                ],
            ),
            metadata=ExportMetadata(),
            output_reproducible=True,
        )

    output = render("secret-one")
    assert output == render("secret-two")
    document = json.loads(output)
    package = named(document, "leaf")
    assert "software_downloadLocation" not in package
    assert "channel=" not in package["software_packageUrl"]
    assert "private" not in output
    assert named(document, "conda-environment")


def test_spdx_normal_export_uses_current_utc(monkeypatch) -> None:
    monkeypatch.delenv("SOURCE_DATE_EPOCH", raising=False)
    before = datetime.now(timezone.utc).replace(microsecond=0)
    document = json.loads(
        export_spdx_jsonld(
            Environment(
                platform="linux-64", explicit_packages=[package_record("leaf")]
            ),
            metadata=ExportMetadata(),
        )
    )
    after = datetime.now(timezone.utc)
    created = next(
        node["created"] for node in document["@graph"] if node["type"] == "CreationInfo"
    )
    assert (
        before
        <= datetime.strptime(created, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        <= after
    )


def test_spdx_determinism_across_processes_and_input_order() -> None:
    script = """
import os
from conda.models.environment import Environment
from conda.models.match_spec import MatchSpec
from conda_sboms.settings import ExportMetadata
from conda_sboms.spdx3 import export_spdx_jsonld
from tests.records import package_record
order = int(os.environ['PYTHONHASHSEED']) % 2
records = [package_record('root', depends=tuple({'leaf', 'other'})),
           package_record('leaf'), package_record('other')]
if order:
    records.reverse()
environment = Environment(platform='linux-64', explicit_packages=records,
    requested_packages=[MatchSpec(name) for name in {'root', 'other'}])
print(export_spdx_jsonld(environment, metadata=ExportMetadata(),
    output_reproducible=True), end='')
"""
    outputs = [
        subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "SOURCE_DATE_EPOCH": "0", "PYTHONHASHSEED": str(seed)},
        ).stdout
        for seed in (1, 2)
    ]
    assert outputs[0] == outputs[1]
    document = json.loads(outputs[0])
    identifiers = [node["spdxId"] for node in document["@graph"] if "spdxId" in node]
    assert len(identifiers) == len(set(identifiers))
    validate_spdx(document)


@pytest.mark.parametrize(
    "changed",
    [
        dict(license_name="MIT"),
        dict(sha256="a" * 64),
        dict(depends=("missing",)),
        dict(version="2"),
    ],
)
def test_spdx_content_changes_get_distinct_document_ids(changed, monkeypatch) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")

    def document_id(record):
        document = json.loads(
            export_spdx_jsonld(
                Environment(platform="linux-64", explicit_packages=[record]),
                metadata=ExportMetadata(),
            )
        )
        return next(
            node["spdxId"]
            for node in document["@graph"]
            if node["type"] == "SpdxDocument"
        )

    assert document_id(package_record("leaf")) != document_id(
        package_record("leaf", **changed)
    )
