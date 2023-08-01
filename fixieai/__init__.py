import importlib.metadata

from fixieai.agents import AgentQuery
from fixieai.agents import AgentResponse
from fixieai.agents import CodeShotAgent
from fixieai.agents import CorpusDocument
from fixieai.agents import CorpusPage
from fixieai.agents import CorpusPartition
from fixieai.agents import CorpusRequest
from fixieai.agents import CorpusResponse
from fixieai.agents import DocumentCorpus
from fixieai.agents import Embed
from fixieai.agents import LlmSettings
from fixieai.agents import Message
from fixieai.agents import OAuthHandler
from fixieai.agents import OAuthParams
from fixieai.agents import StandaloneAgent
from fixieai.agents import UrlDocumentCorpus
from fixieai.agents import UserStorage
from fixieai.client import FixieClient
from fixieai.client import FixieEnvironment
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
    "CorpusDocument",
    "CorpusPage",
    "CorpusPartition",
    "CorpusRequest",
    "CorpusResponse",
    "DocumentCorpus",
    "StandaloneAgent",
    "LlmSettings",
    "OAuthParams",
    "OAuthHandler",
    "UrlDocumentCorpus",
    "UserStorage",
    "FixieClient",
    "FixieEnvironment",
    "get_agents",
    "get_client",
    "get_embeds",
    "query",
]

__version__ = importlib.metadata.version(__name__)
