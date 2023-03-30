import dataclasses
import os

import fastapi
import pytest
import yaml
from fastapi import testclient

import fixieai
from fixieai import agents
from fixieai.agents import agent_base
from fixieai.agents import code_shot

agent_id = "dummy"
BASE_PROMPT = "I am a simple dummy agent."
FEW_SHOTS = """
Q: Sample query 1
Ask Func[simple1]: Simple argument
Func[simple1] says: Simple response
A: Simple final response

Q: Sample query 2
Ask Func[simple2]: Simple argument
Func[simple2] says: Simple response
A: Simple final response
"""
CORPORA = [
    agents.DocumentCorpus(
        urls=["http://example.com/doc1.txt"], loader=agents.DocumentLoader("text")
    ),
]


@pytest.fixture(autouse=True)
def mock_token_verifier(mocker):
    return mocker.patch.object(
        agent_base.VerifiedTokenClaims,
        "from_token",
        return_value=agent_base.VerifiedTokenClaims(agent_id="fake agent id"),
    )


@pytest.fixture
def dummy_code_shot_agent(mocker):
    mocker.patch.dict(os.environ, {"FIXIE_ALLOWED_AGENT_ID": "fake agent id"})
    agent = agents.CodeShotAgent(
        BASE_PROMPT,
        FEW_SHOTS,
        CORPORA,
        conversational=False,
        oauth_params=fixieai.OAuthParams(
            client_id="dummy",
            client_secret="dummy",
            auth_uri="dummy",
            token_uri="dummy",
            scopes=["dummy"],
        ),
        llm_settings=agents.LlmSettings(
            model="test-model", temperature=0.42, maximum_tokens=42
        ),
    )

    return agent


def test_code_shot_handshake(dummy_code_shot_agent, mocker):
    fast_api = fastapi.FastAPI()
    fast_api.include_router(dummy_code_shot_agent.api_router())
    client = testclient.TestClient(fast_api)

    response = client.get("/", headers={"Authorization": "Bearer fixie-test-token"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/yaml"
    yaml_content = yaml.load(response.content, Loader=yaml.Loader)
    assert yaml_content == {
        "base_prompt": dummy_code_shot_agent.base_prompt,
        "few_shots": dummy_code_shot_agent.few_shots,
        "corpora": [dataclasses.asdict(c) for c in dummy_code_shot_agent.corpora],
        "conversational": dummy_code_shot_agent.conversational,
        "response_model": {
            "model": dummy_code_shot_agent.llm_settings.model,
            "temperature": dummy_code_shot_agent.llm_settings.temperature,
            "maximum_tokens": dummy_code_shot_agent.llm_settings.maximum_tokens,
        },
        "type": "code_shot",
    }


def test_split_few_shots():
    few_shots_list = code_shot._split_few_shots(FEW_SHOTS)
    assert few_shots_list == [
        """
Q: Sample query 1
Ask Func[simple1]: Simple argument
Func[simple1] says: Simple response
A: Simple final response""",
        """Q: Sample query 2
Ask Func[simple2]: Simple argument
Func[simple2] says: Simple response
A: Simple final response""",
    ]
