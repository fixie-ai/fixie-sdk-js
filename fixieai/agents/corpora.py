from typing import List, Optional

from pydantic import dataclasses as pydantic_dataclasses


@pydantic_dataclasses.dataclass
class DocumentLoader:
    """Document loader for a Fixie CodeShot Agent."""

    name: str


@pydantic_dataclasses.dataclass
class DocumentCorpus:
    """Document corpus for a Fixie CodeShot Agent."""

    urls: List[str]
    exclude_patterns: Optional[List[str]] = None
    auth_token_func: Optional[str] = None
    loader: Optional[DocumentLoader] = None
