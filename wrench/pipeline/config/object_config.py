from __future__ import annotations

import importlib
from typing import (
    Any,
    ClassVar,
    Generic,
    Optional,
    TypeVar,
    Union,
    cast,
)

from pydantic import (
    ConfigDict,
    Field,
    RootModel,
    field_validator,
)

from wrench.cataloger import BaseCataloger
from wrench.grouper import BaseGrouper
from wrench.harvester import BaseHarvester
from wrench.log import logger
from wrench.metadatabuilder import BaseMetadataBuilder
from wrench.pipeline.component import Component
from wrench.pipeline.config.base import AbstractConfig
from wrench.pipeline.config.param_resolver import (
    ParamConfig,
)

T = TypeVar("T")
"""Generic type to help mypy with the parse method when we know the exact
expected return type.
"""


def issubclass_safe(
    cls: type[object], class_or_tuple: Union[type[object], tuple[type[object]]]
) -> bool:
    """Checks if subclass is safe."""
    if isinstance(class_or_tuple, tuple):
        return any(issubclass_safe(cls, base) for base in class_or_tuple)

    if issubclass(cls, class_or_tuple):
        return True

    # Handle case where module was reloaded
    cls_module = importlib.import_module(cls.__module__)
    # Get the latest version of the base class from the module
    latest_base = getattr(cls_module, class_or_tuple.__name__, None)
    latest_base = cast(Union[tuple[type[object], ...], type[object]], latest_base)
    if issubclass(cls, latest_base):
        return True

    return False


class ObjectConfig(AbstractConfig, Generic[T]):
    """A config to represent an object from a class name and its constructor parameters."""

    """Path to class to be instantiated."""
    class_: str | None = Field(default=None, validate_default=True)
    """Initialization parameters."""
    params_: dict[str, ParamConfig] = {}

    DEFAULT_MODULE: ClassVar[str] = "."
    """Default module to import the class from."""
    INTERFACE: ClassVar[type] = object
    """Constraint on the class (must be a subclass of)."""
    REQUIRED_PARAMS: ClassVar[list[str]] = []
    """List of required parameters for this object constructor."""

    def __init__(self, **data):
        super().__init__(**data)
        self.logger = logger.getChild(self.__class__.__name__)

    @field_validator("params_")
    @classmethod
    def validate_params(cls, params_: dict[str, Any]) -> dict[str, Any]:
        """Make sure all required parameters are provided."""
        for p in cls.REQUIRED_PARAMS:
            if p not in params_:
                raise ValueError(f"Missing parameter {p}")
        return params_

    def get_module(self) -> str:
        return self.DEFAULT_MODULE

    def get_interface(self) -> type:
        return self.INTERFACE

    @classmethod
    def _get_class(cls, class_path: str, optional_module: Optional[str] = None) -> type:
        """Get class from string and an optional module.

        Will first try to import the class from `class_path` alone. If it results in an ImportError,
        will try to import from `f'{optional_module}.{class_path}'`

        Args:
            class_path (str): Class path with format 'my_module.MyClass'.
            optional_module (Optional[str]): Optional module path.
                Used to provide a default path for some known objects and simplify the notation.

        Raises:
            ValueError: if the class can't be imported, even using the optional module.
        """
        # splits class path from module path
        *modules, class_name = class_path.rsplit(".", 1)
        module_name = modules[0] if modules else optional_module

        if module_name is None:
            raise ValueError("Must specify a module to import class from")

        try:
            module = importlib.import_module(module_name)
            # get class_name from the module if available
            klass = getattr(module, class_name)
        except (ImportError, AttributeError):
            if optional_module and module_name != optional_module:
                full_klass_path = optional_module + "." + class_path
                return cls._get_class(full_klass_path)
            raise ValueError(f"Could not find {class_name} in {module_name}")

        return cast(type, klass)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> T:
        """Import `class_`, resolve `params_` and instantiate object."""
        self._global_data = resolved_data or {}
        self.logger.debug(f"OBJECT_CONFIG: parsing {self} using {resolved_data}")

        if self.class_ is None:
            raise ValueError(f"`class_` is required to parse object {self}")
        klass = self._get_class(self.class_, self.get_module())
        if not issubclass_safe(klass, self.get_interface()):
            raise ValueError(
                f"Invalid class '{klass}'. Expected a subclass of '{self.get_interface()}'"
            )
        params = self.resolve_params(self.params_)
        try:
            obj = klass(**params)
        except TypeError as e:
            self.logger.error(
                "OBJECT_CONFIG: failed to instantiate object due to improperly configured parameters"
            )
            raise e
        return cast(T, obj)


class HarvesterConfig(ObjectConfig[BaseHarvester]):
    """Configuration for any Harvester object.

    By default, will try to import from `wrench.harvester`.
    """

    DEFAULT_MODULE = "wrench.harvester"
    INTERFACE = BaseHarvester


class HarvesterType(RootModel):  # type: ignore[type-arg]
    """A model to wrap BaseHarvester and HarvesterConfig objects.

    The `parse` method always returns an object inheriting from BaseHarvester.
    """

    root: Union[BaseHarvester, HarvesterConfig]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> BaseHarvester:
        if isinstance(self.root, BaseHarvester):
            return self.root
        return self.root.parse(resolved_data)


class GrouperConfig(ObjectConfig[BaseGrouper]):
    """Configuration for any Grouper object.

    By default, will try to import from `wrench.grouper`.
    """

    DEFAULT_MODULE = "wrench.grouper"
    INTERFACE = BaseGrouper


class GrouperType(RootModel):  # type: ignore[type-arg]
    """A model to wrap BaseGrouper and GrouperConfig objects.

    The `parse` method always returns an object inheriting from BaseGrouper.
    """

    root: Union[BaseGrouper, GrouperConfig]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> BaseGrouper:
        if isinstance(self.root, BaseGrouper):
            return self.root
        return self.root.parse(resolved_data)


class MetadataBuilderConfig(ObjectConfig[BaseMetadataBuilder]):
    """Configuration for any BaseMetadataBuilder object.

    By default, will try to import from `wrench.metadatabuilder`.
    """

    DEFAULT_MODULE = "wrench.metadatabuilder"
    INTERFACE = BaseMetadataBuilder


class MetadataBuilderType(RootModel):  # type: ignore[type-arg]
    """A model to wrap BaseMetadataBuilder and MetadataBuilderConfig objects.

    The `parse` method always returns an object inheriting from BaseMetadataBuilder.
    """

    root: Union[BaseMetadataBuilder, MetadataBuilderConfig]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> BaseMetadataBuilder:
        if isinstance(self.root, BaseMetadataBuilder):
            return self.root
        return self.root.parse(resolved_data)


class CatalogerConfig(ObjectConfig[BaseCataloger]):
    """Configuration for any BaseCataloger object.

    By default, will try to import from `wrench.cataloger`.
    """

    DEFAULT_MODULE = "wrench.cataloger"
    INTERFACE = BaseCataloger


class CatalogerType(RootModel):  # type: ignore[type-arg]
    """A model to wrap BaseCataloger and CatalogerConfig objects.

    The `parse` method always returns an object inheriting from BaseCataloger.
    """

    root: Union[BaseCataloger, CatalogerConfig]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> BaseCataloger:
        if isinstance(self.root, BaseCataloger):
            return self.root
        return self.root.parse(resolved_data)


class ComponentConfig(ObjectConfig[Component]):
    """A config model for all components.

    In addition to the object config, components can have pre-defined parameters
    that will be passed to the `run` method, ie `run_params_`.
    """

    run_params_: dict[str, ParamConfig] = {}

    DEFAULT_MODULE = "wrench.components"
    INTERFACE = Component

    def get_run_params(self, resolved_data: dict[str, Any]) -> dict[str, Any]:
        self._global_data = resolved_data
        return self.resolve_params(self.run_params_)


class ComponentType(RootModel):  # type: ignore[type-arg]
    root: Union[Component, ComponentConfig]

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def parse(self, resolved_data: dict[str, Any] | None = None) -> Component:
        if isinstance(self.root, Component):
            return self.root
        return self.root.parse(resolved_data)

    def get_run_params(self, resolved_data: dict[str, Any]) -> dict[str, Any]:
        if isinstance(self.root, Component):
            return {}
        return self.root.get_run_params(resolved_data)
