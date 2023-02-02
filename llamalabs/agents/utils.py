import enum
import inspect
import re
from typing import TYPE_CHECKING, Callable, Union
from unittest import mock

if TYPE_CHECKING:
    from llamalabs.agents import api
    from llamalabs.agents import code_shot
else:
    api = mock.MagicMock()
    code_shot = mock.MagicMock()


def strip_fewshot_lines(agent: code_shot.CodeShotAgent):
    """Strips all fewshot lines."""
    for i, fewshot in enumerate(agent.FEWSHOTS):
        agent.FEWSHOTS[i] = _strip_fewshot(fewshot)


def validate_codeshot_agent(agent: code_shot.CodeShotAgent):
    """A client-side validation of fewshots and agent."""
    for fewshot in agent.FEWSHOTS:
        _validate_few_shot_prompt(fewshot)


def get_pyfunc(
    agent: code_shot.CodeShotAgent, func_name: str
) -> Callable[[api.AgentQuery], Union[str, api.Message, api.AgentResponse]]:
    """Gets the method Func[func_name] from `agents` and validates it."""
    if func_name.startswith("_"):
        raise ValueError(f"Func[{func_name}] is not allowed to be called.")

    func = getattr(agent, func_name)

    # Validate that func has a proper api.api.AgentQuery -> api.api.AgentResponse signature.
    if not inspect.ismethod(func):
        raise TypeError(
            f"Attribute {func_name!r} is not a method, but it's of type {type(func)!r}."
        )
    signature = inspect.signature(func)
    params = signature.parameters
    if len(params) != 1:
        raise TypeError(
            f"Expected Func[{func_name}] to get a single api.AgentQuery argument but it "
            f"gets {len(params)}."
        )
    param_type = list(params.values())[0].annotation
    return_type = signature.return_annotation
    if param_type is inspect.Signature.empty or return_type is inspect.Signature.empty:
        raise TypeError(
            f"Expected Func[{func_name}] to set type annotation for its argument and "
            "return type."
        )
    # Delayed import to avoid circular dependency
    from llamalabs.agents import api

    # TODO(hessam): Allow return_type to be a Union of the allowed types.
    if param_type is not api.AgentQuery or return_type not in (
        api.AgentResponse,
        api.Message,
        str,
    ):
        raise TypeError(
            f"Expected Func[{func_name}] to get a single api.AgentQuery "
            "argument and output an api.AgentResponse but it gets "
            f"{list(params.values())} and returns {return_type}."
        )
    return func


def _strip_fewshot(fewshot: str) -> str:
    fewshot = fewshot.strip()
    return "\n".join(line.strip() for line in fewshot.splitlines())


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
