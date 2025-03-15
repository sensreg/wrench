from typing import ClassVar, Literal

from wrench.components import Cataloger, Grouper, Harvester, MetadataBuilder
from wrench.pipeline.config.object_config import ComponentType
from wrench.pipeline.config.template_pipeline.base import TemplatePipelineConfig
from wrench.pipeline.config.types import PipelineType
from wrench.pipeline.models import ConnectionDefinition


class SensorRegistrationPipelineConfig(TemplatePipelineConfig):
    """Template configuration for sensor registration pipeline."""

    COMPONENTS: ClassVar[list[str]] = [
        "harvester",
        "grouper",
        "metadatabuilder",
        "cataloger",
    ]

    harvester: ComponentType | None = None
    grouper: ComponentType | None = None
    metadatabuilder: ComponentType | None = None
    cataloger: ComponentType | None = None

    template_: Literal[PipelineType.SENSOR_PIPELINE] = PipelineType.SENSOR_PIPELINE

    def _get_harvester(self) -> Harvester:
        return Harvester(harvester=self.get_default_harvester())

    def _get_grouper(self) -> Grouper:
        return Grouper(grouper=self.get_default_grouper())

    def _get_metadatabuilder(self) -> MetadataBuilder:
        return MetadataBuilder(metadatabuilder=self.get_default_metadatabuilder())

    def _get_cataloger(self) -> Cataloger:
        return Cataloger(cataloger=self.get_default_cataloger())

    def _get_connections(self) -> list[ConnectionDefinition]:
        connections = []
        connections.append(
            ConnectionDefinition(
                start="harvester",
                end="grouper",
                input_config={"devices": "harvester.devices"},
            )
        )
        connections.append(
            ConnectionDefinition(
                start="harvester",
                end="metadatabuilder",
                input_config={"devices": "harvester.devices"},
            )
        )
        connections.append(
            ConnectionDefinition(
                start="grouper",
                end="metadatabuilder",
                input_config={"groups": "grouper.groups"},
            )
        )
        connections.append(
            ConnectionDefinition(
                start="metadatabuilder",
                end="cataloger",
                input_config={
                    "service_metadata": "metadatabuilder.service_metadata",
                    "group_metadata": "metadatabuilder.group_metadata",
                },
            )
        )
        return connections
