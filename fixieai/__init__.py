import importlib.metadata

from fixieai.agents import AgentQuery
from fixieai.agents import AgentResponse
from fixieai.agents import CodeShotAgent
from fixieai.agents import DocumentCorpus
from fixieai.agents import DocumentLoader
from fixieai.agents import Embed
from fixieai.agents import LlmSettings
from fixieai.agents import Message
from fixieai.agents import OAuthHandler
from fixieai.agents import OAuthParams
from fixieai.agents import StandaloneAgent
from fixieai.agents import UserStorage
from fixieai.client import FixieClient
from fixieai.client import get_agents
from fixieai.client import get_client
from fixieai.client import get_embeds
from fixieai.client import query

__all__ = [
    "AgentQuery",
    "AgentResponse",
    "Embed",
    "Message",
    "CodeShotAgent",
    "StandaloneAgent",
    "DocumentCorpus",
    "DocumentLoader",
    "LlmSettings",
    "OAuthParams",
    "OAuthHandler",
    "UserStorage",
    "FixieClient",
    "get_agents",
    "get_client",
    "get_embeds",
    "query",
]

__version__ = importlib.metadata.version(__name__)
