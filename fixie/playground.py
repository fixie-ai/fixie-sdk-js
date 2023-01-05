#!/usr/bin/env python3

import os
from typing import Any, Dict, List, Optional

from gql import Client
from gql import gql


class Playground:
    def __init__(self, gqlclient: Client, handle: Optional[str]=None):
        self._gqlclient = gqlclient
        if not handle:
            self._metadata = self.create()
            self._handle = str(self._metadata["handle"])
            print(f"Created Playground '{self._handle}'")
        else:
            self._handle = handle
            self._metadata = self.get_metadata()

    @property
    def handle(self) -> str:
        return self._handle

    @property
    def metadata(self) -> Dict[str, Any]:
        assert isinstance(self._metadata, dict)
        return self._metadata

    def get_metadata(self) -> Dict[str, Any]:
        query = gql(
            """
            query getPlayground($handle: String!) {
                playgroundByHandle(handle: $handle) {
                    handle
                    name
                    description
                    owner {
                        username
                    }
                    created
                    modified
                    published
                }
            }
        """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._handle}
        )
        if "playgroundByHandle" not in result or result["playgroundByHandle"] is None:
            raise ValueError("Playground not found")
        assert isinstance(result["playgroundByHandle"], dict)
        return result["playgroundByHandle"]

    def create(self) -> Dict[str, Any]:
        query = gql(
            """
            mutation CreatePlayground {
                createPlayground(playgroundData: {}) {
                    playground {
                        handle
                        name
                        description
                        owner {
                            id
                        }
                        created
                        modified
                        published
                    }
                }
            }
            """
        )
        result = self._gqlclient.execute(query)
        if "createPlayground" not in result or result["createPlayground"] is None:
            raise ValueError(f"Failed to create Playground '{self._handle}'")
        assert isinstance(result["createPlayground"], dict)
        assert isinstance(result["createPlayground"]["playground"], dict)
        return result["createPlayground"]["playground"]

    def delete(self) -> None:
        query = gql(
            """
            mutation DeletePlayground($handle: String!) {
                deletePlayground(handle: $handle) {
                    playground {
                        handle
                    }
                }
            }
        """
        )
        _ = self._gqlclient.execute(
            query, variable_values={"handle": self._handle}
        )

    def get_embeds(self) -> List[Dict[str, Any]]:
        query = gql(
            """
            query getEmbeds($handle: String!) {
                playgroundByHandle(handle: $handle) {
                    embeds {
                        key
                        embed {
                            id
                            contentType
                            created
                            contentHash
                            owner {
                                id
                            }
                            url
                        }
                    }
                }
            }
        """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._handle}
        )
        assert (
            "playgroundByHandle" in result
            and isinstance(result["playgroundByHandle"], dict)
            and isinstance(result["playgroundByHandle"]["embeds"], list)
        )
        return result["playgroundByHandle"]["embeds"]

    def get_messages(self) -> List[Dict[str, Any]]:
        query = gql(
            """
            query getMessages($handle: String!) {
                playgroundByHandle(handle: $handle) {
                    messages {
                        id
                        text
                        sentBy
                        type
                        inReplyTo { id }
                        timestamp
                    }
                }
            }
        """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._handle}
        )
        assert (
            "playgroundByHandle" in result
            and isinstance(result["playgroundByHandle"], dict)
            and isinstance(result["playgroundByHandle"]["messages"], list)
        )
        return result["playgroundByHandle"]["messages"]

    def query(self, text: str) -> str:
        query = gql(
            """
            mutation Post($handle: String!, $text: String!) {
                addPlaygroundMessage(messageData: {playground: $handle, text: $text}) {
                    message {
                        text
                    }
                }
            }
            """
        )
        result = self._gqlclient.execute(
            query, variable_values={"handle": self._handle, "text": text}
        )

        # The reply to the query comes in as the most recent 'response' message in the session.
        response = self.get_messages()[-1]
        assert isinstance(response["text"], str)
        return response["text"]
