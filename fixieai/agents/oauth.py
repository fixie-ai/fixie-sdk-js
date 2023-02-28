import dataclasses
import datetime
import json
import logging
import secrets
from typing import Dict, List, Optional
from urllib import parse

import dataclasses_json
import requests

from fixieai import constants
from fixieai.agents import api
from fixieai.agents import user_storage


@dataclasses.dataclass
class OAuthParams:
    """Encapsulates OAuth parameters, including secret, auth uri, and the scope.

    Agents who want to use OAuth flow, should declare their secrets via this object.
    """

    client_id: str
    client_secret: str
    auth_uri: str
    token_uri: str
    scopes: List[str]

    @classmethod
    def from_client_secrets_file(
        cls, secrets_path: str, scopes: List[str]
    ) -> "OAuthParams":
        """Initializes OAuth from a secrets file, e.g., as obtained from the Google
        Cloud Console.

        Args:
            secrets_path: Path to a json file holding secret values.
            scopes: A list of scopes that access needs to be requested for.
        """
        with open(secrets_path, "r") as file:
            data = json.load(file)
            secrets = data["web"] or data["installed"]
            return cls(
                secrets["client_id"],
                secrets["client_secret"],
                secrets["auth_uri"],
                secrets["token_uri"],
                scopes,
            )


class OAuthHandler:
    """
    OAuthHandler that wraps around a (OAuthParams, query) to authenticate.

    This client object provides 3 main method:
        * credentials: Returns current user's OAuth access token, or None if they are
            not authenticated.
        * get_authorization_url: Returns a url that the users can click to
            authenticate themselves.
        * authorize: Exchanges a received access code (from auth redirect callback) for
            an access token. If successful, user's storage is updated.
    """

    # OAuth keys reserved in UserStorage
    OAUTH_STATE_KEY = "_oauth_state"
    OAUTH_TOKEN_KEY = "_oauth_token"

    def __init__(
        self,
        oauth_params: OAuthParams,
        query: api.AgentQuery,
        agent_id: str,
    ):
        self._storage = user_storage.UserStorage(query, agent_id)
        self._oauth_params = oauth_params
        self._agent_id = agent_id

    def get_authorization_url(self) -> str:
        """Returns a URL to launch the authorization flow."""
        auth_state = f"{self._agent_id}:{secrets.token_urlsafe()}"
        data = {
            "response_type": "code",
            "access_type": "offline",
            "client_id": self._oauth_params.client_id,
            "scope": " ".join(self._oauth_params.scopes),
            "state": auth_state,
            "redirect_uri": constants.FIXIE_OAUTH_REDIRECT_URL,
        }
        url = self._oauth_params.auth_uri + "?" + parse.urlencode(data)
        # Store auth_state in UserStorage for validation later.
        self._storage[self.OAUTH_STATE_KEY] = auth_state
        return url

    def user_token(self) -> Optional[str]:
        """Returns current user's OAuth credentials, or None if not authorized."""
        try:
            creds_json = self._storage[self.OAUTH_TOKEN_KEY]
        except KeyError:
            return None

        if not isinstance(creds_json, str):
            logging.warning(
                f"Value at user_storage[{self.OAUTH_TOKEN_KEY!r}] is "
                f"not an OAuthCredentials json: {creds_json!r}"
            )
            del self._storage[self.OAUTH_TOKEN_KEY]
            return None

        try:
            creds = _OAuthCredentials.from_json(creds_json)
        except (TypeError, LookupError, ValueError):
            logging.warning(
                f"Value at user_storage[{self.OAUTH_TOKEN_KEY!r}] is "
                f"not a valid _OAuthCredentials json: {creds_json!r}"
            )
            del self._storage[self.OAUTH_TOKEN_KEY]
            return None

        if creds.expired:
            logging.debug(f"Credentials expired at {creds.expiry}")
            if not creds.refresh_token:
                logging.warning("No refresh token available")
                return None
            logging.debug("Refreshing credentials...")
            creds.refresh(self._oauth_params)
            self._save_credentials(creds)  # Save refreshed token to UserStorage
        return creds.access_token

    def authorize(self, state: str, code: str):
        """Authorize the received access `code` against the client secret.

        If successful, the credentials will be saved in user storage.
        """
        expected_state = self._storage[self.OAUTH_STATE_KEY]
        if state != expected_state:
            logging.warning(
                f"Unknown state token, expected: {expected_state!r} actual: {state!r}"
            )
            raise ValueError(f"Unknown state token")

        data = {
            "grant_type": "authorization_code",
            "client_id": self._oauth_params.client_id,
            "client_secret": self._oauth_params.client_secret,
            "code": code,
            "redirect_uri": constants.FIXIE_OAUTH_REDIRECT_URL,
        }
        response = _send_authorize_request(self._oauth_params.token_uri, data)
        logging.debug(
            f"OAuth auth request succeeded, lifetime={response.expires_in} "
            f"refreshable={response.refresh_token is not None}"
        )
        credentials = _OAuthCredentials(
            response.access_token,
            _get_expiry(response.expires_in),
            response.refresh_token,
        )
        self._save_credentials(credentials)

    def _save_credentials(self, credentials: "_OAuthCredentials"):
        self._storage[self.OAUTH_TOKEN_KEY] = credentials.to_json()


def _encode_iso_format(value: Optional[datetime.datetime]) -> Optional[str]:
    """Encodes a datetime to a ISO 8601 string, or None."""
    if value is None:
        return None
    return value.isoformat()


def _decode_iso_format(value: Optional[str]) -> Optional[datetime.datetime]:
    """Decodes a datetime from a ISO 8601 string, or None."""
    if value is None:
        return None
    return datetime.datetime.fromisoformat(value)


@dataclasses.dataclass
class _OAuthCredentials(dataclasses_json.DataClassJsonMixin):
    """Holds OAuth credentials, their expiration, and refresh token for a user."""

    access_token: str
    expiry: Optional[datetime.datetime] = dataclasses.field(
        default=None,
        metadata=dataclasses_json.config(
            encoder=_encode_iso_format, decoder=_decode_iso_format
        ),
    )
    refresh_token: Optional[str] = None

    @property
    def expired(self) -> bool:
        """Whether the credentials have expired."""
        return self.expiry is not None and datetime.datetime.utcnow() > self.expiry

    def refresh(self, oauth_params: OAuthParams):
        """Refreshes the access token."""
        if not self.refresh_token:
            raise ValueError("Cannot refresh without a refresh token")

        data = {
            "grant_type": "refresh_token",
            "client_id": oauth_params.client_id,
            "client_secret": oauth_params.client_secret,
            "refresh_token": self.refresh_token,
        }
        response = _send_authorize_request(oauth_params.token_uri, data)
        logging.debug(
            f"OAuth refresh request succeeded, lifetime={response.expires_in}"
        )
        self.access_token = response.access_token
        self.expiry = _get_expiry(response.expires_in)


@dataclasses.dataclass
class _OAuthTokenResponse(dataclasses_json.DataClassJsonMixin):
    """Holds an OAuth response from the OAuth server."""

    access_token: str
    scope: str
    token_type: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None


def _send_authorize_request(uri: str, data: Dict[str, str]) -> _OAuthTokenResponse:
    """POSTs `data` to `uri` and parses the output as an OAuthTokenResponse."""
    response = requests.post(uri, data=data)
    response.raise_for_status()
    content_type = response.headers["Content-Type"].split(";")[0].strip()
    if content_type == "application/json":
        response_dict = response.json()
    elif content_type == "application/x-www-form-urlencoded":
        # urllib parses form data into a list for each key, even if there's only one value.
        response_dict = {k: v[0] for k, v in parse.parse_qs(response.text).items()}
    else:
        raise ValueError(f"Unexpected response content type: {content_type}")
    if "error" in response_dict:
        raise ValueError("OAuth auth request failed")
    return _OAuthTokenResponse.from_dict(response_dict)


def _get_expiry(expires_in_seconds: Optional[int]) -> Optional[datetime.datetime]:
    """Returns the absolute expiration datetime from a relative expires_in_seconds."""
    if expires_in_seconds is None:
        return None
    return datetime.datetime.utcnow() + datetime.timedelta(seconds=expires_in_seconds)
