import base64
import dataclasses
from typing import List, Optional

import dataclasses_json.core
from deprecated import deprecated
from pydantic import dataclasses as pydantic_dataclasses


@pydantic_dataclasses.dataclass
class CorpusRequest(dataclasses_json.DataClassJsonMixin):
    """A request for some piece of the agent's corpus.

    In addition to returning documents, each response may expand the corpus
    space in one or both of two dimensions: new partitions and next pages.

    Partitions are non-overlapping subsets of a corpus which may be loaded in
    parallel by Fixie. A response's new partitions will be ignored if
    previously included in another response.

    When a response includes a page of documents, that page may indicate that
    another page is available in the same partition. Pages are always loaded
    serially in order. The partition is completed when a response has a page
    with no next_page_token.

    Agents will always receive a first request with the default (unnamed)
    partition and no page_token. Subsequent requests depend on prior responses
    and will always include at least one of those fields.

    Examples:
        Simple handful of documents:

            When receiving the initial request, the agent responds with a page
            of documents. This could include a next_page_token for more
            documents in the single default partition if needed.

        Web crawl:

            Each URL corresponds to a partition and the agent never returns
            tokens. The initial response only includes partitions, one for each
            root URL to crawl. Each subsequent request includes the partition
            (the URL) and the corresponding response contains a page with a
            single document - the resource at that URL. If the document links
            to other resources that should be included in the corpus, the
            response also contains those URLs as new partitions. The process
            repeats for all partitions until there are no known incomplete
            partitions or until crawl limits are reached.

        Database:

            Consider a database with a parent table keyed by parent_id and an
            interleaved child table keyed by (parent_id, child_id) whose rows
            correspond to corpus documents. This agent will use tokens that
            encode a read timestamp (for consistency) and an offset to be used
            in combination with a static page size.

            Upon receiving the initial CorpusRequest, the agent chooses a
            commit timestamp to use for all reads and returns a partition for
            each parent_id along with a first_page_token indicating the chosen
            read timestamp and an offset of 0.

            For each partition, the agent then receives requests with the
            partition (a parent_id) and a page token (the read timestamp and
            offest). It responds with documents corresponding to the next page
            size child rows within the given parent. If more children exist,
            the response includes a next_page_token with the same read
            timestamp and an incremented offset. This repeats until there are
            no more children, at which point the response has no
            next_page_token and the partition is complete.

            Note: Including multiple parent_ids in each partition would also
                work and would be an effective way to limit parallelism if
                desired.

    Attributes:
        partition: The partition of the corpus that should be read. This will
            be empty for the initial request, indicating the default partition.
            For subsequent requests, it will either be the name of a partition
            returned by a previous request or empty if the default partition
            contains multiple pages for this agent.
        page_token: A token for paginating results within a corpus partition.
            If present, this will be echoed from a previous response.
    """

    partition: Optional[str] = None
    page_token: Optional[str] = None


@pydantic_dataclasses.dataclass
class CorpusPartition:
    """An identifier for a subset of a corpus, along with an optional
    token to use when loading its first page. Each partition will only be
    loaded once during a single crawl. If multiple responses include the same
    partition, the token of the first received response will be used."""

    partition: str
    first_page_token: Optional[str] = None


@pydantic_dataclasses.dataclass
class CorpusDocument:
    """Some meaningful item of data from a corpus. This could be an HTML page,
    a PDF, or a raw string of text (among others). Fixie will handle parsing
    and chunking this document so that appropriately sized chunks can be
    included in LLM requests.

    Note: If custom parsing is desired, agents are free to implement their own
    parsing to return documents with text/plain mime_types instead of whatever
    they fetch natively. Fixie will not alter text/plain documents prior to
    chunking."""

    source_name: str
    content: bytes = dataclasses.field(
        metadata=dataclasses_json.config(
            encoder=lambda c: base64.b64encode(c).decode(),
            decoder=lambda c: base64.b64decode(c.encode()),
        )
    )
    encoding: str = "UTF-8"
    mime_type: str = "text/plain"

    @property
    def text(self) -> str:
        return self.content.decode(self.encoding)


@pydantic_dataclasses.dataclass
class CorpusPage:
    """A page of CorpusDocuments. In addition to the documents themselves, a
    page may include a continuation token for fetching the next page (in the
    same partition). Omitting a token implies that this is the last page."""

    documents: List[CorpusDocument]
    next_page_token: Optional[str] = None


@pydantic_dataclasses.dataclass
class CorpusResponse(dataclasses_json.DataClassJsonMixin):
    """A response to a CorpusRequest. See CorpusRequest for details."""

    partitions: Optional[List[CorpusPartition]] = None
    page: Optional[CorpusPage] = None


@pydantic_dataclasses.dataclass
class CustomCorpus:
    """A custom corpus for a Fixie CodeShot Agent. This uses a registered
    corpus func to load documents from an arbitrary source."""

    func_name: str


@deprecated(reason="Use register_corpus_func for custom document loading.")
@pydantic_dataclasses.dataclass
class DocumentLoader:
    """Deprecated. This doesn't do anything."""

    name: str


@pydantic_dataclasses.dataclass
class UrlDocumentCorpus:
    """URL Document corpus for a Fixie CodeShot Agent."""

    urls: List[str]
    """URLs to load documents from. A trailing wildcard (e.g., https://example.com/*),
    can be used to load all documents from a site."""

    exclude_patterns: Optional[List[str]] = None
    """A list of wildcard patterns to exclude from crawled URLs (e.g., */no_crawl/*)."""

    auth_token_func: Optional[str] = None

    loader: Optional[DocumentLoader] = None  # Deprecated.


DocumentCorpus = UrlDocumentCorpus  # Deprecated: Prefer UrlDocumentCorpus
