"""Base STAC API client implementation."""
from abc import ABC
from typing import List
from urllib.parse import urljoin, urlparse

import attr
from stac_fastapi.types.stac import LandingPage
from stac_fastapi.types.core import AsyncBaseCoreClient, LandingPageMixin
from stac_fastapi.types.conformance import BASE_CONFORMANCE_CLASSES
from stac_fastapi.types.requests import get_base_url


@attr.s
class BaseClient(AsyncBaseCoreClient, LandingPageMixin, ABC):
    """Base STAC client implementation."""

    settings = attr.ib(default=None)
    api_version = attr.ib(default="1.0.0")

    # Добавим метод для валидации URL
    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL to validate

        Returns:
            bool: True if valid
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except Exception:
            return False

    def landing_page(self, **kwargs) -> LandingPage:
        """
        Generate the STAC API landing page.

        This method creates the root ('/') endpoint response, providing links to the main
        functionality of the API, including search, collections, and conformance information.

        Returns:
            LandingPage: A dictionary containing API metadata and links to major endpoints.
        """

        request = kwargs.get("request")
        if not request:
            raise ValueError("Request object is required")

        base_url = get_base_url(request)
        if not self.validate_url(base_url):
            raise ValueError(f"Invalid base URL: {base_url}")

        landing_page = self._landing_page(
            base_url=base_url,
            conformance_classes=self.conformance_classes(),
            extension_schemas=[],
        )

        landing_page["links"] = [link for link in landing_page["links"] if link["rel"]]
        landing_page["id"] = "worldpop-stac-api"
        landing_page["title"] = "WorldPop STAC API"
        landing_page["description"] = (
            "Welcome to the WorldPop STAC API, a specialized platform for accessing and analyzing global population distribution and covariate data. This API utilizes the SpatioTemporal Asset Catalog (STAC) specification to provide standardized access to a range of geospatial datasets related to human population and environmental factors.\n\n"

            "Our API offers access to the following types of data:\n"
            "• Population estimates\n"
            "• Built settlement layers\n"
            "• Building footprints\n"
            "• Land cover classifications\n"
            "• Elevation and slope data\n"
            "• Climate indicators\n"
            "• Infrastructure data (e.g., roads, water bodies)\n\n"

            "These datasets are available at a consistent resolution of 3 arc seconds (approximately 100m at the equator) and use the Geographic Coordinate System WGS84 (EPSG:4326). The data covers most countries globally, with a focus on providing detailed, up-to-date information for demographic and environmental analysis.\n\n"

            "Key features of our STAC API include:\n"
            "1. Standardized Metadata: Consistent and machine-readable metadata for all datasets.\n"
            "2. Spatial Querying: Ability to search for data within specific geographic areas.\n"
            "3. Temporal Filtering: Options to retrieve data for specific years where applicable.\n"
            "4. Direct Data Access: Links to download the actual data files.\n\n"

            "This API is designed to support various use cases, including:\n"
            "• Academic research on population distribution and dynamics\n"
            "• Urban planning and infrastructure development\n"
            "• Environmental impact assessments\n"
            "• Humanitarian response planning\n\n"

            "By providing easy access to these datasets, the WorldPop STAC API aims to facilitate research and decision-making in fields related to population studies, urban development, and environmental science. We invite researchers, policymakers, and data scientists to explore our catalog and integrate these valuable datasets into their work."
        )

        landing_page["links"].append({
            "rel": "http://www.opengis.net/def/rel/ogc/1.0/queryables",
            "href": urljoin(str(request.base_url), "queryables".lstrip("/")),
            "type": "application/json",
            "title": "Queryables"
        })

        landing_page["links"].append({
            "rel": "service-desc",
            "type": "application/vnd.oai.openapi+json;version=3.0",
            "title": "OpenAPI service description",
            "href": urljoin(str(request.base_url), request.app.openapi_url.lstrip("/")),
        })

        landing_page["links"].append({
            "rel": "service-doc",
            "type": "text/html",
            "title": "OpenAPI service documentation",
            "href": urljoin(str(request.base_url), request.app.docs_url.lstrip("/")),
        })

        landing_page["links"].append({
            "rel": "conformance",
            "href": urljoin(str(request.base_url), "conformance"),
            "type": "application/json",
            "title": "Conformance Classes"
        })

        return landing_page


    def conformance_classes(self) -> List[str]:
        """
        List all conformance classes supported by this API.

        This method returns a list of URIs identifying the specifications that the
        server conforms to.

        Returns:
            List[str]: A list of conformance class URIs.
        """
        # ... existing implementation ...
        base_classes = set(BASE_CONFORMANCE_CLASSES)
        extension_classes = set()

        for extension in self.extensions:
            extension_classes.update(getattr(extension, "conformance_classes", []))

        return list(base_classes | extension_classes)


    @property
    def version(self) -> str:
        """Get API version."""
        return self.api_version

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported extensions."""
        return [ext.__class__.__name__ for ext in self.extensions]