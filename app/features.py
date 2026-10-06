from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel

from app.config import Config


class FeatureInfo(BaseModel):
    id: str
    title: str
    description: str


@dataclass(frozen=True)
class Feature:
    info: FeatureInfo
    enabled: Callable[[Config], bool]


FEATURES: list[Feature] = [
    Feature(
        info=FeatureInfo(
            id="organizations",
            title="Organizations",
            description="Register and manage organizations, identified by their URA number",
        ),
        enabled=lambda _: True,
    ),
    Feature(
        info=FeatureInfo(
            id="clients",
            title="Clients",
            description="Register and manage the clients of an organization",
        ),
        enabled=lambda _: True,
    ),
    Feature(
        info=FeatureInfo(
            id="certificates",
            title="Certificates",
            description="Manage the certificates of organizations and clients",
        ),
        enabled=lambda _: True,
    ),
    Feature(
        info=FeatureInfo(
            id="sources",
            title="Sources",
            description="Manage the sources of organizations and clients",
        ),
        enabled=lambda _: True,
    ),
]


def enabled_features(config: Config) -> list[FeatureInfo]:
    return [feature.info for feature in FEATURES if feature.enabled(config)]
