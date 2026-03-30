"""Unit tests for SQLAlchemy models and Pydantic schemas."""
import uuid

import pytest
from pydantic import ValidationError

from shared.models.project import Project
from shared.models.scene import Scene
from shared.models.shot import Shot
from shared.models.style_preset import StylePreset
from shared.schemas.project import ProjectCreate


def test_project_model_defaults():
    p = Project(title="test")
    assert p.title == "test"
    # server_default="draft" — Python side is None until DB commit
    assert p.status is None or p.status == "draft"
    assert p.description is None


def test_scene_model_has_required_fields():
    s = Scene(
        script_version_id=uuid.uuid4(),
        order_index=0,
        title="Opening",
        status="drafted",
    )
    assert s.order_index == 0
    assert s.status == "drafted"


def test_shot_model_defaults():
    s = Shot(
        scene_id=uuid.uuid4(),
        order_index=0,
    )
    assert s.order_index == 0
    # server_default="drafted" — Python side is None until DB commit
    assert s.status is None or s.status == "drafted"


def test_style_preset_global_flag():
    sp = StylePreset(
        name="Test Style",
        is_global=True,
        project_id=None,
    )
    assert sp.is_global is True
    assert sp.project_id is None


def test_project_create_schema_valid():
    pc = ProjectCreate(title="My Project", description="test desc")
    assert pc.title == "My Project"


def test_project_create_schema_requires_title():
    with pytest.raises(ValidationError):
        ProjectCreate(description="no title")
