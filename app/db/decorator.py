from collections.abc import Callable

from app.db.models.base import Base
from app.db.repository.base import RepositoryBase

repository_registry: dict[type[Base], type[RepositoryBase]] = {}


def repository[T: type[RepositoryBase]](model_class: type[Base]) -> Callable[[T], T]:
    def decorator(repo_class: T) -> T:
        """
        Decorator to register a repository for a model class

        :param repo_class:
        :return:
        """
        repository_registry[model_class] = repo_class
        return repo_class

    return decorator
