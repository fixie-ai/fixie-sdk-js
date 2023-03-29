from typing import List, Optional, Union

from fixieai.agents import agent_base
from fixieai.agents import corpora
from fixieai.agents import llm_settings
from fixieai.agents import metadata
from fixieai.agents import oauth
from fixieai.agents import utils


class CodeShotAgent(agent_base.AgentBase):
    """A CodeShot agent.

    To make a CodeShot agent, simply pass a BASE_PROMPT and FEW_SHOTS:

        BASE_PROMPT = "A summary of what this agent does; how it does it; and its
        personality"

        FEW_SHOTS = '''
        Q: <Sample query that this agent supports>
        A: <Desired response for this query>

        Q: <Another sample query>
        A: <Desired response for this query>
        '''

        agent = CodeShotAgent(BASE_PROMPT, FEW_SHOTS)

    You can have FEW_SHOTS as a single string of all your few-shots separated by 2 new
    lines, or as an explicit list of one few-shot per index.

    Your few-shots may reach out to other Agents in the fixie ecosystem by
    "Ask Agent[agent_id]: <query to pass>", or reach out to some python functions
    by "Ask Func[func_name]: <query to pass>".

    There are a series of default runtime `Func`s provided by the platform available for
    your agents to consume. For a full list of default runtime `Func`s, refer to:
        http://docs.fixie.ai/XXX

    You may also need to write your own python functions here to be consumed by your
    agent. To make a function accessible by an agent, you'd need to register it by
    `@agent.register_func`. Example:

        @agent.register_func
        def func_name(query: fixieai.Message) -> ReturnType:
            ...

        , where ReturnType is one of `str`, `fixieai.Message`, or `fixie.AgentResponse`.

    Note that in the above, we are using the decorator `@agent.register_func` to
    register this function with the agent instance we just created.

    To check out the default `Func`s that are provided in Fixie, see:
        http://docs.fixie.ai/XXX

    """

    def __init__(
        self,
        base_prompt: str,
        few_shots: Union[str, List[str]],
        corpora: Optional[List[corpora.DocumentCorpus]] = None,
        conversational: bool = False,
        oauth_params: Optional[oauth.OAuthParams] = None,
        llm_settings: Optional[llm_settings.LlmSettings] = None,
    ):
        super().__init__(oauth_params)

        if isinstance(few_shots, str):
            few_shots = _split_few_shots(few_shots)

        self.base_prompt = base_prompt
        self.few_shots = few_shots
        self.corpora = corpora
        self.conversational = conversational
        self.llm_settings = llm_settings

        utils.strip_prompt_lines(self)

    def metadata(self) -> metadata.Metadata:
        return metadata.CodeShotAgentMetadata(
            self.base_prompt,
            self.few_shots,
            self.corpora,
            self.conversational,
            self.llm_settings,
        )

    def validate(self):
        utils.validate_code_shot_agent(self)


def _split_few_shots(few_shots: str) -> List[str]:
    """Split a long string of all few-shots into a list of few-shot strings."""
    # First, strip all lines to remove bad spaces.
    few_shots = "\n".join(line.strip() for line in few_shots.splitlines())
    # Then, split by "\n\nQ:".
    few_shot_splits = few_shots.split("\n\nQ:")
    few_shot_splits = [few_shot_splits[0]] + [
        "Q:" + few_shot for few_shot in few_shot_splits[1:]
    ]
    return few_shot_splits
