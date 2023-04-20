from typing import Optional

import fastapi
from fastapi import testclient
from starlette import responses

from fixieai.agents import openai_proxy


def test_authorization_token_middleware():
    FAKE_TOKEN = "fixie-test-token"
    app = fastapi.FastAPI()

    @app.get("/")
    async def test_endpoint(expected_token: Optional[str] = None):
        assert openai_proxy._current_request_token.get() == expected_token

    @app.get("/stream")
    async def test_stream(count: int, expected_token: Optional[str] = None):
        def _gen():
            for _ in range(count):
                assert openai_proxy._current_request_token.get() == expected_token
                yield b"."

        return responses.StreamingResponse(_gen(), status_code=200)

    app.add_middleware(openai_proxy.OpenAIProxyRequestTokenForwarderMiddleware)

    client = testclient.TestClient(app)
    response = client.get(
        f"/?expected_token=test1",
        headers={"Authorization": f"Bearer test1"},
    )
    assert response.status_code == 200

    response = client.get(f"/")
    assert response.status_code == 200

    response = client.get(
        f"/?expected_token=test2",
        headers={"Authorization": f"Bearer test2"},
    )
    assert response.status_code == 200

    response = client.get("/stream?count=10")
    assert response.status_code == 200
    assert response.content == b"." * 10

    response = client.get(
        "/stream?count=10&expected_token=test-streaming",
        headers={"Authorization": f"Bearer test-streaming"},
    )
    assert response.status_code == 200
    assert response.content == b"." * 10
