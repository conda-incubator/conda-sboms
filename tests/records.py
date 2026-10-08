from __future__ import annotations

from conda.models.records import PackageRecord


def package_record(
    name: str,
    *,
    version: str = "1.0",
    build: str = "h123_0",
    depends: tuple[str, ...] = (),
    sha256: str | None = None,
    md5: str | None = None,
    license_name: str | None = None,
    url: str | None = None,
    channel: str = "https://conda.anaconda.org/conda-forge",
    filename: str | None = None,
) -> PackageRecord:
    filename = filename or f"{name}-{version}-{build}.conda"
    return PackageRecord(
        name=name,
        version=version,
        build=build,
        build_number=0,
        channel=channel,
        subdir="linux-64",
        fn=filename,
        depends=list(depends),
        sha256=sha256,
        md5=md5,
        license=license_name,
        size=123,
        url=url or f"https://conda.anaconda.org/conda-forge/linux-64/{filename}",
    )
