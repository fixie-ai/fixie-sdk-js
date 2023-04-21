from __future__ import annotations

import collections.abc
import inspect
import typing
from typing import (
    Any,
    Callable,
    Iterable,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
    get_type_hints,
)

from fixieai.agents import api
from fixieai.agents import oauth
from fixieai.agents import user_storage

# An ArgumentMapper converts a query+agent ID into a supported func argument (e.g. "query" or "user_storage")
ArgumentMapper = Callable[[api.AgentQuery, str], Any]

# BoundArgumentMapper is an ArgumentMapper that has been bound to a named parameter.
BoundArgumentMapper = Tuple[str, ArgumentMapper]


class AgentFunc:
    """A Python function that can be invoked by Fixie.

    Wrapped functions can take up to three arguments:

    1. A message or query of type: `str`, `api.AgentMessage`, or `api.AgentQuery`;
       name: "query", or "message"; or the first parameter if no other rules apply.
    2. A user storage object of type `user_storage.UserStorage` or name "user_storage".
    3. An OAuth handler of type `oauth.OAuthHandler` or name "oauth_handler".

    The semantics of each parameter are inferred by type annotation or name/position if no
    type annotations are present.
    """

    def __init__(
        self,
        impl: Callable,
        argument_mappers: Iterable[BoundArgumentMapper],
        allow_multiple_responses: bool,
    ):
        self._impl = impl
        self._argument_mappers = tuple(argument_mappers)
        self._allow_multiple_responses = allow_multiple_responses

    def __call__(
        self, agent_query: api.AgentQuery, agent_id: str
    ) -> Iterable[api.AgentResponse]:
        kwargs = {}
        for name, mapper in self._argument_mappers:
            kwargs[name] = mapper(agent_query, agent_id)

        result = self._impl(**kwargs)
        return _adapt_func_result(result, self._allow_multiple_responses)

    @classmethod
    def create(
        cls,
        func: Callable,
        oauth_params: Optional[oauth.OAuthParams],
        default_message_type: Union[Type[str], Type[api.Message], Type[api.AgentQuery]],
        allow_generator: bool,
    ) -> AgentFunc:
        """Constructs an AgentFunc from a Python function.

        Args:
            func: the Python function to wrap
            oauth_params: optional OAuthParams, required if the func requires an OAuthHandler
            default_message_type: the message type to default to if type annotations aren't present
            allow_generator: whether the function is allowed to return multiple responses
        """

        if not inspect.isfunction(func):
            raise TypeError(
                f"Registered function {func!r} is not a function, but a {type(func)!r}."
            )
        signature = inspect.signature(func)
        func_name = func.__name__
        params = signature.parameters

        # Validate that there are no var args (*args or **kwargs).
        if any(
            param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL)
            for param in params.values()
        ):
            raise TypeError(
                f"Registered function {func_name} cannot accept variable args: {params!r}."
            )

        # Using the signature (parameter names and type annotations) of the provided function,
        # figure out which parameters correspond to which of the possible values (message,
        # user storage, OAuth handler).
        #
        # Because the types of each of the possible values are distinct, we prioritize type
        # annotations if present, but fall back to well-known names.
        #
        # For each of the possible values we'll try to construct a `BoundArgumentMapper`
        # that can be used at runtime to set the arguments.

        # Ensure every parameter is used exactly once.
        unbound_parameter_names = set(params.keys())

        # Try to bind a query/message mapper.
        typed_message_mappers = {
            api.AgentQuery: lambda query, agent_id: query,
            api.Message: lambda query, agent_id: query.message,
            str: lambda query, agent_id: query.message.text,
        }
        bound_message_mapper = _bind_argument_mapper(
            func,
            unbound_parameter_names=unbound_parameter_names,
            mappers_by_type_or_name=(
                *typed_message_mappers.items(),
                ("query", typed_message_mappers[default_message_type]),
                ("message", typed_message_mappers[default_message_type]),
            ),
        )

        # Try to bind a UserStorage mapper.
        user_storage_mapper = lambda query, agent_id: user_storage.UserStorage(
            query, agent_id
        )
        bound_user_storage_mapper = _bind_argument_mapper(
            func,
            unbound_parameter_names=unbound_parameter_names,
            mappers_by_type_or_name=(
                (user_storage.UserStorage, user_storage_mapper),
                ("user_storage", user_storage_mapper),
            ),
        )

        # Try to bind an OAuthHandler mapper.
        oauth_mapper = lambda query, agent_id: oauth_params and oauth.OAuthHandler(
            oauth_params, query, agent_id
        )
        bound_oauth_mapper = _bind_argument_mapper(
            func,
            unbound_parameter_names=unbound_parameter_names,
            mappers_by_type_or_name=(
                (oauth.OAuthHandler, oauth_mapper),
                ("oauth_handler", oauth_mapper),
            ),
        )
        if bound_oauth_mapper is not None and oauth_params is None:
            raise TypeError(
                f"Function {func_name} that accepts 'oauth_handler' as an argument cannot "
                f"be registered with an agent that hasn't set 'oauth_params' in its "
                "constructor."
            )

        # If we didn't get a message handler and there's a single untyped argument
        # remaining and it's the first parameter, treat it as a message.
        #
        # def f(x): allowed, x is a message
        # def f(x, user_storage): allowed, x is a message
        # def f(user_storage, x): not allowed
        # def f(x, y): not allowed
        # def f(x: int): not allowed
        type_hints = get_type_hints(func)
        if bound_message_mapper is None and len(unbound_parameter_names) == 1:
            remaining_parameter_name = next(iter(unbound_parameter_names))
            first_parameter_name = next(iter(params.keys()))
            if (
                first_parameter_name == remaining_parameter_name
                and remaining_parameter_name not in type_hints
            ):
                bound_message_mapper = (
                    remaining_parameter_name,
                    typed_message_mappers[default_message_type],
                )
                unbound_parameter_names.remove(remaining_parameter_name)

        # All parameters should be accounted for.
        if len(unbound_parameter_names) > 0:
            raise TypeError(
                f"Registered function {func_name} had unknown parameters: {unbound_parameter_names}"
            )

        # Validate that the return type annotation is compatible.
        return_type = get_type_hints(func).get("return")
        if return_type is not None:
            VALID_RETURN_TYPES = (api.AgentResponse, api.Message, str)
            is_return_type_valid = return_type in VALID_RETURN_TYPES

            if allow_generator and not is_return_type_valid:
                # If allow_generator is set, the function can return any Iterable
                # of an allowed type.
                origin_type = typing.get_origin(return_type)
                if origin_type is not None and issubclass(
                    origin_type, collections.abc.Iterable
                ):
                    args = typing.get_args(return_type)
                    is_return_type_valid = (args == ()) or args[0] in VALID_RETURN_TYPES

            if not is_return_type_valid:
                raise TypeError(
                    f"Expected registered function to return an AgentResponse, a Message, "
                    f"or str but it returns {return_type}."
                )

        return AgentFunc(
            func,
            [
                bound_mapper
                for bound_mapper in (
                    bound_message_mapper,
                    bound_user_storage_mapper,
                    bound_oauth_mapper,
                )
                if bound_mapper is not None
            ],
            allow_generator,
        )


def _adapt_func_result(
    result: Any, allow_multiple: bool
) -> Iterable[api.AgentResponse]:
    """Adapts any allowed func return type into an Iterable of AgentResponses."""

    if isinstance(result, api.AgentResponse):
        yield result
    elif isinstance(result, api.Message):
        yield api.AgentResponse(message=result)
    elif isinstance(result, str):
        yield api.AgentResponse(message=api.Message(result))
    elif isinstance(result, collections.abc.Iterable):
        for value in result:
            yield from _adapt_func_result(value, allow_multiple)

            if not allow_multiple:
                break
    else:
        raise TypeError(
            f"The func result was type {type(result)}, but must be a str, Message, AgentResponse, or iterable."
        )


def _bind_argument_mapper(
    func: Callable,
    unbound_parameter_names: Set[str],
    mappers_by_type_or_name: Iterable[Tuple[Union[type, str], ArgumentMapper]],
) -> Optional[BoundArgumentMapper]:
    """Attempts to select an argument name to which a mapper can be bound.

    If a mapper is bound, the name will be removed from `unbound_parameter_names`.
    """

    type_hints = get_type_hints(func)

    for type_or_name, mapper in mappers_by_type_or_name:
        for name in unbound_parameter_names:
            if isinstance(type_or_name, type) and type_hints.get(name) == type_or_name:
                unbound_parameter_names.remove(name)
                return name, mapper
            elif (
                name not in type_hints
                and isinstance(type_or_name, str)
                and name == type_or_name
            ):
                unbound_parameter_names.remove(name)
                return name, mapper

    return None
