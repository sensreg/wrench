import importlib
import pkgutil
from pathlib import Path
from typing import Any


def discover_components(package_name="wrench"):
    """Discover all available components in the package."""
    package = importlib.import_module(package_name)
    package_path = Path(package.__file__).parent

    # Specific directories to check for components
    component_paths = {
        "harvester": package_path / "harvester",
        "grouper": package_path / "grouper",
        "cataloger": package_path / "cataloger",
    }

    for component_type, path in component_paths.items():
        if not path.exists():
            continue

        # Find all subdirectories
        for module_info in pkgutil.iter_modules([str(path)]):
            if not module_info.ispkg:
                continue

            # Import the module to trigger registration
            importlib.import_module(
                f"{package_name}.{component_type}.{module_info.name}"
            )


class ComponentRegistry:
    """Registry for all pipeline components."""

    _registry: dict[str, Any] = {
        "harvester": {},
        "grouper": {},
        "metadatabuilder": {},
        "cataloger": {},
    }

    @classmethod
    def register(cls, component_type, name, component_class):
        """Register a component with the registry."""
        if component_type not in cls._registry:
            raise ValueError(f"Unknown component type: {component_type}")
        cls._registry[component_type][name] = component_class

    @classmethod
    def get(cls, component_type, name):
        """Get a component class by type and name."""
        if component_type not in cls._registry:
            raise ValueError(f"Unknown component type: {component_type}")
        if name not in cls._registry[component_type]:
            available = list(cls._registry[component_type].keys())
            raise ValueError(
                f"Unknown {component_type} '{name}'. Available: {available}"
            )
        return cls._registry[component_type][name]
