from typing import Sequence

from pydantic import validate_call

from wrench.cataloger import BaseCataloger
from wrench.models import CommonMetadata
from wrench.pipeline.models import Component, DataModel


class CatalogerStatus(DataModel):
    success: bool = False
    groups: list[str]


class Cataloger(Component):
    """
    Component for creating cataloger component from any cataloger.

    Args:
        cataloger (BaseCataloger): The cataloger to use in the pipeline.
    """

    def __init__(self, cataloger: BaseCataloger):
        self._cataloger = cataloger

    @validate_call
    async def run(
        self, service_metadata: CommonMetadata, group_metadata: Sequence[CommonMetadata]
    ) -> CatalogerStatus:
        """Run the cataloger and register metadata."""
        try:
            # Directly get items from the harvester
            self._cataloger.register(service=service_metadata, groups=group_metadata)
            return CatalogerStatus(
                success=True, groups=[group.identifier for group in group_metadata]
            )
        except Exception:
            # Re-raise to ensure pipeline knows this component failed
            raise
