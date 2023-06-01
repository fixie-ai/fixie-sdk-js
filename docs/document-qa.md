# Document Question and Answering

## Overview

One of the most popular use cases for LLMs is doing question answering (Q/A) over a large corpus of unstructured data.

Fixie makes it possible to quickly build Q/A Agents by automatically crawling a set of developer-provided URLs, generating embeddings, chunking the data, and storing it inside of a Vector Database for efficient retrieval. For data sets that aren't easily available to a web crawler, Fixie also supports [custom corpora](#custom-corpora).

To get started, let's look at a simple [CodeShotAgent](/agents/#CodeShotAgent) that answers questions about Python:

```python
import fixieai

BASE_PROMPT = """I am a helpful assistant that can answer questions \
  about Python. I try to be as concise as possible \
  in my answers while still effectively answering the question."""

URLS = [
    "https://docs.python.org/3.11/*"
]

DOCUMENTS = [fixieai.DocumentCorpus(urls=URLS)]
agent = fixieai.CodeShotAgent(BASE_PROMPT, [], DOCUMENTS, conversational=True)
```

You'll notice that we created a new variable, `URLS`, that contains an array of webpages that we would like Fixie to automatically crawl. (See [Specifying URLs](#specifying-urls) for detail about how this works.)

Once we have our `URLS`, we instantiate a new `CodeShotAgent` with our `BASE_PROMPT`, an empty Few Shot array, a set of `DOCUMENTS` that point to our URLs, and whether we want a `conversational` Agent (conversational agents keep previous questions and answers in memory, so we recommend it for Q/A Agents).

When a `DocumentCorpus` is provided, FewShots are optional (hence the empty array that we passed in). If you need FewShots, see [Using Fewshots with Docs](#using-fewshots-with-docs).

Once ready, you can deploy your agent using `fixie deploy`. The agent will deploy immediately, but will not answer questions until indexing is complete. See [Monitoring Indexing Status](#monitoring-indexing-status) for more.

## Specifying URLs

You can specify URLs in two forms: static or wildcard.

| Kind     | Example                                                   | Use-case                                         |
| -------- | --------------------------------------------------------- | ------------------------------------------------ |
| Static   | `https://docs.python.org/3.11/tutorial/introduction.html` | Index only the specified URL.                    |
| Wildcard | `https://docs.python.org/3.11/*`                          | Index the specified URL and all of its subpages. |

When you specify a wildcard, Fixie will:

- Crawl the site, respecting a [sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview#:~:text=A%20sitemap%20is%20a%20file,crawl%20your%20site%20more%20efficiently.) if it exists.
- Limit the crawl to pages that start with the specified pattern. For example:

```
# Wildcard pattern: https://foo.com/bar/*

https://foo.com/bar/index.html

    Links to -> https://foo.com/bar/nested/index.html
    Links to -> https://foo.com/bar/deep/nested/index.html
        These pages will be indexed.

    Links to -> https://foo.com/index.html
        This page will not be indexed, because it doesn't start with the wildcard pattern.

    Links to -> https://different-domain.com
        This page will not be indexed, because it doesn't start with the wildcard pattern.
```

## Accessing Private URLs with Bearer Token

In many cases, the set of documents that you want to access will be behind authentication. Fixie supports passing in a `Bearer` token with each request. To enable this, you'll define a new function that returns a token that will be passed in to the `Authorization` HTTP header as follows: `Authorization: Bearer {your_token}`.

Here's an example:

```python
import fixieai

BASE_PROMPT = """I can answer questions from secret, non-public docs."""

URLS = [
    "https://private.myamazingsite.com/*"
]

CORPORA = [fixieai.DocumentCorpus(urls=URLS, auth_token_func="auth")]
agent = fixieai.CodeShotAgent(BASE_PROMPT, [], CORPORA, conversational=True)

# Don't forget to call @agent.register_func on your auth function
@agent.register_func
def auth():
    return "12345"
```

## Custom Corpora

If web crawling isn't a good fit for your use case, you can register a corpus function to load documents any way you need to. This allows for reading a private database for example.

```python
import fixieai
from datetime import datetime

BASE_PROMPT = """I am a helpful assistant that can answer questions \
  about the contents of MyDatabase. I try to be as concise as possible \
  in my answers while still effectively answering the question."""

agents = fixieai.CodeShotAgent(BASE_PROMPT, [], conversational=True)

class MyDatabasePageToken:
    read_timestamp: datetime
    offset: int = 0

    def encode(self) -> str:
        # Serialize to a utf-8 encoded string
        pass

    @staticmethod
    def decode(token: str) -> MyDatabasePageToken:
        # Undo encode
        pass

PAGE_SIZE = 20

@agent.register_corpus_func
def load_my_database(request: fixieai.CorpusRequest) -> fixie.CorpusResponse:
    if not request.partition:
        initial_read = db_client.read("MyTopLevelTable", keys_only=True)
        first_page_token = MyDatabasePageToken(initial_read.timestamp())
        partition_names = [row.key for row in initial_read.results]
        return fixieai.CorpusResponse(partitions=[fixieai.CorpusPartition(name, first_page_token) for name in partition_names])
    else:
        top_level_key = request.partition
        token = MyDatabasePageToken.decode(request.page_token)
        offset = token.offset * PAGE_SIZE
        read = db_client.read("MyNestedTable", parent_key=top_level_key, limit=PAGE_SIZE, offset=offset, read_timestamp=token.read_timestamp)
        docs = [fixie.CorpusDocument(row.key, row.my_column) for row in read.results]
        if read.has_more_results():
            token.offset += 1
            next_page_token = token.encode()
        else:
            next_page_token = None
        return fixieai.CorpusResponse(page=fixieai.CorpusPage(docs, next_page_token))
```

This example assumes an easily partitionable database with columns that already have text data, but there are way more options available. See [CorpusRequest][fixieai.agents.corpora.CorpusRequest] for more details.

## Using Fewshots with Docs

By default, you don't need to use FewShots with Docs. Fixie's automatic behavior will produce a Q/A agent that meets the general need.

If using FewShots, you'll need to manually tell Fixie to query the corpus using the built-in `fixie_query_corpus` function.

Here's an example for an Agent that has access to docs about the primary plot points from HBO's Silicon Valley:

```python
FEW_SHOTS = """
Q: Who was Gilfoyle played by?
Ask Func[fixie_query_corpus]: Who was Gilfoyle played by?
Func[fixie_query_corpus] says: Gilfoyle was played by Martin Starr.
A: Gilfoyle was played by Martin Starr.
"""
```

## Excluding documents during crawl

There are some cases where you don't want Fixie to crawl certain wepages or types of webpages when using the `*` wildcard pattern. In order to do this, you can supply a set of `exclude_patterns`, which are an array of regular expressions:

```python
import fixieai

BASE_PROMPT = """I answer questions based on the supplied corpus"""

URLS = [
    "https://public.myamazingsite.com/*"
]

# Don't index any PDFs
EXCLUDE_PATTERNS = [
  "*.pdf",
]

CORPORA = [fixieai.DocumentCorpus(urls=URLS, exclude_patterns=EXCLUDE_PATTERNS)]
agent = fixieai.CodeShotAgent(BASE_PROMPT, [], CORPORA, conversational=True)
```

## Supported file types

| File Type | Extension                        |
| --------- | -------------------------------- |
| Documents | `.doc`, `.docx`, `.ppt`, `.pptx` |
| PDFs      | `.pdf`                           |
| Webpages  | `.html`                          |
| Text      | `.md`, `.txt`, `.rtf`,           |
| Email     | `.msg`, `.eml`                   |
| E-Books   | `.epub`                          |

## Monitoring Indexing Status

You can check the indexing status of your Agent by asking it any question. Your agent will return `I'm still starting up. Please try again in a few minutes` if it's still indexing. Indexing can take upwards of a few hours for very large data sets (smaller sets can be done in just a few minutes).

Coming soon is the ability to see and manage your indexing directly on [the Fixie dev console](https://app.fixie.ai).
