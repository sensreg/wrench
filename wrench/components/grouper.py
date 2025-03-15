from typing import Sequence

from pydantic import validate_call

from wrench.components.types import Groups
from wrench.grouper import BaseGrouper
from wrench.pipeline.component import Component


class Grouper(Component):
    """
    Component for creating grouper component from any grouper.

    Args:
        grouper (BaseGrouperr): The grouper to use in the pipeline.
    """

    def __init__(self, grouper: BaseGrouper):
        self._grouper = grouper

    @validate_call
    async def run(self, devices: Sequence[dict]) -> Groups:
        """Run the grouper and group Items."""
        groups = self._grouper.group_items(devices)
        return Groups(groups=groups)
