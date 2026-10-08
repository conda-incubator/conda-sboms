from __future__ import annotations

from collections.abc import Hashable
from string import hexdigits
from typing import TYPE_CHECKING, TypeVar
from urllib.parse import urlsplit, urlunsplit

from conda.common.url import remove_auth, split_anaconda_token
from conda.exceptions import CondaValueError
from conda.models.match_spec import MatchSpec
from packageurl import PackageURL

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from conda.models.records import PackageRecord

Reference = TypeVar("Reference", bound=Hashable)


def package_identity(
    record: PackageRecord,
) -> tuple[PackageURL, dict[str, str], str | None]:
    """Preserve conda archive identity without local paths or URL credentials."""
    filename = None
    if record.fn:
        filename = str(record.fn).replace("\\", "/").rsplit("/", 1)[-1]
        filename = filename.split("?", 1)[0].split("#", 1)[0] or None
    channel = record.channel_name
    if record.channel.scheme == "file" or channel in {None, "", "<unknown>"}:
        channel = None
    qualifiers = {"build": record.build, "subdir": record.subdir}
    properties = {
        "conda:package:build": record.build,
        "conda:package:build-number": str(record.build_number),
        "conda:package:subdir": record.subdir,
    }
    if channel:
        qualifiers["channel"] = channel
        properties["conda:package:channel"] = channel
    if filename:
        properties["conda:package:filename"] = filename
        if filename.endswith(".conda"):
            qualifiers["type"] = "conda"
        elif filename.endswith(".tar.bz2"):
            qualifiers["type"] = "tar.bz2"
    size = getattr(record, "size", None)
    if size is not None:
        properties["conda:package:size"] = str(size)
    purl = PackageURL(
        type="conda",
        name=str(record.name),
        version=str(record.version),
        qualifiers=qualifiers,
    )
    url = str(record.url) if record.url else None
    sanitized_url = None
    if url:
        try:
            parts = urlsplit(url)
            windows_path = (
                len(parts.scheme) == 1
                and len(url) > 2
                and url[1] == ":"
                and url[2] in {"/", "\\"}
            )
            if parts.scheme and parts.scheme.lower() != "file" and not windows_path:
                parts = urlsplit(remove_auth(split_anaconda_token(url)[0]))
                sanitized_url = urlunsplit(
                    (parts.scheme, parts.netloc, parts.path, "", "")
                )
        except ValueError:
            pass
    return purl, properties, sanitized_url


def validated_hashes(record: PackageRecord) -> list[tuple[str, str]]:
    hashes = []
    for algorithm, value, length in (
        ("SHA-256", record.sha256, 64),
        ("MD5", record.md5, 32),
    ):
        if not value:
            continue
        if len(value) != length or any(char not in hexdigits for char in value):
            raise CondaValueError(
                f"Invalid {algorithm} hash for conda package {record.name}"
            )
        hashes.append((algorithm, value.lower()))
    return hashes


def package_dependency_graph(
    packages: Iterable[tuple[PackageRecord, Reference]],
    references_by_name: Mapping[str, Reference],
) -> tuple[dict[Reference, list[Reference]], int, set[Reference]]:
    """Map declared conda dependencies to the resolved records by name."""
    edges = {}
    missing_count = 0
    incomplete_references = set()
    for record, reference in packages:
        dependencies = set()
        for dependency in record.depends:
            name = MatchSpec(dependency).name
            target = references_by_name.get((name or "").lower())
            if target is None:
                missing_count += 1
                incomplete_references.add(reference)
            else:
                dependencies.add(target)
        edges[reference] = sorted(dependencies, key=str)
    return edges, missing_count, incomplete_references


def root_dependency_references(
    requested_packages: list[MatchSpec],
    edges: Mapping[Reference, list[Reference]],
    references_by_name: Mapping[str, Reference],
) -> list[Reference]:
    """Select requested roots or infer roots covering disconnected cycles."""
    if requested_packages:
        return sorted(
            {
                reference
                for spec in requested_packages
                if (reference := references_by_name.get((spec.name or "").lower()))
                is not None
            },
            key=str,
        )
    incoming = {target for targets in edges.values() for target in targets}
    roots = sorted(edges.keys() - incoming, key=str)
    reachable = set()
    for reference in [*roots, *sorted(edges, key=str)]:
        if reference in reachable:
            continue
        if reference not in roots:
            roots.append(reference)
        pending = [reference]
        while pending:
            dependency = pending.pop()
            if dependency in reachable:
                continue
            reachable.add(dependency)
            pending.extend(edges[dependency])
    return roots
