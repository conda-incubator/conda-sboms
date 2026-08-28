# Export a conda-workspaces environment

`conda workspace export` uses the same exporter plugin hook as `conda export`.
Install `conda-sboms` and `conda-workspaces` into the environment that owns the
`conda` executable before using these commands. The behavior described below
requires conda-workspaces 0.8.0 or newer.

For a standard conda installation, activate `base` and install both plugins:

```console
conda activate base
conda install --channel conda-forge "conda-workspaces>=0.8.0" "conda-sboms>=0.3.0"
```

The CycloneDX exporter requires exact package records. A declared workspace
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
CycloneDX exporter is single-platform, so passing multiple `--platform` values
fails. Current conda-workspaces rejects a selected lockfile environment and
platform containing pip or other external package references before
`conda-sboms` runs. Lockfile export therefore currently requires an all-conda
selection.

The current workspace lock model does not retain the manifest's authoritative
top-level requirements. The exporter therefore connects the environment root
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
workspace can fail earlier because the CycloneDX exporter accepts one platform
per document.
