from __future__ import annotations

from pathlib import Path

import yaml

from .grading_profile import GradingProfile


class GradingConfig:
    def __init__(self, path: str) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"Grading config not found at {self._path}")
        with self._path.open("r", encoding="utf-8") as handle:
            grading_config_document = yaml.safe_load(handle) or {}
        self.profiles: dict[str, GradingProfile] = {
            profile_name: GradingProfile.from_dict(grading_profile_document)
            for profile_name, grading_profile_document in (
                grading_config_document.get("profiles") or {}
            ).items()
        }

    def get(self, name: str) -> GradingProfile:
        if name not in self.profiles:
            raise KeyError(f"Grading profile '{name}' not defined")
        return self.profiles[name]


def load_grading_config(path: str) -> GradingConfig:
    return GradingConfig(path)

