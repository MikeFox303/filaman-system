import pytest
from pydantic import ValidationError

from app.api.v1.admin import UserCreate
from app.api.v1.me import MeUpdate


@pytest.mark.parametrize("language", ["en", "de", "ru"])
def test_user_language_accepts_supported_language(language):
    assert MeUpdate(language=language).language == language
    assert UserCreate(email="user@example.com", password="password123", language=language).language == language


@pytest.mark.parametrize("model", [MeUpdate, UserCreate])
def test_user_language_rejects_unknown_language(model):
    kwargs = {"language": "fr"}
    if model is UserCreate:
        kwargs.update(email="user@example.com", password="password123")

    with pytest.raises(ValidationError):
        model(**kwargs)
