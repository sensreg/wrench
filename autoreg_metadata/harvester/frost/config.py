from pydantic import BaseModel, Field


class PaginationConfig(BaseModel):
    """Configuration for pagination behavior"""

    page_delay: float = Field(
        default=0.1, description="Delay between pagination requests in seconds"
    )
    timeout: int = Field(default=60, description="Request timeout in seconds")
    batch_size: int = Field(
        default=100, description="Number of items per page")


class TranslatorConfig(BaseModel):
    """Configuration for translation service"""

    url: str = Field(description="Base URL for the translation service")
    source_lang: str | None = Field(
        default=None, description="Source language code")


class FrostConfig(BaseModel):
    """Main configuration for FROST harvester"""

    base_url: str = Field(description="Base URL for the FROST server")

    identifier: str = Field(
        description="Identifier for registering into backend, must be lowercase and separated by underscores")

    title: str = Field(
        description="The title which should be used for entry in the catalog"
    )

    description: str = Field(
        description="The description which should be used for entry in the catalog"
    )

    translator: TranslatorConfig | None = Field(
        default=None, description="Translation service configuration"
    )
    pagination: PaginationConfig = Field(
        default_factory=PaginationConfig, description="Pagination settings"
    )
    default_limit: int = Field(
        default=-1, description="Default limit for fetching items (-1 for no limit)"
    )
