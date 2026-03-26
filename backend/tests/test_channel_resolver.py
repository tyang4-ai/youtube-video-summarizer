import pytest
from unittest.mock import patch, MagicMock
from app.services.channel_resolver import resolve_channel_id


def test_extract_from_channel_url():
    cid, _ = resolve_channel_id("https://www.youtube.com/channel/UC29ju8bIPH5as8OGnQzwJyA")
    assert cid == "UC29ju8bIPH5as8OGnQzwJyA"


def test_raw_channel_id():
    cid, _ = resolve_channel_id("UC29ju8bIPH5as8OGnQzwJyA")
    assert cid == "UC29ju8bIPH5as8OGnQzwJyA"


@patch("app.services.channel_resolver.httpx.get")
def test_resolve_handle_url(mock_get):
    mock_resp = MagicMock()
    mock_resp.text = '<meta itemprop="identifier" content="UC29ju8bIPH5as8OGnQzwJyA">'
    mock_resp.raise_for_status = MagicMock()
    mock_get.return_value = mock_resp
    cid, _ = resolve_channel_id("https://www.youtube.com/@fireship")
    assert cid == "UC29ju8bIPH5as8OGnQzwJyA"


def test_invalid_url_raises():
    with pytest.raises(ValueError):
        resolve_channel_id("")
