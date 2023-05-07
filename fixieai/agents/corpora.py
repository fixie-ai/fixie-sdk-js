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
    """URLs to load documents from. A trailing wildcard (e.g., https://example.com/*),
    can be used to load all documents from a site."""

    exclude_patterns: Optional[List[str]] = None
    """A list of wildcard patterns to exclude from crawled URLs (e.g., */no_crawl/*)."""

    auth_token_func: Optional[str] = None
    loader: Optional[DocumentLoader] = None
