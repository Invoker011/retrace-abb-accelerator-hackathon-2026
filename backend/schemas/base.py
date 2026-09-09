"""Base schema definitions and resilient Pydantic fallback."""
try:
    from pydantic import BaseModel, Field
except ImportError:
    import re

    class BaseModel:  # type: ignore
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
                # Map camelCase alias to snake_case attribute
                snake_k = re.sub(r"(?<!^)(?=[A-Z])", "_", k).lower()
                if snake_k != k:
                    setattr(self, snake_k, v)

        def dict(self):
            return self.__dict__

        def model_dump(self):
            return self.__dict__

    def Field(default=None, default_factory=None, **kwargs):  # type: ignore
        if default_factory is not None:
            return default_factory()
        return default if default is not ... else None
