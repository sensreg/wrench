from typing import Any, ClassVar

from wrench.log import logger
from wrench.pipeline.config.pipeline_config import AbstractPipelineConfig
from wrench.pipeline.models import ComponentDefinition


class TemplatePipelineConfig(AbstractPipelineConfig):
    """This class represent a 'template' pipeline, with default nodes and edges.

    Component names are defined in the COMPONENTS class var. For each of them,
    a `_get_<component_name>` method must be implemented that returns the proper
    component. Optionally, `_get_run_params_for_<component_name>` can be implemented
    to deal with parameters required by the component's run method and predefined on
    template initialization.
    """

    COMPONENTS: ClassVar[list[str]] = []

    def _get_component(self, component_name: str) -> ComponentDefinition | None:
        method = getattr(self, f"_get_{component_name}")
        component = method()
        if component is None:
            return None
        method = getattr(self, f"_get_run_params_for_{component_name}", None)
        run_params = method() if method else {}
        component_definition = ComponentDefinition(
            name=component_name,
            component=component,
            run_params=run_params,
        )
        logger.debug(f"TEMPLATE_PIPELINE: resolved component {component_definition}")
        return component_definition

    def _get_components(self) -> list[ComponentDefinition]:
        components = []
        for component_name in self.COMPONENTS:
            comp = self._get_component(component_name)
            if comp is not None:
                components.append(comp)
        return components

    def get_run_params(self, user_input: dict[str, Any]) -> dict[str, Any]:
        return {}
