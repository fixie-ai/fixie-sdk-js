from __future__ import annotations

import enum
import re
from typing import TYPE_CHECKING, Callable, Optional, Set

if TYPE_CHECKING:
    from fixieai.agents import code_shot

ODD_NUM_POUNDS = re.compile(r"(?<!#)(##)*#(?!#)")
EMBED_REF = re.compile(ODD_NUM_POUNDS.pattern + r"(?P<embed_key>\w+)(?!\w)")


def strip_prompt_lines(agent: code_shot.CodeShotAgent):
    """Strips all prompt lines."""
    agent.base_prompt = _strip_all_lines(agent.base_prompt)
    for i, fewshot in enumerate(agent.few_shots):
        agent.few_shots[i] = _strip_all_lines(fewshot)


def validate_code_shot_agent(agent: code_shot.CodeShotAgent):
    """A client-side validation of few_shots and agent."""
    _validate_base_prompt(agent.base_prompt)
    for fewshot in agent.few_shots:
        _validate_few_shot_prompt(
            fewshot, agent.conversational, agent.is_valid_func_name
        )


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
    AGENT_SAYS = re.compile(r"^Agent\[(?P<agent_id>\w+)] says:")
    FUNC_SAYS = re.compile(r"^Func\[(?P<func_name>\w+)] says:")
    ASK_AGENT = re.compile(r"^Ask Agent\[(?P<agent_id>\w+)]:")
    ASK_FUNC = re.compile(r"^Ask Func\[(?P<func_name>\w+)]:")
    RESPONSE = re.compile(r"^A:")
    NO_PATTERN: None = None

    @classmethod
    def match(cls, line: str) -> Optional[re.Match[str]]:
        """Returns a match from a FewshotLinePattern for a given line, or None if nothing matched."""
        if "\n" in line:
            raise ValueError(
                "Cannot get the pattern for a multi-line text. Patterns must be "
                "extracted one line at a time."
            )
        matches = [
            match
            for prompt_pattern in cls
            if prompt_pattern is not cls.NO_PATTERN
            and (match := prompt_pattern.value.match(line))
        ]
        if len(matches) > 1:
            raise RuntimeError(
                f"More than one pattern ({list(FewshotLinePattern(match.re) for match in matches)}) matched the line {line!r}."
            )
        elif len(matches) == 0:
            return None

        match = matches[0]
        if match.re is cls.QUERY.value:
            if match.end() == len(line):
                raise ValueError("A 'Q:' line cannot end without a query.")

        assert isinstance(match, re.Match)
        return match


def _validate_few_shot_prompt(
    prompt: str, conversational: bool, is_valid_func_name: Callable[[str], bool]
):
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
    pattern_matches = [FewshotLinePattern.match(line) for line in lines]
    _assert(
        pattern_matches[0] is not None
        and pattern_matches[0].re is FewshotLinePattern.QUERY.value,
        "Fewshot must start with a 'Q:'",
        prompt,
    )
    last_pattern = FewshotLinePattern.QUERY
    known_embeds: Set[str] = set()

    for i, (match, line) in enumerate(zip(pattern_matches, lines)):
        pattern = (
            FewshotLinePattern(match.re)
            if match is not None
            else FewshotLinePattern.NO_PATTERN
        )

        if pattern is FewshotLinePattern.ASK_AGENT:
            assert match is not None
            next_match = (
                pattern_matches[i + 1] if i + 1 < len(pattern_matches) else None
            )
            _assert(
                next_match is not None
                and next_match.re is FewshotLinePattern.AGENT_SAYS.value
                and match.group("agent_id") == next_match.group("agent_id"),
                "Each 'Ask Agent' line must be immediately followed by an 'Agent says' line that references the same ",
                prompt,
            )

        if pattern is FewshotLinePattern.ASK_FUNC:
            assert match is not None
            next_match = (
                pattern_matches[i + 1] if i + 1 < len(pattern_matches) else None
            )
            _assert(
                next_match is not None
                and next_match.re is FewshotLinePattern.FUNC_SAYS.value
                and match.group("func_name") == next_match.group("func_name"),
                "Each 'Ask Func' line must be immediately followed by an 'Func says' line that references the same func.",
                prompt,
            )
            _assert(
                is_valid_func_name(match.group("func_name")),
                "Each 'Ask Func' line must reference a valid func name.",
                prompt,
            )

        if pattern is FewshotLinePattern.FUNC_SAYS:
            assert match is not None
            _assert(
                is_valid_func_name(match.group("func_name")),
                "Each 'Func says' line must reference a valid func name.",
                prompt,
            )

        if pattern is not FewshotLinePattern.NO_PATTERN:
            last_pattern = pattern

        # Check that any embeds are valid.
        for embed_match in EMBED_REF.finditer(line):
            key = embed_match.group("embed_key")
            if key not in known_embeds:
                _assert(
                    last_pattern
                    not in (
                        FewshotLinePattern.ASK_AGENT,
                        FewshotLinePattern.ASK_FUNC,
                        FewshotLinePattern.RESPONSE,
                    ),
                    "New embeds may not be introduced in Ask Agent, Ask Func, or A: lines.",
                    prompt,
                )
                known_embeds.add(key)

    _assert(
        last_pattern is FewshotLinePattern.RESPONSE,
        f"Fewshot must end with a 'A:' pattern, but it ends with {last_pattern}",
        prompt,
    )

    # Check that there's Q: and A: lines are interleaved.
    all_qa_lines = [
        "Q"
        if match.re is FewshotLinePattern.QUERY.value
        else "A"
        if match.re is FewshotLinePattern.RESPONSE.value
        else "x"
        for match in pattern_matches
        if match is not None
    ]
    qa_str = "".join(all_qa_lines)

    if conversational:
        _assert(
            re.match("^(Qx*A)+$", qa_str) is not None,
            "Each fewshot must have interleaved Q: and A: patterns when conversational=True",
            prompt,
        )
    else:
        _assert(
            re.match("^Qx*A$", qa_str) is not None,
            "Each fewshot must have exactly one Q: and A: pattern when conversational=False",
            prompt,
        )


def _assert(condition: bool, msg: str, prompt: str):
    if not condition:
        raise ValueError(f"{msg} in few-shot prompt: {prompt!r}.")
