"""Pytest configuration and fixtures for tests."""

import os

# Set required environment variables before importing app modules
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-testing-only")
