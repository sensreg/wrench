from typing import Any

from pydantic import BaseModel, PrivateAttr

from wrench.pipeline.config.param_resolver import ParamConfig, ParamToResolveConfig


class AbstractConfig(BaseModel):
    """Base class for all configs.

    Provides methods to get a class from a string and resolve a parameter defined by
    a dict with a 'resolver_' key.

    Each subclass must implement a 'parse' method that returns the relevant object.
    """

    _global_data: dict[str, Any] = PrivateAttr({})
    """Additional parameter ignored by all Pydantic model_* methods."""

    def resolve_param(self, param: ParamConfig) -> Any:
        """Finds the parameter value from its definition."""
        if not isinstance(param, ParamToResolveConfig):
            # some parameters do not have to be resolved, real
            # values are already provided
            return param
        return param.resolve(self._global_data)

    def resolve_params(self, params: dict[str, ParamConfig]) -> dict[str, Any]:
        """Resolve all parameters.

        Returning dict[str, Any] because parameters can be anything (str, float, list, dict...)
        """
        return {
            param_name: self.resolve_param(param)
            for param_name, param in params.items()
        }

    def parse(self, resolved_data: dict[str, Any] | None = None) -> Any:
        raise NotImplementedError()
