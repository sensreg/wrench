import enum
import os
from typing import Any, ClassVar, Literal, Union

from pydantic import BaseModel


class ParamResolverEnum(str, enum.Enum):
    ENV = "ENV"
    CONFIG_KEY = "CONFIG_KEY"


class ParamToResolveConfig(BaseModel):
    def resolve(self, data: dict[str, Any]) -> Any:
        raise NotImplementedError


class ParamFromEnvConfig(ParamToResolveConfig):
    resolver_: Literal[ParamResolverEnum.ENV] = ParamResolverEnum.ENV
    var_: str

    def resolve(self, data: dict[str, Any]) -> Any:
        return os.environ.get(self.var_)


class ParamFromKeyConfig(ParamToResolveConfig):
    resolver_: Literal[ParamResolverEnum.CONFIG_KEY] = ParamResolverEnum.CONFIG_KEY
    key_: str

    KEY_SEP: ClassVar[str] = "."

    def resolve(self, data: dict[str, Any]) -> Any:
        d = data
        for k in self.key_.split(self.KEY_SEP):
            d = d[k]
        return d


ParamConfig = Union[
    float,
    str,
    ParamFromEnvConfig,
    ParamFromKeyConfig,
    dict[str, Any],
]
