import enum
import inspect
import re
from typing import TYPE_CHECKING, Callable, get_type_hints
from unittest import mock

if TYPE_CHECKING:
    from fixieai.agents import api
    from fixieai.agents import code_shot
else:
    api = mock.MagicMock()
    code_shot = mock.MagicMock()


def strip_prompt_lines(agent_metadata: code_shot.AgentMetadata):
    """Strips all prompt lines."""
    agent_metadata.base_prompt = _strip_all_lines(agent_metadata.base_prompt)
    for i, fewshot in enumerate(agent_metadata.few_shots):
        agent_metadata.few_shots[i] = _strip_all_lines(fewshot)


def validate_code_shot_agent(agent_metadata: code_shot.AgentMetadata):
    """A client-side validation of few_shots and agent."""
    _validate_base_prompt(agent_metadata.base_prompt)
    for fewshot in agent_metadata.few_shots:
        _validate_few_shot_prompt(fewshot)


def validate_registered_pyfunc(func: Callable, agent: code_shot.CodeShotAgent):
    """Validates `func`'s signature to be a valid CodeShot Func.

    Args:
        func: The function to be validated.
        agent: The CodeShotAgent that this func is going to be registered for.
    """
    # Delayed import to avoid circular dependency
    from fixieai.agents import api
    from fixieai.agents import oauth
    from fixieai.agents import user_storage

    ALLOWED_FUNC_PARAMS = {
        "query": api.Message,
        "user_storage": user_storage.UserStorage,
        "oauth_handler": oauth.OAuthHandler,
    }

    # Validate that func is a function type.
    if not inspect.isfunction(func):
        raise TypeError(
            f"Registered function {func!r} is not a function, but a {type(func)!r}."
        )
    signature = inspect.signature(func)
    func_name = func.__name__
    params = signature.parameters

    # Validate that there are not var args (*args or **kwargs).
    if any(
        param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL)
        for param in params.values()
    ):
        raise TypeError(
            f"Registered function {func_name} cannot accept variable args: {params!r}."
        )

    # Validate that all argument names are known.
    unknown_params = set(params.keys()) - set(ALLOWED_FUNC_PARAMS.keys())
    if unknown_params:
        raise TypeError(
            f"Registered function {func_name} gets unknown arguments {unknown_params}. "
            f"List of allowed Func arguments are {list(ALLOWED_FUNC_PARAMS.keys())}."
        )

    # Check the type annotations match what's expected, if func is type annotated.
    type_hints = get_type_hints(func)
    for arg_name, arg_type in ALLOWED_FUNC_PARAMS.items():
        if arg_name in type_hints and type_hints[arg_name] != arg_type:
            raise TypeError(
                f"Expected argument {arg_name!r} to be of type {arg_type!r}, but it's "
                f"typed as {type_hints[arg_name]!r}."
            )
    if "return" in type_hints and type_hints["return"] not in (
        api.AgentResponse,
        api.Message,
        str,
    ):
        raise TypeError(
            f"Expected registered function to return an AgentResponse, a Message, "
            f"or str but it returns {type_hints['return']}."
        )

    # Some custom checks.
    if "oauth_handler" in params and agent.oauth_params is None:
        raise TypeError(
            f"Function {func_name} who accepts 'oauth_handler' as an argument cannot "
            f"be registered with agent {agent!r} who hasn't set 'oauth_params' in its "
            "constructor."
        )

    return func


def _strip_all_lines(prompt: str) -> str:
    prompt = prompt.strip()
    return "\n".join(line.strip() for line in prompt.splitlines())


def _validate_base_prompt(base_prompt: str):
    if base_prompt.endswith("\n") or base_prompt.startswith("\n"):
        raise ValueError(
            "base_prompt should not start or end in newlines. "
            f"base_prompt={base_prompt!r}."
        )
    whitespaces = (" ", "\t", "\r")
    prompt_lines = base_prompt.split("\n")
    bad_lines = [
        line
        for line in prompt_lines
        if line.startswith(whitespaces) or line.endswith(whitespaces)
    ]
    if bad_lines:
        raise ValueError(
            f"Some lines in the base prompt start or end in whitespaces: {bad_lines!r}."
        )


class FewshotLinePattern(enum.Enum):
    QUERY = re.compile(r"^Q:")
    AGENT_SAYS = re.compile(r"^Agent\[\w+] says:")
    FUNC_SAYS = re.compile(r"^Func\[\w+] says:")
    ASK_AGENT = re.compile(r"^Ask Agent\[\w+]:")
    ASK_FUNC = re.compile(r"^Ask Func\[\w+]:")
    RESPONSE = re.compile(r"^A:")
    NO_PATTERN: None = None

    @classmethod
    def pattern(cls, line: str) -> "FewshotLinePattern":
        """Returns the matched PromptPattern for a given line."""
        if "\n" in line:
            raise ValueError(
                "Cannot get the pattern for a multi-line text. Patterns must be "
                "extracted one line at a time."
            )
        pattern_matches = [
            prompt_pattern
            for prompt_pattern in cls
            if prompt_pattern is not cls.NO_PATTERN and prompt_pattern.value.match(line)
        ]
        if len(pattern_matches) > 1:
            raise RuntimeError(
                f"More than one pattern ({pattern_matches}) matched the line {line!r}."
            )
        elif len(pattern_matches) == 1:
            return pattern_matches[0]
        else:
            return cls.NO_PATTERN


def _validate_few_shot_prompt(prompt: str):
    """Validates 'prompt' as a correctly formatted few shot prompt."""
    lines = prompt.splitlines(False)

    # Check that no line starts or ends in a whitespace.
    whitespaces = (" ", "\t", "\r")
    bad_lines = [
        line
        for line in lines
        if line.startswith(whitespaces) or line.endswith(whitespaces)
    ]
    _assert(
        not bad_lines,
        f"Some lines in the fewshot start or end in whitespaces: {bad_lines!r}.",
        prompt,
    )

    # Check that it doesn't end with newline
    _assert(not prompt.endswith("\n"), "Fewshot ends with newline.", prompt)

    # Check that fewshot starts with a Q:, ends in an A:, and a Func says and Agent
    # says follows every Ask Func and Ask Agent.
    lines_patterns = [FewshotLinePattern.pattern(line) for line in lines]
    _assert(
        lines_patterns[0] is FewshotLinePattern.QUERY,
        "Fewshot must start with a 'Q:'",
        prompt,
    )
    last_pattern = FewshotLinePattern.QUERY
    for i, pattern in enumerate(lines_patterns):
        if pattern is FewshotLinePattern.ASK_AGENT:
            _assert(
                i + 1 < len(lines_patterns)
                and lines_patterns[i + 1] is FewshotLinePattern.AGENT_SAYS,
                "Each 'Ask Agent' line must be followed by an 'Agent says' line.",
                prompt,
            )
        if pattern is FewshotLinePattern.ASK_FUNC:
            _assert(
                i + 1 < len(lines_patterns)
                and lines_patterns[i + 1] is FewshotLinePattern.FUNC_SAYS,
                "Each 'Ask Func' line must be followed by an 'Func says' line.",
                prompt,
            )
        if pattern is not FewshotLinePattern.NO_PATTERN:
            last_pattern = pattern
    _assert(
        last_pattern is FewshotLinePattern.RESPONSE,
        f"Fewshot must end with a 'A:' pattern, but it ends with {last_pattern}",
        prompt,
    )

    # Check that there's Q: and A: lines are interleaved.
    all_qa_lines = [
        "Q" if pattern is FewshotLinePattern.QUERY else "A"
        for pattern in lines_patterns
        if pattern in (FewshotLinePattern.QUERY, FewshotLinePattern.RESPONSE)
    ]
    qa_str = "".join(all_qa_lines)
    _assert(
        qa_str.replace("QA", "") == "",
        "Q: and A: lines must be interleaved in fewshot.",
        prompt,
    )


def _assert(condition: bool, msg: str, prompt: str):
    if not condition:
        raise ValueError(f"{msg} in few-shot prompt: {prompt!r}.")
