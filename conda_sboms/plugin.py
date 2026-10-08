from __future__ import annotations

from typing import TYPE_CHECKING

from conda.plugins import hookimpl
from conda.plugins.types import CondaEnvironmentExporter, EnvironmentFormat

if TYPE_CHECKING:
    from collections.abc import Iterable

    from conda.plugins.types import CondaSetting


@hookimpl
def conda_settings() -> Iterable[CondaSetting]:
    from .settings import CycloneDXExportMetadata

    yield from CycloneDXExportMetadata.conda_settings()


@hookimpl
def conda_environment_exporters() -> Iterable[CondaEnvironmentExporter]:
    from . import cyclonedx, spdx3

    yield CondaEnvironmentExporter(
        name=cyclonedx.FORMAT,
        aliases=cyclonedx.ALIASES,
        default_filenames=cyclonedx.DEFAULT_FILENAMES,
        export=cyclonedx.export_cyclonedx_json,
        description=cyclonedx.DESCRIPTION,
        environment_format=EnvironmentFormat.environment,
    )
    yield CondaEnvironmentExporter(
        name="cyclonedx-json-v1.6",
        aliases=(),
        default_filenames=(),
        export=cyclonedx.export_cyclonedx_json_v1_6,
        description="CycloneDX 1.6 JSON software bill of materials",
        environment_format=EnvironmentFormat.environment,
    )
    yield CondaEnvironmentExporter(
        name="cyclonedx-xml-v1.7",
        aliases=("cyclonedx-xml", "cdx-xml"),
        default_filenames=("*.cdx.xml",),
        export=cyclonedx.export_cyclonedx_xml,
        description="CycloneDX 1.7 XML software bill of materials",
        environment_format=EnvironmentFormat.environment,
    )
    yield CondaEnvironmentExporter(
        name=spdx3.FORMAT,
        aliases=spdx3.ALIASES,
        default_filenames=spdx3.DEFAULT_FILENAMES,
        export=spdx3.export_spdx_jsonld,
        description=spdx3.DESCRIPTION,
        environment_format=EnvironmentFormat.environment,
    )
