from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from conda.base.context import context
from conda.common.configuration import PrimitiveParameter
from conda.exceptions import CondaValueError
from conda.plugins.types import CondaSetting


@dataclass(frozen=True, slots=True)
class CycloneDXExportMetadata:
    """Validated product and author metadata for one SBOM export."""

    product_name: str | None = None
    product_version: str | None = None
    product_manufacturer: str | None = None
    product_manufacturer_url: str | None = None
    author_name: str | None = None
    author_email: str | None = None
    author_organization: str | None = None
    author_organization_url: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "product_name", (self.product_name or "").strip() or None
        )
        object.__setattr__(
            self, "product_version", (self.product_version or "").strip() or None
        )
        object.__setattr__(
            self,
            "product_manufacturer",
            (self.product_manufacturer or "").strip() or None,
        )
        object.__setattr__(
            self,
            "product_manufacturer_url",
            (self.product_manufacturer_url or "").strip() or None,
        )
        object.__setattr__(
            self, "author_name", (self.author_name or "").strip() or None
        )
        object.__setattr__(
            self, "author_email", (self.author_email or "").strip() or None
        )
        object.__setattr__(
            self,
            "author_organization",
            (self.author_organization or "").strip() or None,
        )
        object.__setattr__(
            self,
            "author_organization_url",
            (self.author_organization_url or "").strip() or None,
        )

        if bool(self.product_name) != bool(self.product_version):
            raise CondaValueError(
                "conda_sboms_product_name and conda_sboms_product_version must be "
                "configured together"
            )
        if self.product_manufacturer and not self.product_name:
            raise CondaValueError(
                "conda_sboms_product_manufacturer requires configured product name "
                "and version"
            )
        if self.product_manufacturer_url and not self.product_manufacturer:
            raise CondaValueError(
                "conda_sboms_product_manufacturer_url requires a configured product "
                "manufacturer"
            )
        if self.product_version and len(self.product_version) > 1024:
            raise CondaValueError(
                "conda_sboms_product_version must not exceed 1024 characters"
            )
        if self.author_email:
            if not self.author_name:
                raise CondaValueError(
                    "conda_sboms_author_email requires a configured author name"
                )
            if (
                self.author_email.count("@") != 1
                or any(character.isspace() for character in self.author_email)
                or self.author_email.startswith("@")
                or self.author_email.endswith("@")
            ):
                raise CondaValueError(
                    "conda_sboms_author_email must be a valid email address"
                )
        if self.author_organization_url and not self.author_organization:
            raise CondaValueError(
                "conda_sboms_author_organization_url requires a configured author "
                "organization"
            )
        for setting, url in (
            (
                "conda_sboms_product_manufacturer_url",
                self.product_manufacturer_url,
            ),
            (
                "conda_sboms_author_organization_url",
                self.author_organization_url,
            ),
        ):
            if not url:
                continue
            try:
                parts = urlsplit(url)
            except ValueError as error:
                raise CondaValueError(
                    f"{setting} must be an HTTP or HTTPS URL without "
                    "credentials, query, or fragment"
                ) from error
            if (
                parts.scheme.lower() not in {"http", "https"}
                or not parts.netloc
                or parts.username is not None
                or parts.password is not None
                or "?" in url
                or "#" in url
                or any(character.isspace() for character in url)
                or re.search(r"%(?![0-9A-Fa-f]{2})", url)
            ):
                raise CondaValueError(
                    f"{setting} must be an HTTP or HTTPS URL without "
                    "credentials, query, or fragment"
                )

    @classmethod
    def from_context(cls) -> CycloneDXExportMetadata:
        """Read metadata from conda's active plugin settings."""
        return cls(
            product_name=context.plugins.conda_sboms_product_name,
            product_version=context.plugins.conda_sboms_product_version,
            product_manufacturer=context.plugins.conda_sboms_product_manufacturer,
            product_manufacturer_url=(
                context.plugins.conda_sboms_product_manufacturer_url
            ),
            author_name=context.plugins.conda_sboms_author_name,
            author_email=context.plugins.conda_sboms_author_email,
            author_organization=context.plugins.conda_sboms_author_organization,
            author_organization_url=(
                context.plugins.conda_sboms_author_organization_url
            ),
        )

    @staticmethod
    def conda_settings() -> tuple[CondaSetting, ...]:
        """Declare conda's lightweight plugin settings."""
        return (
            CondaSetting(
                name="conda_sboms_product_name",
                description="Product name for the exported SBOM.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
            CondaSetting(
                name="conda_sboms_product_version",
                description="Product version for the exported SBOM.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
            CondaSetting(
                name="conda_sboms_product_manufacturer",
                description="Organization that manufactured the exported product.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
            CondaSetting(
                name="conda_sboms_product_manufacturer_url",
                description="URL for the product manufacturer.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
            CondaSetting(
                name="conda_sboms_author_name",
                description="Person who authored the exported SBOM.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
            CondaSetting(
                name="conda_sboms_author_email",
                description="Email address for the person who authored the SBOM.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
            CondaSetting(
                name="conda_sboms_author_organization",
                description="Organization that authored the exported SBOM.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
            CondaSetting(
                name="conda_sboms_author_organization_url",
                description="URL for the organization that authored the SBOM.",
                parameter=PrimitiveParameter("", element_type=str),
            ),
        )


ExportMetadata = CycloneDXExportMetadata
