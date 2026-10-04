"""Small environment-backed application settings."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Settings:
    service_name: str = "Support Resolution Assistant"
    version: str = "0.1.0"
    environment: str = os.getenv("APP_ENV", "development")


settings = Settings()
