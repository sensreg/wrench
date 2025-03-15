from abc import ABC, abstractmethod
from typing import Sequence

from wrench.models import CommonMetadata, Group


class BaseMetadataBuilder(ABC):
    @abstractmethod
    def build_service_metadata(self, source_data: Sequence) -> CommonMetadata:
        """
        Retrieves metadata for service endpoint.

        Returns:
            CommonMetadata: Data model conformant to catalog requirement.
        """
        pass

    @abstractmethod
    def build_group_metadata(self, group: Group) -> CommonMetadata:
        """
        Builds metadata for groups returned by Grouper.

        Returns:
            CommonMetadata: Data model conformant to catalog requirement.
        """
        pass
