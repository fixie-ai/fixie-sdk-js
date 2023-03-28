import pytest

from fixieai import constants
from fixieai.cli.auth import user_config

EXAMPLE_URL = "https://example.fixie.ai"


@pytest.fixture
def config_without_environment():
    return user_config.UserConfig.from_dict(
        {
            "fixie_api_key": "default-token",
        }
    )


@pytest.fixture
def config_with_environment():
    return user_config.UserConfig.from_dict(
        {
            "fixie_api_key": "default-token",
            "environment_auth_tokens": [
                {"url": EXAMPLE_URL, "auth_token": "environment-token"}
            ],
        }
    )


def test_user_config_no_env(config_without_environment):
    assert config_without_environment.auth_token == "default-token"


def test_user_config_no_matching_env(config_with_environment):
    assert config_with_environment.auth_token == "default-token"


def test_user_config_matching_env(mocker, config_with_environment):
    mocker.patch.object(constants, "FIXIE_API_URL", EXAMPLE_URL)
    assert config_with_environment.auth_token == "environment-token"


def test_set_token_multiple_environments(mocker, config_without_environment):
    url_1, token_1 = "https://test1.fixie.ai", "token1"
    mocker.patch.object(constants, "FIXIE_API_URL", url_1)
    config_without_environment.auth_token = token_1
    assert config_without_environment.auth_token == token_1

    url_2, token_2 = "https://test2.fixie.ai", "token2"
    mocker.patch.object(constants, "FIXIE_API_URL", url_2)
    config_without_environment.auth_token = token_2
    assert config_without_environment.auth_token == token_2

    # If we switch the URL back we should get the first token
    mocker.patch.object(constants, "FIXIE_API_URL", url_1)
    assert config_without_environment.auth_token == token_1


def test_config_to_from_yaml(config_with_environment, config_without_environment):
    assert (
        user_config.UserConfig.from_yaml(config_without_environment.to_yaml())
        == config_without_environment
    )
    assert (
        user_config.UserConfig.from_yaml(config_with_environment.to_yaml())
        == config_with_environment
    )
