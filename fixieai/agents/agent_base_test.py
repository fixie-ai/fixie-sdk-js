import os

import pytest
import yaml
from fastapi import testclient
from pydantic import dataclasses as pydantic_dataclasses

import fixieai
from fixieai import agents
from fixieai.agents import agent_base
from fixieai.agents import exceptions
from fixieai.agents import token

agent_id = "dummy"
CORPUS_RESPONSE = agents.CorpusResponse(
    partitions=[agents.CorpusPartition("newPartition")],
    page=agents.CorpusPage([agents.CorpusDocument("doc1", "doc1Content".encode())]),
)
CORPUS_RESPONSE_JSON = {
    "partitions": [
        {
            "partition": "newPartition",
            "first_page_token": None,
        }
    ],
    "page": {
        "documents": [
            {
                "source_name": "doc1",
                "content": "ZG9jMUNvbnRlbnQ=",
                "mime_type": "text/plain",
                "encoding": "UTF-8",
            }
        ],
        "next_page_token": None,
    },
}
CORPUS_REQUEST_JSON = {
    "partition": "defaultPartition",
    "page_token": "token",
}


@pytest.fixture(autouse=True)
def mock_token_verifier(mocker):
    return mocker.patch.object(
        token.VerifiedTokenClaims,
        "from_token",
        return_value=token.VerifiedTokenClaims(
            agent_id="fake agent id", is_anonymous=False, token="fake token"
        ),
    )


@pytest.fixture
def dummy_agent(mocker):
    mocker.patch.dict(os.environ, {"FIXIE_ALLOWED_AGENT_ID": "fake agent id"})

    @pydantic_dataclasses.dataclass
    class DummyMetadata:
        dummy_metadata: bool = True

    class DummyAgent(agents.AgentBase):
        def metadata(self):
            return DummyMetadata()

        def validate(self):
            pass

    agent = DummyAgent(
        oauth_params=fixieai.OAuthParams(
            client_id="dummy",
            client_secret="dummy",
            auth_uri="dummy",
            token_uri="dummy",
            scopes=["dummy"],
        ),
    )

    @agent.register_func
    def simple1(query: agents.Message) -> str:
        return "Simple response 1"

    @agent.register_func()
    def simple2(query: agents.Message):
        return "Simple response 2"

    @agent.register_func(func_name="custom")
    def simple3(query):
        return "Simple response custom"

    @agent.register_func()
    def unhandled_exception(query):
        raise ValueError("Func failed!")

    @agent.register_func()
    def agent_exception(query):
        raise exceptions.AgentException(
            response_message="Agent exception!",
            error_message="My exception occurred.",
            error_code="ERR_MY_ERROR_CODE",
            http_status_code=400,
            detail=1,
        )

    @agent.register_func(func_name="corpus")
    def check_api_routing(query):
        return "Success"

    @agent.register_corpus_func
    def load_corpus(request: agents.CorpusRequest) -> agents.CorpusResponse:
        return CORPUS_RESPONSE

    @agent.register_corpus_func(func_name="custom_name_corpus_load")
    def load_corpus_custom_name(request: agents.CorpusRequest):
        return CORPUS_RESPONSE

    @agent.register_corpus_func(func_name="simple1")
    def load_corpus_existing_fn_name(request):
        return CORPUS_RESPONSE

    @agent.register_corpus_func()
    def unhandled_corpus_exception(query):
        raise ValueError("Corpus func failed!")

    @agent.register_corpus_func()
    def corpus_agent_exception(query):
        raise exceptions.AgentException(
            response_message="Corpus agent exception!",
            error_message="My exception occurred.",
            error_code="ERR_MY_ERROR_CODE",
            http_status_code=400,
            detail=1,
        )

    return agent


def test_simple_agent_handshake(dummy_agent, mocker):
    client = testclient.TestClient(dummy_agent.app())

    # Use a small chunk size to exercise chunking logic
    mocker.patch.object(agent_base, "_RESPONSE_CHUNK_SIZE", 2)
    response = client.get("/", headers={"Authorization": "Bearer fixie-test-token"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/yaml"
    yaml_content = yaml.load(response.content, Loader=yaml.Loader)
    assert yaml_content == {"dummy_metadata": True}


def test_simple_agent_func_calls(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test Func[simple1]
    response = client.post(
        "/simple1", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "Simple response 1", "embeds": {}},
        "error": None,
    }
    mock_token_verifier.assert_called_once_with(
        "fixie-test-token", dummy_agent._jwks_client, dummy_agent._allowed_agent_id
    )

    # Test Func[simple2]
    response = client.post(
        "/simple2", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "Simple response 2", "embeds": {}},
        "error": None,
    }

    # Test Func[custom]
    response = client.post(
        "/custom", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "Simple response custom", "embeds": {}},
        "error": None,
    }

    # Test Func[corpus]
    response = client.post(
        "/corpus", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == {
        "message": {"text": "Success", "embeds": {}},
        "error": None,
    }

    # Test non-existing Func[] returns 404: Not Found
    response = client.post(
        "/simple3", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 404

    # Test Func[simple1] with bad arguments returns 422: Unprocessable Entity
    response = client.post(
        "/simple1", json={"message": {"ttt": "Howdy"}}, headers=headers
    )
    assert response.status_code == 422

    # Test Func[__init__] 404: Not Found
    response = client.post(
        "/__init__", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 404

    # Test Func without auth header returns 401: Unauthorized
    response = client.post("/simple1", json={"message": {"text": "Howdy"}})
    assert response.status_code == 403


def test_agent_corpus_func_calls(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}
    request_body = CORPUS_REQUEST_JSON

    # Test load_corpus
    response = client.post("/corpus/load_corpus", json=request_body, headers=headers)
    assert response.status_code == 200
    json = response.json()
    assert json == CORPUS_RESPONSE_JSON
    mock_token_verifier.assert_called_once_with(
        "fixie-test-token", dummy_agent._jwks_client, dummy_agent._allowed_agent_id
    )

    # Test load_corpus_custom_name
    response = client.post(
        "/corpus/custom_name_corpus_load", json=request_body, headers=headers
    )
    assert response.status_code == 200
    json = response.json()
    assert json == CORPUS_RESPONSE_JSON

    # Test load_corpus_existing_fn_name
    response = client.post("/corpus/simple1", json=request_body, headers=headers)
    assert response.status_code == 200
    json = response.json()
    assert json == CORPUS_RESPONSE_JSON

    # Test non-existing corpus func returns 404: Not Found
    response = client.post("/corpus/non-existing", json=request_body, headers=headers)
    assert response.status_code == 404

    # Note: corpus functions will never return a 422 since there are no
    # required fields.

    # Test Func[__init__] as corpus function returns 404: Not Found
    response = client.post("/corpus/__init__", json=request_body, headers=headers)
    assert response.status_code == 404

    # Test load_corpus without auth header returns 401: Unauthorized
    response = client.post("/corpus/load_corpus", json=request_body)
    assert response.status_code == 403


def test_simple_agent_func_failure(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test Func[unhandled_exception]
    response = client.post(
        "/unhandled_exception", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 500
    json = response.json()
    assert json["message"]["text"] == exceptions.UNHANDLED_EXCEPTION_RESPONSE_TEXT
    assert "ValueError: Func failed!\n" in json["error"]["details"]["traceback"]


def test_simple_agent_func_custom_failure(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test Func[unhandled_exception]
    response = client.post(
        "/agent_exception", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 400
    json = response.json()
    assert json["message"]["text"] == "Agent exception!"
    assert json["error"]["details"]["detail"] == 1


def test_corpus_func_failure(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test unhandled_corpus_exception
    response = client.post(
        "/corpus/unhandled_corpus_exception", json=CORPUS_REQUEST_JSON, headers=headers
    )
    assert response.status_code == 500
    json = response.json()
    assert json["message"]["text"] == exceptions.UNHANDLED_EXCEPTION_RESPONSE_TEXT
    assert "ValueError: Corpus func failed!\n" in json["error"]["details"]["traceback"]


def test_corpus_agent_exception(dummy_agent, mock_token_verifier):
    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}

    # Test corpus_agent_exception
    response = client.post(
        "/corpus/corpus_agent_exception", json=CORPUS_REQUEST_JSON, headers=headers
    )
    assert response.status_code == 400
    json = response.json()
    assert json["message"]["text"] == "Corpus agent exception!"
    assert json["error"]["details"]["detail"] == 1


def test_registering_func_with_custom_name(dummy_agent):
    dummy_agent.register_func(lambda query: "1", func_name="name1")
    dummy_agent.register_func(lambda query: "2", func_name="name2")
    dummy_agent.register_func(lambda query: "3", func_name="name3")

    def invoke_func(name: str):
        responses = dummy_agent._funcs[name](
            fixieai.AgentQuery(fixieai.Message("test")), "agent-id"
        )
        return next(iter(responses)).message.text

    assert invoke_func("name1") == "1"
    assert invoke_func("name2") == "2"
    assert invoke_func("name3") == "3"


def test_invalid_token(dummy_agent, mock_token_verifier):
    mock_token_verifier.return_value = None

    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}
    response = client.post(
        "/simple1", json={"message": {"text": "Howdy"}}, headers=headers
    )
    assert response.status_code == 403


def test_invalid_token_corpus_request(dummy_agent, mock_token_verifier):
    mock_token_verifier.return_value = None

    client = testclient.TestClient(dummy_agent.app(), raise_server_exceptions=False)
    headers = {"Authorization": "Bearer fixie-test-token"}
    response = client.post(
        "/corpus/load_corpus", json=CORPUS_REQUEST_JSON, headers=headers
    )
    assert response.status_code == 403
