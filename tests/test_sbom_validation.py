from __future__ import annotations

import copy
import socket
import urllib.request

import pytest
from jsonschema import ValidationError
from lxml import etree

from tests.sbom_validation import (
    validate_cyclonedx_json,
    validate_cyclonedx_xml,
    validate_spdx,
    validate_spdx_semantics,
)


@pytest.fixture
def spdx_document() -> dict:
    creation = "_:creation"
    base = "https://example.org/sbom/"
    return {
        "@context": "https://spdx.org/rdf/3.0.1/spdx-context.jsonld",
        "@graph": [
            {
                "type": "CreationInfo",
                "@id": creation,
                "specVersion": "3.0.1",
                "created": "1970-01-01T00:00:00Z",
                "createdBy": [base + "tool"],
            },
            {
                "type": "SoftwareAgent",
                "spdxId": base + "tool",
                "name": "conda-sboms",
                "creationInfo": creation,
            },
            {
                "type": "software_Package",
                "spdxId": base + "environment",
                "name": "example",
                "software_primaryPurpose": "application",
                "creationInfo": creation,
            },
            {
                "type": "software_Sbom",
                "spdxId": base + "sbom",
                "creationInfo": creation,
                "element": [base + "environment"],
                "rootElement": [base + "environment"],
            },
            {
                "type": "SpdxDocument",
                "spdxId": base + "document",
                "creationInfo": creation,
                "element": [base + "tool", base + "environment", base + "sbom"],
                "rootElement": [base + "sbom"],
            },
        ],
    }


@pytest.fixture(autouse=True)
def deny_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        pytest.fail("SBOM validation attempted network access")

    monkeypatch.setattr(urllib.request, "urlopen", fail)
    monkeypatch.setattr(socket.socket, "connect", fail)


def test_spdx_validation_is_offline_and_preserves_document(spdx_document: dict) -> None:
    original = copy.deepcopy(spdx_document)
    validate_spdx(spdx_document)
    assert spdx_document == original


def test_spdx_validation_rejects_missing_creator(spdx_document: dict) -> None:
    del spdx_document["@graph"][0]["createdBy"]
    with pytest.raises(ValidationError):
        validate_spdx(spdx_document)


def test_spdx_semantic_validation_rejects_missing_creator(spdx_document: dict) -> None:
    del spdx_document["@graph"][0]["createdBy"]
    with pytest.raises(AssertionError, match="SHACL") as error:
        validate_spdx_semantics(spdx_document)
    assert "createdBy" in str(error.value)


def test_spdx_semantic_validation_rejects_wrong_creator_type(
    spdx_document: dict,
) -> None:
    spdx_document["@graph"][0]["createdBy"] = ["https://example.org/sbom/environment"]
    with pytest.raises(AssertionError, match="SHACL"):
        validate_spdx(spdx_document)


def test_spdx_validation_rejects_empty_graph(spdx_document: dict) -> None:
    spdx_document["@graph"] = []
    with pytest.raises(AssertionError, match="SpdxDocument"):
        validate_spdx(spdx_document)


@pytest.mark.parametrize("version", ["1.6", "1.7"])
def test_cyclonedx_json_validation_is_offline(version: str) -> None:
    validate_cyclonedx_json(
        {
            "bomFormat": "CycloneDX",
            "specVersion": version,
            "version": 1,
            "components": [
                {
                    "type": "library",
                    "name": "example",
                    "licenses": [{"license": {"id": "MIT"}}],
                }
            ],
        }
    )


def test_cyclonedx_json_validation_rejects_invalid_license() -> None:
    with pytest.raises(ValidationError):
        validate_cyclonedx_json(
            {
                "bomFormat": "CycloneDX",
                "specVersion": "1.7",
                "version": 1,
                "components": [
                    {
                        "type": "library",
                        "name": "example",
                        "licenses": [{"license": {"id": "invalid"}}],
                    }
                ],
            }
        )


def test_cyclonedx_xml_validation_is_offline() -> None:
    validate_cyclonedx_xml(
        '<bom xmlns="http://cyclonedx.org/schema/bom/1.7" version="1">'
        '<components><component type="library" bom-ref="example">'
        "<name>example</name><licenses><license><id>MIT</id></license></licenses>"
        '</component></components><dependencies><dependency ref="example"/>'
        "</dependencies></bom>"
    )


def test_cyclonedx_xml_validation_rejects_invalid_document() -> None:
    with pytest.raises(etree.DocumentInvalid):
        validate_cyclonedx_xml(
            '<bom xmlns="http://cyclonedx.org/schema/bom/1.7" version="1">'
            '<components><component type="invalid"><name>example</name>'
            "</component></components></bom>"
        )
