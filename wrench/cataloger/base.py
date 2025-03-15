from abc import ABC, abstractmethod
from typing import Sequence

from wrench.log import logger
from wrench.models import CommonMetadata


class BaseCataloger(ABC):
    def __init__(self, endpoint: str, api_key: str):
        """
        Initializes the base class with the given endpoint and API key.

        Args:
            endpoint (str): The API endpoint URL.
            api_key (str): The API key for authentication.
        """
        self.endpoint = endpoint
        self.api_key = api_key

        self.logger = logger.getChild(self.__class__.__name__)

    @abstractmethod
    def register(self, service: CommonMetadata, groups: Sequence[CommonMetadata]):
        pass
