from pydantic import validate_call

from wrench.components.types import Items
from wrench.harvester import BaseHarvester
from wrench.pipeline.models import Component


class Harvester(Component):
    """
    Component for creating harvester component from any harvester.

    Args:
        harvester (BaseHarvester): The harvester to use in the pipeline.
    """

    def __init__(self, harvester: BaseHarvester):
        self._harvester = harvester

    @validate_call
    async def run(self) -> Items:
        """Run the harvester and extract items."""
        # Directly get items from the harvester
        devices = self._harvester.return_items()
        return Items(devices=devices)
