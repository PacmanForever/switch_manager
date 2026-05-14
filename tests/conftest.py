"""Shared test fixtures for switchflow_controller."""

from __future__ import annotations

import pytest


@pytest.fixture
def auto_enable_custom_integrations() -> bool:
	"""Enable loading integrations from the local custom_components directory."""
	return True