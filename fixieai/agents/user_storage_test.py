import doctest
import re

import pytest

from fixieai import constants
from fixieai.agents import api
from fixieai.agents import user_storage

FAKE_AGENT_ID = "fake-agent"
FAKE_ACCESS_TOKEN = "fake-access-token"


class MockUserStorageService:
    """Mocks /api/userstorage behavior."""

    def __init__(self):
        self._data = {}

    def _parse_request(self, request):
        assert request.headers["Authorization"] == f"Bearer {FAKE_ACCESS_TOKEN}"
        prefix = f"/api/userstorage/{FAKE_AGENT_ID}"
        assert request.path.startswith(prefix)
        key = request.path[len(prefix) + 1 :]
        return key

    def post(self, request, context):
        key = self._parse_request(request)
        assert key
        self._data[key] = request.json()["data"]
        return {"msg": "success"}

    def get(self, request, context):
        key = self._parse_request(request)
        if key:
            return {"data": self._data[key]}
        else:
            return [{"key": key, "value": value} for key, value in self._data.items()]

    def head(self, request, context):
        key = self._parse_request(request)
        assert key
        try:
            self._data[key]
        except KeyError:
            context.status_code = 400
            return {"msg": "key doesn't exist"}
        else:
            context.status_code = 200
            return {"msg": "key exists"}

    def delete(self, request, context):
        key = self._parse_request(request)
        assert key
        del self._data[key]
        return {"msg": "success"}


@pytest.fixture
def mock_user_storage_urls(requests_mock):
    mock_storage_service = MockUserStorageService()
    user_storage_path_re = re.compile(
        "^" + re.escape(constants.FIXIE_USER_STORAGE_URL) + "/"
    )
    requests_mock.post(user_storage_path_re, json=mock_storage_service.post)
    requests_mock.get(user_storage_path_re, json=mock_storage_service.get)
    requests_mock.head(user_storage_path_re, json=mock_storage_service.head)
    requests_mock.delete(user_storage_path_re, json=mock_storage_service.delete)


VALUES_TO_TEST = [
    1,
    2.4,
    True,
    b"binary",
    "simple_str",
    {"key": "value"},
    {"key1": {"key2": ["value1", True, b"binary2", None, 4.3]}},
]


@pytest.mark.parametrize("test_value", VALUES_TO_TEST)
def test_user_storage(mock_user_storage_urls, test_value):
    query = api.AgentQuery(
        message=api.Message("sample query"), access_token=FAKE_ACCESS_TOKEN
    )
    storage = user_storage.UserStorage(query, agent_id=FAKE_AGENT_ID)

    # Add the value and test its existence
    storage["key"] = test_value
    assert "key" in storage
    assert len(storage) == 1
    assert storage["key"] == test_value
    assert list(storage) == ["key"]

    del storage["key"]
    assert "key" not in storage
    assert len(storage) == 0
    with pytest.raises(KeyError):
        _ = storage["key"]

    val = storage.get("key", "default value")
    assert val == "default value"


def test_doctest(mock_user_storage_urls):
    doctest.testmod(user_storage, raise_on_error=True)
