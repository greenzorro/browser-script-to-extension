import hashlib
import json
from unittest.mock import Mock

import pytest
import requests

from src.fetcher import DependencyFetcher


def response_with(content: bytes) -> Mock:
    response = Mock(content=content)
    response.raise_for_status.return_value = None
    return response


def lock_data(lib_dir):
    return json.loads(
        (lib_dir.parent / DependencyFetcher.LOCK_FILENAME).read_text(encoding="utf-8")
    )


def test_verified_dependency_is_reused_without_network(tmp_path):
    lib_dir = tmp_path / "lib"
    url = "https://cdn.example.com/library.js"
    first_fetcher = DependencyFetcher(lib_dir)
    first_fetcher.session.get = Mock(return_value=response_with(b"known good code"))

    assert first_fetcher.fetch_all([url]) == ["library.js"]

    second_fetcher = DependencyFetcher(lib_dir)
    second_fetcher.session.get = Mock(side_effect=AssertionError("network not expected"))

    assert second_fetcher.fetch_all([url]) == ["library.js"]
    second_fetcher.session.get.assert_not_called()
    entry = lock_data(lib_dir)["dependencies"][url]
    assert entry == {
        "filename": "library.js",
        "sha256": hashlib.sha256(b"known good code").hexdigest(),
    }


def test_refresh_dependencies_downloads_and_updates_hash(tmp_path):
    lib_dir = tmp_path / "lib"
    url = "https://cdn.example.com/library.js"
    first_fetcher = DependencyFetcher(lib_dir)
    first_fetcher.session.get = Mock(return_value=response_with(b"old code"))
    first_fetcher.fetch_all([url])

    refresh_fetcher = DependencyFetcher(lib_dir)
    refresh_fetcher.session.get = Mock(return_value=response_with(b"current code"))

    assert refresh_fetcher.fetch_all([url], refresh=True) == ["library.js"]
    assert (lib_dir / "library.js").read_bytes() == b"current code"
    assert lock_data(lib_dir)["dependencies"][url]["sha256"] == hashlib.sha256(
        b"current code"
    ).hexdigest()
    refresh_fetcher.session.get.assert_called_once_with(url, timeout=30)


def test_changed_url_with_same_basename_is_downloaded(tmp_path):
    lib_dir = tmp_path / "lib"
    old_url = "https://old.example.com/library.js"
    new_url = "https://new.example.com/library.js"
    first_fetcher = DependencyFetcher(lib_dir)
    first_fetcher.session.get = Mock(return_value=response_with(b"old source"))
    first_fetcher.fetch_all([old_url])

    second_fetcher = DependencyFetcher(lib_dir)
    second_fetcher.session.get = Mock(return_value=response_with(b"new source"))

    assert second_fetcher.fetch_all([new_url]) == ["library.js"]
    assert (lib_dir / "library.js").read_bytes() == b"new source"
    assert lock_data(lib_dir)["dependencies"] == {
        new_url: {
            "filename": "library.js",
            "sha256": hashlib.sha256(b"new source").hexdigest(),
        }
    }
    second_fetcher.session.get.assert_called_once_with(new_url, timeout=30)


def test_tampered_dependency_is_redownloaded(tmp_path):
    lib_dir = tmp_path / "lib"
    url = "https://cdn.example.com/library.js"
    first_fetcher = DependencyFetcher(lib_dir)
    first_fetcher.session.get = Mock(return_value=response_with(b"known good code"))
    first_fetcher.fetch_all([url])
    (lib_dir / "library.js").write_bytes(b"tampered code")

    repair_fetcher = DependencyFetcher(lib_dir)
    repair_fetcher.session.get = Mock(return_value=response_with(b"repaired code"))

    assert repair_fetcher.fetch_all([url]) == ["library.js"]
    assert (lib_dir / "library.js").read_bytes() == b"repaired code"
    repair_fetcher.session.get.assert_called_once_with(url, timeout=30)


def test_existing_file_without_valid_lock_is_not_trusted(tmp_path):
    lib_dir = tmp_path / "lib"
    lib_dir.mkdir()
    (lib_dir / "library.js").write_bytes(b"unverified legacy cache")
    (tmp_path / DependencyFetcher.LOCK_FILENAME).write_text(
        '{"version": 1, "dependencies": {"broken": "entry"}}',
        encoding="utf-8",
    )
    url = "https://cdn.example.com/library.js"
    fetcher = DependencyFetcher(lib_dir)
    fetcher.session.get = Mock(return_value=response_with(b"verified download"))

    assert fetcher.fetch_all([url]) == ["library.js"]
    assert (lib_dir / "library.js").read_bytes() == b"verified download"
    fetcher.session.get.assert_called_once_with(url, timeout=30)


def test_failed_refresh_preserves_dependency_and_lock(tmp_path):
    lib_dir = tmp_path / "lib"
    url = "https://cdn.example.com/library.js"
    first_fetcher = DependencyFetcher(lib_dir)
    first_fetcher.session.get = Mock(return_value=response_with(b"known good code"))
    first_fetcher.fetch_all([url])
    lock_before = (tmp_path / DependencyFetcher.LOCK_FILENAME).read_bytes()

    failed_fetcher = DependencyFetcher(lib_dir)
    failed_response = Mock()
    failed_response.raise_for_status.side_effect = requests.HTTPError("503")
    failed_fetcher.session.get = Mock(return_value=failed_response)

    with pytest.raises(RuntimeError, match="Build aborted"):
        failed_fetcher.fetch_all([url], refresh=True)

    assert (lib_dir / "library.js").read_bytes() == b"known good code"
    assert (tmp_path / DependencyFetcher.LOCK_FILENAME).read_bytes() == lock_before
    assert not list(lib_dir.glob(".*.download"))


def test_same_basename_from_two_urls_gets_stable_unique_names(tmp_path):
    lib_dir = tmp_path / "lib"
    urls = [
        "https://one.example.com/library.js",
        "https://two.example.com/library.js",
    ]
    first_fetcher = DependencyFetcher(lib_dir)
    first_fetcher.session.get = Mock(
        side_effect=[response_with(b"one"), response_with(b"two")]
    )

    names = first_fetcher.fetch_all(urls)

    assert names[0] == "library.js"
    assert names[1].startswith("library_")
    assert names[1].endswith(".js")
    assert len(list(lib_dir.glob("*.js"))) == 2

    second_fetcher = DependencyFetcher(lib_dir)
    second_fetcher.session.get = Mock(side_effect=AssertionError("network not expected"))
    assert second_fetcher.fetch_all(urls) == names
    second_fetcher.session.get.assert_not_called()
