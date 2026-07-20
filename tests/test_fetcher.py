from unittest.mock import Mock

import requests

from src.fetcher import DependencyFetcher


def test_existing_dependency_is_refreshed(tmp_path):
    target = tmp_path / "library.js"
    target.write_bytes(b"old code")
    fetcher = DependencyFetcher(tmp_path)
    response = Mock(content=b"current code")
    response.raise_for_status.return_value = None
    fetcher.session.get = Mock(return_value=response)

    assert fetcher.fetch("https://cdn.example.com/library.js") == "library.js"
    assert target.read_bytes() == b"current code"
    fetcher.session.get.assert_called_once()


def test_failed_refresh_preserves_previous_dependency(tmp_path):
    target = tmp_path / "library.js"
    target.write_bytes(b"known good code")
    fetcher = DependencyFetcher(tmp_path)
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("503")
    fetcher.session.get = Mock(return_value=response)

    assert fetcher.fetch("https://cdn.example.com/library.js") is None
    assert target.read_bytes() == b"known good code"


def test_same_basename_from_two_urls_gets_unique_names(tmp_path):
    fetcher = DependencyFetcher(tmp_path)
    response = Mock(content=b"code")
    response.raise_for_status.return_value = None
    fetcher.session.get = Mock(return_value=response)

    names = fetcher.fetch_all([
        "https://one.example.com/library.js",
        "https://two.example.com/library.js",
    ])

    assert names[0] == "library.js"
    assert names[1].startswith("library_")
    assert names[1].endswith(".js")
    assert len(list(tmp_path.glob("*.js"))) == 2
