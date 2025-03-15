from typing import Sequence

from wrench.models import CommonMetadata, Group
from wrench.pipeline.component import DataModel


class Items(DataModel):
    devices: Sequence[dict]


class Groups(DataModel):
    groups: Sequence[Group]


class Metadata(DataModel):
    service_metadata: CommonMetadata
    group_metadata: list[CommonMetadata]
