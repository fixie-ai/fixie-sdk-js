from __future__ import annotations

import logging
from typing import Optional

import jwt
from pydantic import dataclasses as pydantic_dataclasses

from fixieai import constants

# The JWT claim containing the agent ID
_AGENT_ID_JWT_CLAIM = "aid"
_USER_ID_JWT_CLAIM = "sub"

logger = logging.getLogger(__file__)


@pydantic_dataclasses.dataclass
class VerifiedTokenClaims:
    """Verified claims from an agent token."""

    # The agent_id for which the request is intended.
    agent_id: str

    # Indicates whether the request is on behalf of a user or anonymous.
    is_anonymous: bool

    # The verified token.
    token: str

    @staticmethod
    def from_token(
        token: str,
        jwks_client: jwt.PyJWKClient,
        expected_agent_id: Optional[str],
    ) -> Optional[VerifiedTokenClaims]:
        try:
            public_key = jwks_client.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                public_key.key,
                algorithms=["EdDSA"],
                audience=constants.FIXIE_AGENT_API_AUDIENCES,
            )
        except jwt.DecodeError:
            return None

        token_agent_id = claims.get(_AGENT_ID_JWT_CLAIM)
        if not isinstance(token_agent_id, str):
            # Agent id claim is required
            logger.warning("Rejecting valid JWT without any agent ID claim")
            return None

        if expected_agent_id is not None and token_agent_id != expected_agent_id:
            # The agent ID in the token did not match the allowed value.
            logger.warning(
                f"Rejecting valid JWT because agent ID in token ({token_agent_id!r}) did not match {expected_agent_id!r}"
            )
            return None

        return VerifiedTokenClaims(
            agent_id=token_agent_id,
            is_anonymous=claims.get(_USER_ID_JWT_CLAIM) is None,
            token=token,
        )
