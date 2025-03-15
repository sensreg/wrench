from wrench.components.registry import ComponentRegistry


def register_component(component_type, name=None):
    """Decorator to register component classes."""

    def decorator(cls):
        component_name = name or cls.__name__.lower().replace("component", "")
        ComponentRegistry.register(component_type, component_name, cls)
        return cls

    return decorator
