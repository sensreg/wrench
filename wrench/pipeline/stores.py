# wrench/pipeline/stores.py
import abc
import asyncio
import json
import os
from typing import Any, Generic, Optional, TypeVar

T = TypeVar("T")


class Store(abc.ABC, Generic[T]):
    """Abstract base class for storing and retrieving data."""

    @abc.abstractmethod
    async def add(self, key: str, value: T, overwrite: bool = True) -> None:
        """Store a value with the given key."""
        pass

    @abc.abstractmethod
    async def get(self, key: str) -> Optional[T]:
        """Retrieve a value by key."""
        pass

    @abc.abstractmethod
    async def delete(self, key: str) -> None:
        """Delete a value by key."""
        pass

    @abc.abstractmethod
    async def list_keys(self) -> list[str]:
        """List all stored keys."""
        pass


class ResultStore(Store):
    """Storage for pipeline execution results."""

    @staticmethod
    def get_key(run_id: str, component_name: str, suffix: str = "") -> str:
        """Create a standardized key for storing component results."""
        key = f"{run_id}:{component_name}"
        if suffix:
            key += f":{suffix}"
        return key

    async def add_status_for_component(
        self, run_id: str, component_name: str, status: str
    ) -> None:
        """Store status for a component in a particular run."""
        await self.add(
            self.get_key(run_id, component_name, "status"), status, overwrite=True
        )

    async def get_status_for_component(
        self, run_id: str, component_name: str
    ) -> Optional[str]:
        """Get the status of a component in a particular run."""
        return await self.get(self.get_key(run_id, component_name, "status"))

    async def add_result_for_component(
        self, run_id: str, component_name: str, result: Any, overwrite: bool = True
    ) -> None:
        """Store the result of a component in a particular run."""
        await self.add(
            self.get_key(run_id, component_name), result, overwrite=overwrite
        )

    async def get_result_for_component(
        self, run_id: str, component_name: str
    ) -> Optional[Any]:
        """Get the result of a component in a particular run."""
        return await self.get(self.get_key(run_id, component_name))


class InMemoryStore(ResultStore):
    """In-memory implementation of a result store."""

    def __init__(self):
        """Initializes an InMemoryStore."""
        self._data: dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def add(self, key: str, value: Any, overwrite: bool = True) -> None:
        async with self._lock:
            if not overwrite and key in self._data:
                raise KeyError(f"Key '{key}' already exists and overwrite is False")
            self._data[key] = value

    async def get(self, key: str) -> Optional[Any]:
        async with self._lock:
            return self._data.get(key)

    async def delete(self, key: str) -> None:
        async with self._lock:
            if key in self._data:
                del self._data[key]

    async def list_keys(self) -> list[str]:
        async with self._lock:
            return list(self._data.keys())


class FileStore(ResultStore):
    """File-based implementation of a result store."""

    def __init__(self, directory: str = ".pipeline_store"):
        """Initializes a file store."""
        self.directory = directory
        os.makedirs(directory, exist_ok=True)
        self._lock = asyncio.Lock()

    def _get_file_path(self, key: str) -> str:
        """Convert a key to a valid file path."""
        # Replace characters that might not be valid in filenames
        safe_key = key.replace(":", "_").replace("/", "_")
        return os.path.join(self.directory, f"{safe_key}.json")

    async def add(self, key: str, value: Any, overwrite: bool = True) -> None:
        file_path = self._get_file_path(key)

        async with self._lock:
            if not overwrite and os.path.exists(file_path):
                raise KeyError(f"Key '{key}' already exists and overwrite is False")

            with open(file_path, "w") as f:
                json.dump(value, f)

    async def get(self, key: str) -> Optional[Any]:
        file_path = self._get_file_path(key)

        async with self._lock:
            if not os.path.exists(file_path):
                return None

            with open(file_path, "r") as f:
                return json.load(f)

    async def delete(self, key: str) -> None:
        file_path = self._get_file_path(key)

        async with self._lock:
            if os.path.exists(file_path):
                os.remove(file_path)

    async def list_keys(self) -> list[str]:
        async with self._lock:
            files = [f for f in os.listdir(self.directory) if f.endswith(".json")]
            return [f[:-5].replace("_", ":") for f in files]
