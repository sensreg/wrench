from typing import Sequence

from pydantic import validate_call

from wrench.components.types import Metadata
from wrench.metadatabuilder import BaseMetadataBuilder
from wrench.models import Group
from wrench.pipeline.models import Component


class MetadataBuilder(Component):
    """
    Component for creating metadata builder component from any metadata builder.

    Args:
        metadatabuilder (BaseMetadataBuilder): The metadata builder to use in the
            pipeline.
    """

    def __init__(self, metadatabuilder: BaseMetadataBuilder):
        self._metadatabuilder = metadatabuilder

    @validate_call
    async def run(self, devices: Sequence[dict], groups: Sequence[Group]) -> Metadata:
        """Run the metadata builder."""
        service_metadata = self._metadatabuilder.build_service_metadata(devices)

        group_metadata = [
            self._metadatabuilder.build_group_metadata(group) for group in groups
        ]

        return Metadata(
            service_metadata=service_metadata, group_metadata=group_metadata
        )
