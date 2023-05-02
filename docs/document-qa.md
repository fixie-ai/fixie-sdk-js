# Document Question and Answering

## Overview

One of the most popular use cases for LLMs is doing Q/A over a large corpus of unstructured data.

Fixie makes it possible to quickly build Q/A Agents by automatically crawling a set of developer-provided URLs, generating embeddings, chunking the data, and storing it inside of a Vector Database for efficient retrieval.

To understand how to get started, let's look at a quick example of a [CodeShotAgent](/agents.md/#codeshotagent) that is designed to answer questions about Fixie:

```python
import fixieai

BASE_PROMPT = """I am a helpful assistant that can answer questions \
  about building on top of Fixie.ai. I try to be as concise as possible \
  in my answers while still effectively answering the question."""

URLS = [
    "https://docs.fixie.ai/*"
]

DOCUMENTS = [fixieai.DocumentCorpus(urls=URLS)]
agent = fixieai.CodeShotAgent(BASE_PROMPT, [], DOCUMENTS, conversational=True)
```

You'll notice that we created a new variable, `URLS`, that contains an array of webpages that we would like Fixie to automatically crawl. Notice the `*` at the end of the Fixie docs URL. This tells Fixie that we want to not just crawl the single page, but we want to crawl **all** webpages found on that base URL (similar to how a search engine works).

Fixie also supports indexing individual pages, but the `*` can be useful when you have hundreds of pages that need to be ingested. If you need to exclude certain files (or types of files), see [Excluding documents during crawl](#excluding-documents-during-crawl).

> Note: By default, Fixie will crawl up to 1,000 documents for each wildcard URL. If you need more, [get in touch](mailto:hello@fixie.ai).

Once we have our `URLS`, we instantiate a new `CodeShotAgent` with our `BASE_PROMPT`, an empty Few Shot array, a set of `DOCUMENTS` that point to our URLs, and whether we want a `conversational` Agent (conversational agents keep previus questions in memory, so we recommend it for Q/A Agents).

When a `DocumentCorpus` is provided, FewShots are optional (hence the empty array that we passed in). If you need FewShots, see [Using Fewshots with Docs](#using-fewshots-with-docs).

Once ready, you can deploy your agent using `fixie deploy`. Note that depending on the size and number of documents, indexing can take some time. While indexing is in progress, your agent will deploy but will always return `I'm still starting up. Please try again in a few minutes.` See [Monitoring Indexing Status](#monitoring-indexing-status) for more.

## Accessing Private URLs

In many cases, the set of documents that you want to access will be behind authentication. Fixie supports passing in a `Bearer` token with each request.

To enable this, you'll define a new function that returns a token that will be passed in to the `Authorization` header as follows: `Authorization: Bearer {your_token}`.

Here's an example:

```python
import fixieai

BASE_PROMPT = """I can answer questions from secret, non-public docs."""

URLS = [
    "https://private.myamazingsite.com/*"
]

def Auth():
    return "12345"

CORPORA = [fixieai.DocumentCorpus(urls=URLS, auth_token_func="Auth")]
agent = fixieai.CodeShotAgent(BASE_PROMPT, [], CORPORA, conversational=True)
```

## Using Fewshots with Docs

In most cases, we recommend not using FewShots for Q/A use cases, as Fixie will take care of things for you. That said, in some cases (e.g., combining with other functions, exerting more control, etc) you may wish to use FewShots.

If using FewShots, you'll need to manually tell Fixie to query the corpus using the built-in `fixie_query_corpus` function.

Here's an example for an Agent that was trained on the primary plot points from HBO's Silicon Valley:

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

This feature is coming soon!
