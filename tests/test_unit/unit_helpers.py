import contextlib
import os
import json
import pytest
import requests
from pathlib import Path


def make_path(name):
    return Path(__file__).parent / "fixtures" / name


@contextlib.contextmanager
def env(**kwargs):
    original = {key: os.getenv(key) for key in kwargs}
    os.environ.update({key: str(value) for key, value in kwargs.items()})
    try:
        yield
    finally:
        for key, value in original.items():
            if value is None:
                del os.environ[key]
            else:
                os.environ[key] = value


def load_example(file):
    with open(make_path(file)) as f:
        j = json.load(f)
    return j


def contains_exactly(items, lst):
    return len(items) == len(lst) and all(i in lst for i in items)


class MockResponse:
    def __init__(self, status_code):
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 300:
            raise requests.HTTPError(self.status_code)


@pytest.fixture(scope="function")
def mock_session(monkeypatch, request):

    def mock_method(*args, **kwargs):
        return MockResponse(request.param)

    monkeypatch.setattr(requests.Session, "patch", mock_method)
    monkeypatch.setattr(requests.Session, "get", mock_method)
