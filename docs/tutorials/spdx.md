# Generate and inspect an SPDX SBOM

This tutorial exports a small conda environment as SPDX 3.0.1 JSON-LD and
inspects its inventory and dependency relationships.

:::{note}
SPDX export is unreleased. Use the
[source development environment](../how-to/install.md)
for every command below. Run commands from the repository root. Creating the
example environment requires network access to conda-forge.
:::

## Create the example environment

::::{tab-set}

:::{tab-item} POSIX

```console
pixi run --locked -e dev conda create \
  --prefix ./build/spdx-tutorial-environment \
  --channel conda-forge --yes python=3.13 requests
```

:::

:::{tab-item} PowerShell

```powershell
pixi run --locked -e dev conda create `
  --prefix ./build/spdx-tutorial-environment `
  --channel conda-forge --yes python=3.13 requests
```

:::

::::

## Export SPDX

::::{tab-set}

:::{tab-item} POSIX

```console
pixi run --locked -e dev conda export \
  --prefix ./build/spdx-tutorial-environment --from-history \
  --format spdx-jsonld-v3.0.1 \
  --file build/tutorial-environment.spdx.jsonld
```

:::

:::{tab-item} PowerShell

```powershell
pixi run --locked -e dev conda export `
  --prefix ./build/spdx-tutorial-environment --from-history `
  --format spdx-jsonld-v3.0.1 `
  --file build/tutorial-environment.spdx.jsonld
```

:::

::::

`--from-history` preserves the requested `python` and `requests` roots when
conda history supplies them. Every resolved conda package still appears in
the inventory.

## Inspect the graph

JSON-LD stores linked elements under `@graph`. Print the package inventory and
the relationship types:

::::{tab-set}

:::{tab-item} POSIX

```console
pixi run --locked -e dev python - <<'PY'
import json
from pathlib import Path

document = json.loads(
    Path("build/tutorial-environment.spdx.jsonld").read_text(encoding="utf-8")
)
elements = document["@graph"]
packages = [item for item in elements if item.get("type") == "software_Package"]
relationships = [item for item in elements if item.get("type") == "Relationship"]
print(document["@context"])
print(len(packages), "packages including the environment")
print(sorted({item["relationshipType"] for item in relationships}))
print(next(item["name"] for item in packages if item["name"] == "requests"))
PY
```

:::

:::{tab-item} PowerShell

```powershell
@'
import json
from pathlib import Path

document = json.loads(
    Path("build/tutorial-environment.spdx.jsonld").read_text(encoding="utf-8")
)
elements = document["@graph"]
packages = [item for item in elements if item.get("type") == "software_Package"]
relationships = [item for item in elements if item.get("type") == "Relationship"]
print(document["@context"])
print(len(packages), "packages including the environment")
print(sorted({item["relationshipType"] for item in relationships}))
print(next(item["name"] for item in packages if item["name"] == "requests"))
'@ | pixi run --locked -e dev python -
```

:::

::::

The context identifies SPDX 3.0.1. The inventory includes an application
package for the environment and library packages for the resolved conda
records. Its exact size depends on the solve. `contains` records inventory
membership, `dependsOn` records dependencies, and `hasDeclaredLicense`
connects packages to declared-license information.

Open the file and find the `requests` package. Its package version, PURL,
archive hashes, sanitized download location, and conda properties identify the
selected artifact. Follow a relationship's `from` and `to` identifiers to
find the linked elements.

## Validate the document

The same one-line command works in POSIX shells and PowerShell:

```console
pixi run --locked -e dev python -c "import json, pathlib; from tests.sbom_validation import validate_spdx; validate_spdx(json.loads(pathlib.Path('build/tutorial-environment.spdx.jsonld').read_text(encoding='utf-8'))); print('SPDX JSON Schema and SHACL validation passed')"
```

This uses the checkout's pinned official JSON Schema, JSON-LD context, and
SHACL model. The [validation guide](../how-to/validate.md) explains what each
check establishes.

## Export the same records in CycloneDX

Select another format without recreating the environment:

```console
pixi run --locked -e dev conda export --prefix ./build/spdx-tutorial-environment --from-history --format cyclonedx-xml-v1.7 --file build/tutorial-environment.cdx.xml
pixi run --locked -e dev conda export --prefix ./build/spdx-tutorial-environment --from-history --format cyclonedx-json-v1.6 --file build/tutorial-environment-1.6.cdx.json
```

These commands describe the same resolved conda inventory using different
schemas. Read [formats and relationships](../explanation/formats-and-relationships.md)
before comparing their fields directly.

## Clean up

Remove the disposable environment:

```console
pixi run --locked -e dev conda remove --prefix ./build/spdx-tutorial-environment --all --yes
```

Remove the three generated documents with `rm` in a POSIX shell or
`Remove-Item` in PowerShell.

## Next steps

- Supply [product and author metadata](../how-to/set-product-metadata.md).
- Set a stable creation time with [reproducible output](../how-to/reproducible-output.md).
- Look up exact fields in the [SPDX reference](../reference/spdx-jsonld.md).
