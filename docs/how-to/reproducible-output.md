# Produce reproducible output

By default, the SBOM timestamp records the current time. Preserve a meaningful
timestamp with `SOURCE_DATE_EPOCH` for every format. CycloneDX can also omit
its optional timestamp through the public Python API. SPDX requires a
creation timestamp and cannot omit it.

## Preserve a stable timestamp

Choose a non-negative Unix timestamp and export the environment.

::::{tab-set}

:::{tab-item} POSIX

```console
SOURCE_DATE_EPOCH=1720000000 conda export \
  --name my-environment \
  --from-history \
  --format cyclonedx-json \
  --file my-environment.cdx.json
```

:::

:::{tab-item} PowerShell

```powershell
$env:SOURCE_DATE_EPOCH = "1720000000"
conda export `
  --name my-environment `
  --from-history `
  --format cyclonedx-json `
  --file my-environment.cdx.json
```

:::

::::

The exporter sorts components, dependency entries, dependency targets, and JSON
keys. It omits the optional random CycloneDX serial number. With the same
`Environment` input, including requested, external, and virtual packages, the
same environment name and platform, the same product and author metadata, the
same exporter and serializer versions, and the same epoch, a second export is
byte-for-byte identical.

The value must be an integer greater than or equal to zero. An invalid,
negative, or unrepresentable timestamp fails the export instead of silently
using the current time.

For the unreleased formats, run through the source development environment
and select `spdx-jsonld-v3.0.1`, `cyclonedx-xml-v1.7`, or
`cyclonedx-json-v1.6`. The same epoch rules apply. SPDX element identifiers
are derived from sanitized content including the timestamp, so an unchanged
timestamp is also needed for stable identifiers. XML uses deterministic
element ordering rather than JSON key ordering.

## Omit the CycloneDX timestamp

Clients that expose a reproducible-output option can omit time-based metadata
through the public API:

```python
from conda_sboms.cyclonedx import export_cyclonedx_json

document = export_cyclonedx_json(
    environment,
    output_reproducible=True,
)
```

Explicit reproducible mode takes precedence over `SOURCE_DATE_EPOCH`. It omits
the optional CycloneDX `metadata.timestamp` field instead of synthesizing a
timestamp and records `cdx:reproducible=true` in `metadata.properties`. Use
`SOURCE_DATE_EPOCH` when consumers require a timestamp. Stock `conda export`
continues to use `SOURCE_DATE_EPOCH` because conda's exporter hook cannot pass
format-specific options.

The same rule applies to CycloneDX XML and JSON 1.6. XML omits the timestamp
element, and JSON omits the field. Both retain the reproducibility property.

## Request reproducible SPDX output

Set the timestamp before calling the SPDX callback:

```python
import os

from conda_sboms.spdx3 import export_spdx_jsonld

os.environ["SOURCE_DATE_EPOCH"] = "1720000000"
document = export_spdx_jsonld(
    environment,
    output_reproducible=True,
)
```

This explicit mode requires a valid epoch and raises `CondaValueError` when
the variable is missing or invalid. The SPDX creation timestamp remains in
the document. Calling the callback without this option also honors a supplied
epoch, just as the CLI does.

Reproducibility does not promise identical output across different
`conda-sboms` versions. A format update may intentionally change the document.
