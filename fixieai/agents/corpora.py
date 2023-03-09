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
    loader: Optional[DocumentLoader] = None
