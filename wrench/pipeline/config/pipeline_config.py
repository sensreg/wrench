import logging
from typing import Any, ClassVar, Literal, Optional, Union

from pydantic import field_validator

from wrench.cataloger import BaseCataloger
from wrench.grouper import BaseGrouper
from wrench.harvester import BaseHarvester
from wrench.metadatabuilder import BaseMetadataBuilder
from wrench.pipeline.models import (
    ComponentDefinition,
    ConnectionDefinition,
    PipelineDefinition,
)

from .base import AbstractConfig
from .object_config import (
    CatalogerType,
    ComponentType,
    GrouperType,
    HarvesterType,
    MetadataBuilderType,
)
from .param_resolver import (
    ParamConfig,
)
from .types import PipelineType

logger = logging.getLogger(__name__)


class AbstractPipelineConfig(AbstractConfig):
    """
    This class defines the fields possibly used by all pipelines.

    Harvester, Grouper, Cataloger. can be provided by user as a single item or a dict of items.
    Validators deal with type conversion so that the field in all instances is a dict of items.
    """

    harvester_config: dict[str, HarvesterType] = {}
    grouper_config: dict[str, GrouperType] = {}
    metadatabuilder_config: dict[str, MetadataBuilderType] = {}
    cataloger_config: dict[str, CatalogerType] = {}
    # extra parameters values that can be used in different places of the config file
    extras: dict[str, ParamConfig] = {}

    DEFAULT_NAME: ClassVar[str] = "default"
    """Name of the default item in dict
    """

    @field_validator("harvester_config", mode="before")
    @classmethod
    def validate_harvesters(
        cls, harvesters: Union[HarvesterType, dict[str, Any]]
    ) -> dict[str, Any]:
        if not isinstance(harvesters, dict) or "class_" in harvesters:
            return {cls.DEFAULT_NAME: harvesters}
        return harvesters

    @field_validator("grouper_config", mode="before")
    @classmethod
    def validate_groupers(
        cls, groupers: Union[GrouperType, dict[str, Any]]
    ) -> dict[str, Any]:
        if not isinstance(groupers, dict) or "class_" in groupers:
            return {cls.DEFAULT_NAME: groupers}
        return groupers

    @field_validator("metadatabuilder_config", mode="before")
    @classmethod
    def validate_metadatabuilder(
        cls, metadatabuilder: Union[MetadataBuilderType, dict[str, Any]]
    ) -> dict[str, Any]:
        if not isinstance(metadatabuilder, dict) or "class_" in metadatabuilder:
            return {cls.DEFAULT_NAME: metadatabuilder}
        return metadatabuilder

    @field_validator("cataloger_config", mode="before")
    @classmethod
    def validate_cataloger(
        cls, cataloger: Union[CatalogerType, dict[str, Any]]
    ) -> dict[str, Any]:
        if not isinstance(cataloger, dict) or "class_" in cataloger:
            return {cls.DEFAULT_NAME: cataloger}
        return cataloger

    def _resolve_component_definition(
        self, name: str, config: ComponentType
    ) -> ComponentDefinition:
        component = config.parse(self._global_data)
        if hasattr(config.root, "run_params_"):
            component_run_params = self.resolve_params(config.root.run_params_)
        else:
            component_run_params = {}
        component_def = ComponentDefinition(
            name=name,
            component=component,
            run_params=component_run_params,
        )
        logger.debug(f"PIPELINE_CONFIG: resolved component {component_def}")
        return component_def

    def _parse_global_data(self) -> dict[str, Any]:
        """
        Global data contains data that can be referenced in other parts of the config.

        Typically, neo4j drivers, LLMs and embedders can be referenced in component
         input parameters.
        """
        # 'extras' parameters can be referenced in other configs,
        # that's why they are parsed before the others
        # e.g., an API key used for both LLM and Embedder can be stored only
        # once in extras.
        extra_data = {
            "extras": self.resolve_params(self.extras),
        }
        logger.debug(f"PIPELINE_CONFIG: resolved 'extras': {extra_data}")
        harvesters: dict[str, BaseHarvester] = {
            harvester_name: harvester_config.parse(extra_data)
            for harvester_name, harvester_config in self.harvester_config.items()
        }
        groupers: dict[str, BaseGrouper] = {
            grouper_name: grouper_config.parse(extra_data)
            for grouper_name, grouper_config in self.grouper_config.items()
        }
        metadatabuilders: dict[str, BaseMetadataBuilder] = {
            metadatabuilder_name: metadatabuilder_config.parse(extra_data)
            for metadatabuilder_name, metadatabuilder_config in self.metadatabuilder_config.items()
        }
        catalogers: dict[str, BaseCataloger] = {
            cataloger_name: cataloger_config.parse(extra_data)
            for cataloger_name, cataloger_config in self.cataloger_config.items()
        }
        global_data = {
            **extra_data,
            "harvester_config": harvesters,
            "grouper_config": groupers,
            "metadatabuilder_config": metadatabuilders,
            "cataloger_config": catalogers,
        }
        logger.debug(f"PIPELINE_CONFIG: resolved globals: {global_data}")
        return global_data

    def _get_components(self) -> list[ComponentDefinition]:
        return []

    def _get_connections(self) -> list[ConnectionDefinition]:
        return []

    def parse(
        self, resolved_data: Optional[dict[str, Any]] = None
    ) -> PipelineDefinition:
        """
        Parse the full config and returns a PipelineDefinition object.

        Contains instantiated components and a list of connections.
        """
        self._global_data = self._parse_global_data()
        return PipelineDefinition(
            components=self._get_components(),
            connections=self._get_connections(),
        )

    def get_run_params(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return user_input

    async def close(self) -> None:
        drivers = self._global_data.get("neo4j_config", {})
        for driver_name in drivers:
            driver = drivers[driver_name]
            logger.debug(f"PIPELINE_CONFIG: closing driver {driver_name}: {driver}")
            driver.close()

    def get_harvester_by_name(self, name: str) -> BaseHarvester:
        harvesters: dict[str, BaseHarvester] = self._global_data.get(
            "harvester_config", {}
        )
        return harvesters[name]

    def get_default_harvester(self) -> BaseHarvester:
        return self.get_harvester_by_name(self.DEFAULT_NAME)

    def get_grouper_by_name(self, name: str) -> BaseGrouper:
        llms: dict[str, BaseGrouper] = self._global_data.get("grouper_config", {})
        return llms[name]

    def get_default_grouper(self) -> BaseGrouper:
        return self.get_grouper_by_name(self.DEFAULT_NAME)

    def get_metadatabuilder_by_name(self, name: str) -> BaseMetadataBuilder:
        print(self._global_data)
        metadatabuilder: dict[str, BaseMetadataBuilder] = self._global_data.get(
            "metadatabuilder_config", {}
        )
        return metadatabuilder[name]

    def get_default_metadatabuilder(self) -> BaseMetadataBuilder:
        return self.get_metadatabuilder_by_name(self.DEFAULT_NAME)

    def get_cataloger_by_name(self, name: str) -> BaseCataloger:
        cataloger: dict[str, BaseCataloger] = self._global_data.get(
            "cataloger_config", {}
        )
        return cataloger[name]

    def get_default_cataloger(self) -> BaseCataloger:
        return self.get_cataloger_by_name(self.DEFAULT_NAME)


class PipelineConfig(AbstractPipelineConfig):
    """
    Configuration class for raw pipelines.

    Config must contain all components and connections.
    """

    component_config: dict[str, ComponentType]
    connection_config: list[ConnectionDefinition]
    template_: Literal[PipelineType.NONE] = PipelineType.NONE

    def _get_connections(self) -> list[ConnectionDefinition]:
        return self.connection_config

    def _get_components(self) -> list[ComponentDefinition]:
        return [
            self._resolve_component_definition(name, component_config)
            for name, component_config in self.component_config.items()
        ]
