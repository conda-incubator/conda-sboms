# Export a conda-workspaces environment

`conda workspace export` uses the same exporter plugin hook as `conda export`.
Install `conda-sboms` and `conda-workspaces` into the environment that owns the
`conda` executable before using these commands. The behavior described below
requires conda-workspaces 0.8.0 or newer.

The distinctions between generic export and the dedicated SBOM command below
were checked against conda-workspaces 0.11.1.

For a standard conda installation, activate `base` and install both plugins:

```console
conda activate base
conda install --channel conda-forge "conda-workspaces>=0.8.0" "conda-sboms>=0.3.0"
```

Every SBOM exporter requires exact package records. A declared workspace
manifest contains requirements rather than a solved package inventory, so use
either an existing `conda.lock` or an installed workspace prefix.

## Export from conda.lock

Choose one environment and one platform represented in the lockfile:

```console
conda workspace export \
  --environment default \
  --from-lockfile \
  --platform linux-64 \
  --format cyclonedx-json \
  --file default-linux-64.cdx.json
```

This path does not solve or install into the workspace prefix. Current
conda-workspaces converts lock entries through conda-lockfiles, which may
download and extract archives into conda's package cache to construct exact
package records. Network access may therefore be required.

Every locked conda package for `default` on `linux-64` becomes a component. The
SBOM exporter is single-platform, so passing multiple `--platform` values
fails. Current conda-workspaces rejects a selected lockfile environment and
platform containing pip or other external package references before
`conda-sboms` runs. Lockfile export therefore currently requires an all-conda
selection.

Generic `conda workspace export --from-lockfile` does not enrich the lockfile
records with the manifest's requested packages. The exporter connects the environment root
to inferred graph roots and records
`conda:environment:root-dependency-source` as `inferred-graph-roots`.

## Export an installed workspace prefix

Use the installed prefix when its conda history is the preferred source of
requested package roots:

```console
conda workspace export \
  --environment default \
  --from-prefix \
  --from-history \
  --format cyclonedx-json \
  --file default.cdx.json
```

`--from-history` asks conda to populate the requested package set. When that
metadata is available, the root source is `requested-packages`. Otherwise the
exporter falls back to graph-root inference.

Without `--from-lockfile` or `--from-prefix`, conda-workspaces supplies only
declared requirements. For one selected platform, `conda-sboms` rejects that
input because it does not contain exact package records. A multi-platform
workspace can fail earlier because an SBOM exporter accepts one platform
per document.

## Select an additional format

The unreleased formats are available to generic `conda workspace export`
through the same hook. Install a source build of `conda-sboms` into the
environment that owns the `conda` executable and `conda-workspaces`, then
select the format explicitly:

```console
conda workspace export \
  --environment default \
  --from-lockfile \
  --platform linux-64 \
  --format spdx-jsonld-v3.0.1 \
  --file default-linux-64.spdx.jsonld
```

Use `cyclonedx-xml-v1.7` for XML or `cyclonedx-json-v1.6` for the older JSON
schema. Input requirements, inferred lockfile roots, possible cache access,
and the all-conda lockfile restriction remain the same. The plugin does not
discover the workspace manifest or add its own workspace behavior.

## Distinguish the dedicated SBOM command

In conda-workspaces 0.11.1, `conda workspace sbom` calls the existing
CycloneDX 1.7 JSON callback directly. It does not select the additional formats
listed above. From a lockfile, it reconstructs records without fetching
archives and adds the selected environment's requested packages from the
manifest. With `--from-prefix`, it uses history and restricts export to the
host platform.

Use generic `conda workspace export` for SPDX or another CycloneDX output.
Use the dedicated command when its CycloneDX 1.7 behavior fits the task. See
the [conda-workspaces 0.11.1 SBOM guide](https://github.com/conda-incubator/conda-workspaces/blob/0.11.1/docs/how-to/sbom.md)
and [export implementation](https://github.com/conda-incubator/conda-workspaces/blob/0.11.1/conda_workspaces/export.py)
for the versioned behavior.
