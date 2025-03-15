import inspect
from abc import ABC, ABCMeta, abstractmethod
from typing import Any

from pydantic import BaseModel
from typing_extensions import get_type_hints

from .exceptions import PipelineDefinitionError


class DataModel(BaseModel):
    """Input or Output data model for Components."""

    pass


class ComponentMeta(ABCMeta):
    """Metaclass that extracts component interface from method signatures."""

    def __new__(
        meta, name: str, bases: tuple[type, ...], attrs: dict[str, Any]
    ) -> type:
        # extract input and outputs from the run method signature
        run_method = attrs.get("run")
        if run_method is not None:
            sign = inspect.signature(run_method)
            attrs["component_inputs"] = {
                param.name: {
                    "has_default": param.default != inspect.Parameter.empty,
                    "annotation": param.annotation,
                }
                for param in sign.parameters.values()
                if param.name not in ("self", "kwargs")
            }
        # extract returned fields from the run method return type hint
        return_model = get_type_hints(run_method).get("return")  # type: ignore
        if return_model is None:
            raise PipelineDefinitionError(
                f"The run method return type must be annotated in {name}"
            )  # return type must be annotated

        # type hint must be subclass of DataModel
        if not issubclass(return_model, DataModel):
            raise PipelineDefinitionError(
                f"The run method must return a subclass of DataModel in {name}"
            )

        attrs["component_outputs"] = {
            f: {
                "has_default": field.is_required(),
                "annotation": field.annotation,
            }
            for f, field in return_model.model_fields.items()
        }

        return type.__new__(meta, name, bases, attrs)


class Component(ABC, metaclass=ComponentMeta):
    """Interface that needs to be implemented by all components."""

    # these variables are filled by the metaclass
    # added here for the type checker
    # DO NOT CHANGE
    component_inputs: dict[str, dict[str, str | bool | type]]
    component_outputs: dict[str, dict[str, str | bool | type]]

    @abstractmethod
    async def run(*args: Any, **kwargs: Any) -> DataModel:
        pass
