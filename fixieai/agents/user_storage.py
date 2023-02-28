import base64
import json
from typing import TYPE_CHECKING, Dict, List, MutableMapping, Union

import requests

from fixieai import constants

if TYPE_CHECKING:
    from fixieai.agents.api import AgentQuery

UserStoragePrimitives = Union[bool, int, float, str, bytes, None]
UserStorageType = Union[
    UserStoragePrimitives,
    List["UserStorageType"],
    Dict[str, "UserStorageType"],
]


class UserStorage(MutableMapping[str, UserStorageType]):
    """UserStorage provides a dict-like interface to a user-specific storage.

    Usage:
    >>> from fixieai import AgentQuery, Message
    >>> query = AgentQuery(
    ...   Message("incoming query"),
    ...   access_token="fake-access-token"
    ... )
    >>> storage = UserStorage(query, "fake-agent")
    >>> storage["key"] = "value"
    >>> storage["complex-key"] = {"key1": {"key2": [12, False, None, b"binary"]}}
    >>> assert len(storage) == 2
    >>> assert storage["complex-key"]["key1"]["key2"][-1] == b"binary"
    """

    def __init__(
        self,
        query: "AgentQuery",
        agent_id: str,
        userstorage_url: str = constants.FIXIE_USER_STORAGE_URL,
    ):
        # TODO(hessam): Remove agent_id from args once access_token includes agent_id
        #  as well.
        self._agent_id = agent_id
        self._userstorage_url = userstorage_url
        self._session = requests.Session()
        self._session.headers.update({"Authorization": f"Bearer {query.access_token}"})

    def __setitem__(self, key: str, value: UserStorageType):
        url = f"{self._userstorage_url}/{self._agent_id}/{key}"
        response = self._session.post(url, json={"data": to_json(value)})
        response.raise_for_status()

    def __getitem__(self, key: str) -> UserStorageType:
        url = f"{self._userstorage_url}/{self._agent_id}/{key}"
        try:
            response = self._session.get(url)
            response.raise_for_status()
            return from_json(response.json()["data"])
        except requests.exceptions.HTTPError as e:
            raise KeyError(f"Key {key} not found") from e

    def __contains__(self, key: object) -> bool:
        url = f"{self._userstorage_url}/{self._agent_id}/{key}"
        try:
            response = self._session.head(url)
            response.raise_for_status()
            return True
        except requests.exceptions.HTTPError as e:
            return False

    def __delitem__(self, key: str):
        url = f"{self._userstorage_url}/{self._agent_id}/{key}"
        try:
            response = self._session.delete(url)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise KeyError(f"Key {key} not found") from e

    def _get_all_keys(self):
        url = f"{self._userstorage_url}/{self._agent_id}"
        response = self._session.get(url)
        response.raise_for_status()
        return [value["key"] for value in response.json()]

    def __iter__(self):
        return iter(self._get_all_keys())

    def __len__(self):
        return len(self._get_all_keys())


JsonType = Union[None, int, float, str, bool, List["JsonType"], Dict[str, "JsonType"]]


def to_json(obj: UserStorageType) -> str:
    """Serialize a UserStorageType to a JSON string."""
    return json.dumps(to_json_type(obj))


def from_json(json_dump: str) -> UserStorageType:
    """Deserializes a UserStorageType from a JSON string."""
    return from_json_type(json.loads(json_dump))


def to_json_type(obj: UserStorageType) -> JsonType:
    """Encodes a UserStorageType to JsonType."""
    if isinstance(obj, bytes):
        return {"type": "_bytes_ascii", "data": base64.b64encode(obj).decode("ASCII")}
    elif isinstance(obj, list):
        return [to_json_type(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: to_json_type(value) for key, value in obj.items()}
    else:
        return obj


def from_json_type(obj: JsonType) -> UserStorageType:
    """Decodes a JsonType to UserStorageType."""
    if _is_bytes_encoded_json_dict(obj):
        return base64.b64decode(obj["data"])  # type: ignore
    elif isinstance(obj, list):
        return [from_json_type(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: from_json_type(value) for key, value in obj.items()}
    else:
        return obj


def _is_bytes_encoded_json_dict(obj: JsonType) -> bool:
    """Returns True if obj is a {"type": "_bytes_ascii", "data": encoded_string}."""
    if not isinstance(obj, dict):
        return False
    if set(obj.keys()) != {"type", "data"}:
        return False
    elif obj["type"] != "_bytes_ascii" or not isinstance(obj["data"], str):
        return False
    else:
        return True
