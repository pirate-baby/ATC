"""Pytest configuration and fixtures for tests."""

import os

os.environ.setdefault("JWT_SECRET_KEY", "atc-dev-jwt-secret-do-not-use-in-production")
