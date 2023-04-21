from typing import Generator, Iterable, List, Optional

import pytest

import fixieai
from fixieai.agents import agent_func
from fixieai.agents import api
from fixieai.agents import oauth


@pytest.fixture
def oauth_params():
    return oauth.OAuthParams(
        client_id="dummy",
        client_secret="dummy",
        auth_uri="dummy",
        token_uri="dummy",
        scopes=["dummy"],
    )


def test_create_from_python_type_coercion(oauth_params):
    def valid(
        expected: Optional[Iterable[api.AgentResponse]] = None,
        oauth_params=None,
        default_message_type=str,
        allow_generator=False,
    ):
        def _wrap(f):
            normalized = agent_func.AgentFunc.create(
                f, oauth_params, default_message_type, allow_generator
            )
            query_text = "Test query"
            result = normalized(
                api.AgentQuery(api.Message(text=query_text)), "test-agent-id"
            )

            expected_results = (
                [api.AgentResponse(api.Message(query_text))]
                if expected is None
                else list(expected)
            )
            assert expected_results == list(result)

        return _wrap

    @valid(expected=[api.AgentResponse(api.Message("PASS"))])
    def no_arguments():
        return "PASS"

    @valid()
    def untyped_query(query):
        return query

    @valid()
    def untyped_query_userstorage(query, user_storage):
        assert isinstance(user_storage, fixieai.UserStorage)
        return query

    @valid(oauth_params=oauth_params)
    def untyped_query_userstorage_oauth(query, user_storage, oauth_handler):
        assert isinstance(user_storage, fixieai.UserStorage)
        assert isinstance(oauth_handler, fixieai.OAuthHandler)
        return query

    @valid()
    def untyped_userstorage_query(user_storage, query):
        assert isinstance(user_storage, fixieai.UserStorage)
        return query

    @valid()
    def only_argument_query(query):
        return query

    @valid()
    def only_argument_assumed_to_be_query(x):
        return x

    @valid()
    def first_argument_assumed_to_be_query(x, user_storage):
        assert isinstance(user_storage, fixieai.UserStorage)
        return x

    @valid()
    def query_valid_type_annotation_str(x: str):
        assert isinstance(x, str)
        return x

    @valid()
    def query_valid_type_annotation_message(x: fixieai.Message):
        assert isinstance(x, fixieai.Message)
        return x.text

    @valid()
    def query_valid_type_annotation_query(x: fixieai.AgentQuery):
        assert isinstance(x, fixieai.AgentQuery)
        return x.message.text

    @valid()
    def valid_return_type_str(query: str) -> str:
        return query

    @valid()
    def valid_return_type_message(query: api.Message) -> api.Message:
        assert isinstance(query, api.Message)
        return query

    @valid()
    def valid_return_type_response(query: api.Message) -> api.AgentResponse:
        assert isinstance(query, api.Message)
        return api.AgentResponse(query)

    @valid(
        [api.AgentResponse(api.Message("1")), api.AgentResponse(api.Message("2"))],
        allow_generator=True,
    )
    def valid_return_type_response_generator(
        query: api.Message,
    ) -> api.AgentResponseGenerator:
        yield api.AgentResponse(api.Message("1"))
        yield api.AgentResponse(api.Message("2"))

    @valid(
        [api.AgentResponse(api.Message("1")), api.AgentResponse(api.Message("2"))],
        allow_generator=True,
    )
    def valid_return_type_str_generator(query) -> Generator:
        yield "1"
        yield "2"

    @valid(
        [api.AgentResponse(api.Message("1")), api.AgentResponse(api.Message("2"))],
        allow_generator=True,
    )
    def valid_return_type_str_generator_generic(query) -> Generator[str, None, None]:
        yield "1"
        yield "2"

    @valid(
        [api.AgentResponse(api.Message("1")), api.AgentResponse(api.Message("2"))],
        allow_generator=True,
    )
    def valid_return_type_str_iterable_generic(query) -> Iterable[str]:
        return ["1", "2"]

    @valid(
        [api.AgentResponse(api.Message("1")), api.AgentResponse(api.Message("2"))],
        allow_generator=True,
    )
    def valid_return_type_str_list_generic(query) -> List[str]:
        return ["1", "2"]

    @valid()
    def types_take_precedence(query: fixieai.UserStorage, user_storage: str):
        assert isinstance(query, fixieai.UserStorage)
        assert isinstance(user_storage, str)
        return user_storage

    @valid(default_message_type=str)
    def default_type_str(query):
        assert isinstance(query, str)
        return query

    @valid(default_message_type=fixieai.Message)
    def default_type_message(query):
        assert isinstance(query, fixieai.Message)
        return query

    @valid(default_message_type=fixieai.AgentQuery)
    def default_type_query(query):
        assert isinstance(query, fixieai.AgentQuery)
        return query.message

    def invalid(
        exception_type,
        match: str,
        oauth_params=None,
        default_message_type=str,
        allow_generator=False,
    ):
        def _wrap(f):
            with pytest.raises(exception_type, match=match):
                agent_func.AgentFunc.create(
                    f, oauth_params, default_message_type, allow_generator
                )

        return _wrap

    @invalid(TypeError, "unknown parameters")
    def extra_argument_is_invalid(query, x):
        ...

    @invalid(TypeError, "unknown parameters")
    def too_many_arguments(a, b, c):
        ...

    @invalid(TypeError, "query")
    def query_invalid_type_annotation(query: int):
        ...

    @invalid(TypeError, "oauth_params")
    def oauth_handler_requires_oauth_params(query, user_storage, oauth_handler):
        ...

    @invalid(TypeError, "variable args")
    def varargs_not_allowed(*query):
        ...

    @invalid(TypeError, "variable args")
    def kwargs_not_allowed(**query):
        ...

    @invalid(TypeError, "returns", allow_generator=False)
    def generator_not_always_allowed(query: str) -> api.AgentResponseGenerator:
        yield api.AgentResponse(api.Message(query))

    @invalid(TypeError, "returns", allow_generator=True)
    def generator_invalid_generic() -> Generator[int, None, None]:
        yield 1
