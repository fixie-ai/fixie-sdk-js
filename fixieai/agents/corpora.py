import base64
import dataclasses
from typing import List, Optional

import dataclasses_json.core
from deprecated import deprecated
from pydantic import dataclasses as pydantic_dataclasses


@pydantic_dataclasses.dataclass
class CorpusRequest(dataclasses_json.DataClassJsonMixin):
    """A request for some piece of the agent's corpus. This should yield a
    CORPUS_LOAD type response.

    Request flow:
        For each request, agents should return:
            a set of partitions for the corpus, optionally with
                continuation_tokens for the first page of each;
            a page of documents from the corpus (from the given partition if
                present), optionally with a continuation_token for the next
                page;
            or both
        Agents will initially receive an empty CorpusRequest. Subsequent
        requests will depend on the responses of prior requests. Each unique
        returned partition will result in a request with that partition and the
        first continuation_token associated with that partition (if any). Each
        page of documents with a continuation_token will result in a request
        with the same partition and the returned continuation_token. A
        partition is done when a response includes a page of documents with no
        continuation_token.
        While each of the requests for an individual partition must be serial,
        each partition may be loaded in parallel.

    Examples:
        Simple handful of documents:
            When receiving the initial request, the agent responds with a page
            of documents. (This could include a continuation_token for more
            documents in the single default partition if needed.)
        Web crawl:
            Each URL corresponds to a partition and the agent never returns
            continuation_tokens. The initial request returns only partitions,
            one for each root URL to crawl. Each subsequent request includes
            the partition (the URL) and returns a page with a single document
            (the resource at the URL) and no continuation_token along with
            additional partitions for all referenced URLs.
        Database:
            Consider a database with a parent table keyed by parent_id and an
            interleaved child table keyed by (parent_id, child_id) whose rows
            correspond to corpus documents. This agent will use
            continuation_tokens that encode a read timestamp (for consistency)
            and an offset to be used in combination with a static page size.

            Upon receiving the initial CorpusRequest, the agent chooses a
            commit timestamp to use for all reads and returns a partition for
            each parent_id (or key ranges on parent_id if preferable) along
            with a continuation_token indicating the chosen read timestamp.

            For each partition, the agent receives an initial request with the
            partition and continuation_token and responds with documents
            corresponding to the first page size child rows for the partition.
            If more children exist, the response includes a continuation_token
            with the same read timestamp and an offset of 1 for the next page.

            Within each partition, each response with a continuation_token
            causes the the agent to receive an additional request with that
            continuation_token and the same partition. This repeats until all
            child rows in the partition have been returned.

    Args:
        partition: The partition of the corpus that should be read. This will
            be empty for the initial request. For subsequent requests, it will
            either be a partition returned by a previous request or empty if
            the agent only has one default partition.
        continuation_token: A token for paginating results within a corpus
            partition. If present, this will be echoed from a previous
            response.
    """

    partition: Optional[str] = None
    continuation_token: Optional[str] = None


@pydantic_dataclasses.dataclass
class CorpusPartition:
    """An identifier for a subset of a corpus, along with an optional
    continuation_token to use when loading its first page. Each partition will
    only be loaded once during a single crawl. If multiple responses include
    the same partition, the continuation_token of the first received response
    will be used.

    Note:
        Continuation tokens must be encodable as UTF-8."""

    partition: str
    continuation_token: Optional[str] = None


@pydantic_dataclasses.dataclass
class CorpusDocument:
    """Some meaningful item of data from a corpus. This could be an HTML page,
    a Word document, or a raw string of text (among others). Fixie will handle
    parsing and chunking this document so that appropriately sized chunks can
    be included in LLM requests."""

    source_name: str
    content: bytes = dataclasses.field(
        metadata=dataclasses_json.config(
            encoder=lambda c: base64.urlsafe_b64encode(c).decode(),
            decoder=lambda c: base64.urlsafe_b64decode(c.encode()),
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
    same partition). Omitting a continuation token implies that this is the
    last page.

    Note:
        Continuation tokens must be encodable as UTF-8.
    """

    documents: List[CorpusDocument]
    continuation_token: Optional[str] = None


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
