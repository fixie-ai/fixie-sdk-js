from typing import List, Literal, Optional, Union

from pydantic import dataclasses as pydantic_dataclasses

from fixieai.agents import corpora as fixie_corpora
from fixieai.agents import llm_settings


@pydantic_dataclasses.dataclass
class StandaloneAgentMetadata:
    """Metadata for a Fixie Standalone Agent."""

    sample_queries: Optional[List[str]] = None
    type: Literal["standalone"] = "standalone"


@pydantic_dataclasses.dataclass
class CodeShotAgentMetadata:
    """Metadata for a Fixie CodeShot Agent."""

    base_prompt: str
    few_shots: List[str]
    corpora: Optional[List[fixie_corpora.DocumentCorpus]] = None
    conversational: bool = False
    response_model: Optional[llm_settings.LlmSettings] = None
    type: Literal["code_shot"] = "code_shot"


Metadata = Union[StandaloneAgentMetadata, CodeShotAgentMetadata]
