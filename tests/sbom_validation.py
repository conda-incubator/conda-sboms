from __future__ import annotations

import json
from functools import cache
from pathlib import Path

import pyshacl
from cyclonedx.schema import SchemaVersion
from cyclonedx.validation.json import JsonStrictValidator
from jsonschema import Draft7Validator, Draft202012Validator
from lxml import etree
from rdflib import RDF, Graph, Namespace
from referencing import Registry, Resource

SCHEMAS = Path(__file__).parent / "schemas"
SPDX_CONTEXT = "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
SPDX_CORE = Namespace("https://spdx.org/rdf/3.0.1/terms/Core/")


@cache
def spdx_schema() -> Draft202012Validator:
    schema = json.loads((SCHEMAS / "spdx-3.0.1" / "spdx-json-schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@cache
def spdx_ontology() -> Graph:
    return Graph().parse(SCHEMAS / "spdx-3.0.1" / "spdx-model.ttl", format="turtle")


def validate_spdx(document: dict) -> None:
    """Validate SPDX structure and semantics using only pinned local resources."""
    spdx_schema().validate(document)
    validate_spdx_semantics(document)


def validate_spdx_semantics(document: dict) -> None:
    """Check RDF constraints independently of JSON Schema validation."""
    assert document["@context"] == SPDX_CONTEXT
    expanded = document.copy()
    expanded["@context"] = json.loads(
        (SCHEMAS / "spdx-3.0.1" / "spdx-context.jsonld").read_text()
    )["@context"]
    graph = Graph().parse(data=json.dumps(expanded), format="json-ld")
    assert len(set(graph.subjects(RDF.type, SPDX_CORE.SpdxDocument))) == 1, (
        "Expected exactly one expanded SpdxDocument"
    )
    conforms, _, report = pyshacl.validate(
        graph,
        shacl_graph=spdx_ontology(),
        ont_graph=spdx_ontology(),
        inference="none",
        do_owl_imports=False,
    )
    assert conforms, f"SPDX SHACL validation failed:\n{report}"


@cache
def cyclonedx_json_schema() -> Draft7Validator:
    directory = SCHEMAS / "cyclonedx-1.7.2"
    registry = Registry()
    for filename in (
        "spdx.schema.json",
        "jsf-0.82.schema.json",
        "cryptography-defs.schema.json",
    ):
        schema = json.loads((directory / filename).read_text())
        registry = registry.with_resource(schema["$id"], Resource.from_contents(schema))
    schema = json.loads((directory / "bom-1.7.schema.json").read_text())
    Draft7Validator.check_schema(schema)
    return Draft7Validator(schema, registry=registry)


def validate_cyclonedx_json(document: dict) -> None:
    """Use the corrected 1.7 schema or the official library's bundled 1.6 schema."""
    if document["specVersion"] == "1.6":
        errors = JsonStrictValidator(SchemaVersion.V1_6).validate_str(
            json.dumps(document)
        )
        assert not errors, errors
    else:
        assert document["specVersion"] == "1.7", "Unsupported CycloneDX version"
        cyclonedx_json_schema().validate(document)


class CycloneDXSchemaResolver(etree.Resolver):
    def resolve(self, url, public_id, context):
        if url in {
            "http://cyclonedx.org/schema/spdx",
            "https://cyclonedx.org/schema/spdx",
        }:
            return self.resolve_filename(
                str(SCHEMAS / "cyclonedx-1.7.2" / "spdx.xsd"), context
            )
        raise ValueError("Unexpected external XML schema resource")


@cache
def cyclonedx_xml_schema() -> etree.XMLSchema:
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    parser.resolvers.add(CycloneDXSchemaResolver())
    schema = etree.fromstring(
        (SCHEMAS / "cyclonedx-1.7.2" / "bom-1.7.xsd").read_bytes(), parser=parser
    )
    return etree.XMLSchema(schema)


def validate_cyclonedx_xml(output: str) -> None:
    """Validate CycloneDX XML against the corrected XSD without remote imports."""
    parser = etree.XMLParser(no_network=True, resolve_entities=False)
    document = etree.fromstring(output.encode(), parser=parser)
    cyclonedx_xml_schema().assertValid(document)
