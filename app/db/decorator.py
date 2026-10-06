from collections.abc import Callable
from typing import TypeVar

from app.db.models.base import Base
from app.db.repository.base import RepositoryBase

T = TypeVar("T", bound=type[RepositoryBase])

repository_registry: dict[type[Base], type[RepositoryBase]] = {}


def repository(model_class: type[Base]) -> Callable[..., T]:
    def decorator(repo_class: T) -> T:
        """
        Decorator to register a repository for a model class

        :param repo_class:
        :return:
        """
        repository_registry[model_class] = repo_class
        return repo_class

    return decorator
