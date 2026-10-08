from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING
from xml.etree import ElementTree

import pytest
from conda.models.environment import Environment
from conda.models.records import PackageRecord
from conda.plugins.types import EnvironmentFormat

from conda_sboms import cyclonedx, spdx3
from conda_sboms.plugin import conda_environment_exporters
from conda_sboms.settings import ExportMetadata

from .sbom_validation import (
    validate_cyclonedx_json,
    validate_cyclonedx_xml,
    validate_spdx,
)

if TYPE_CHECKING:
    from pathlib import Path


@pytest.fixture
def export_environment(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    environment = os.environ.copy()
    environment.update(
        {
            "CONDA_NO_PLUGINS": "false",
            "CONDA_PLUGINS_CONDA_SBOMS_PRODUCT_NAME": "  Acme Runtime  ",
            "CONDA_PLUGINS_CONDA_SBOMS_PRODUCT_VERSION": "2026.08",
            "CONDA_PLUGINS_CONDA_SBOMS_PRODUCT_MANUFACTURER": "Acme GmbH",
            "CONDA_PLUGINS_CONDA_SBOMS_PRODUCT_MANUFACTURER_URL": (
                "https://acme.example/products/runtime"
            ),
            "CONDA_PLUGINS_CONDA_SBOMS_AUTHOR_NAME": "Alice Example",
            "CONDA_PLUGINS_CONDA_SBOMS_AUTHOR_EMAIL": "alice@acme.example",
            "CONDA_PLUGINS_CONDA_SBOMS_AUTHOR_ORGANIZATION": "Acme Product Security",
            "CONDA_PLUGINS_CONDA_SBOMS_AUTHOR_ORGANIZATION_URL": (
                "https://acme.example/security"
            ),
        }
    )
    return environment


def test_plugin_registration() -> None:
    exporters = list(conda_environment_exporters())
    assert len(exporters) == 4
    by_name = {exporter.name: exporter for exporter in exporters}
    for name, aliases, filenames, callback in (
        (
            "cyclonedx-json-v1.7",
            ("cyclonedx-json", "cyclonedx", "cdx-json"),
            ("*.cdx.json",),
            cyclonedx.export_cyclonedx_json,
        ),
        ("cyclonedx-json-v1.6", (), (), cyclonedx.export_cyclonedx_json_v1_6),
        (
            "cyclonedx-xml-v1.7",
            ("cyclonedx-xml", "cdx-xml"),
            ("*.cdx.xml",),
            cyclonedx.export_cyclonedx_xml,
        ),
        (
            "spdx-jsonld-v3.0.1",
            ("spdx-jsonld",),
            ("*.spdx3.json", "*.spdx.jsonld"),
            spdx3.export_spdx_jsonld,
        ),
    ):
        exporter = by_name[name]
        assert exporter.aliases == aliases
        assert exporter.default_filenames == filenames
        assert exporter.environment_format is EnvironmentFormat.environment
        assert exporter.export is callback


def test_plugin_import_keeps_formats_lazy() -> None:
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys\n"
                "import conda_sboms.plugin\n"
                "assert 'conda_sboms.cyclonedx' not in sys.modules\n"
                "assert 'conda_sboms.spdx3' not in sys.modules\n"
                "assert 'cyclonedx' not in sys.modules\n"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    "exporter",
    [
        cyclonedx.export_cyclonedx_json,
        cyclonedx.export_cyclonedx_json_v1_6,
        cyclonedx.export_cyclonedx_xml,
        spdx3.export_spdx_jsonld,
    ],
)
def test_export_accepts_records_without_optional_archive_metadata(
    exporter, monkeypatch
):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    record = PackageRecord(
        name="leaf", version="1", build="0", build_number=0, subdir="linux-64"
    )
    output = exporter(
        Environment(platform="linux-64", explicit_packages=[record]),
        metadata=ExportMetadata(),
    )
    assert "conda:package:size" not in output
    if exporter is cyclonedx.export_cyclonedx_xml:
        validate_cyclonedx_xml(output)
    elif exporter is spdx3.export_spdx_jsonld:
        validate_spdx(json.loads(output))
    else:
        validate_cyclonedx_json(json.loads(output))


@pytest.mark.parametrize(
    ("format_name", "version", "serialization"),
    [
        ("cyclonedx-json-v1.7", "1.7", "json"),
        ("cyclonedx-json", "1.7", "json"),
        ("cyclonedx", "1.7", "json"),
        ("cdx-json", "1.7", "json"),
        ("cyclonedx-json-v1.6", "1.6", "json"),
        ("cyclonedx-xml-v1.7", "1.7", "xml"),
        ("cyclonedx-xml", "1.7", "xml"),
        ("cdx-xml", "1.7", "xml"),
        ("spdx-jsonld-v3.0.1", "3.0.1", "jsonld"),
        ("spdx-jsonld", "3.0.1", "jsonld"),
    ],
)
def test_conda_discovers_and_runs_exporter(
    export_environment: dict[str, str],
    format_name: str,
    version: str,
    serialization: str,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "conda",
            "export",
            "--prefix",
            sys.prefix,
            "--format",
            format_name,
        ],
        check=True,
        capture_output=True,
        text=True,
        env=export_environment,
    )
    output = completed.stdout
    assert output.endswith("\n")
    if serialization == "xml":
        document = ElementTree.fromstring(output)
        ns = {"c": "http://cyclonedx.org/schema/bom/1.7"}
        assert document.findtext("c:metadata/c:component/c:name", namespaces=ns) == (
            "Acme Runtime"
        )
        assert document.findtext("c:metadata/c:component/c:version", namespaces=ns) == (
            "2026.08"
        )
        validate_cyclonedx_xml(output)
    elif serialization == "jsonld":
        document = json.loads(output)
        assert document["@context"] == (
            "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
        )
        root = next(
            element
            for element in document["@graph"]
            if element.get("type") == "software_Package"
            and element.get("name") == "Acme Runtime"
        )
        assert root["software_packageVersion"] == "2026.08"
        if format_name == "spdx-jsonld-v3.0.1":
            validate_spdx(document)
    else:
        document = json.loads(output)
        assert document["specVersion"] == version
        assert document["metadata"]["authors"] == [
            {"email": "alice@acme.example", "name": "Alice Example"}
        ]
        assert document["metadata"]["manufacturer"] == {
            "name": "Acme Product Security",
            "url": ["https://acme.example/security"],
        }
        root = document["metadata"]["component"]
        assert root["name"] == "Acme Runtime"
        assert root["version"] == "2026.08"
        assert root["manufacturer"] == {
            "name": "Acme GmbH",
            "url": ["https://acme.example/products/runtime"],
        }
        assert root["bom-ref"].startswith(
            "conda-environment:Acme%20Runtime@2026.08?platform="
        )
        assert document["metadata"]["tools"]["components"][0]["name"] == "conda-sboms"
        validate_cyclonedx_json(document)


@pytest.mark.parametrize(
    "filename", ["demo.cdx.json", "demo.cdx.xml", "demo.spdx3.json", "demo.spdx.jsonld"]
)
def test_conda_detects_exporter_by_filename(
    export_environment: dict[str, str], tmp_path: Path, filename: str
) -> None:
    path = tmp_path / filename
    subprocess.run(
        [
            sys.executable,
            "-m",
            "conda",
            "export",
            "--prefix",
            sys.prefix,
            "--file",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=export_environment,
    )
    output = path.read_text()
    if filename.endswith(".xml"):
        validate_cyclonedx_xml(output)
    elif filename.endswith(".cdx.json"):
        document = json.loads(output)
        assert document["specVersion"] == "1.7"
        validate_cyclonedx_json(document)
    else:
        assert json.loads(output)["@context"] == (
            "https://spdx.org/rdf/3.0.1/spdx-context.jsonld"
        )
