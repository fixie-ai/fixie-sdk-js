# Document Question and Answering

## Overview

One of the most popular use cases for LLMs is doing question answering (Q/A) over a large corpus of unstructured data.

Fixie makes it possible to quickly build Q/A Agents by automatically crawling a set of developer-provided URLs, generating embeddings, chunking the data, and storing it inside of a Vector Database for efficient retrieval.

To get started, let's look at a simple [CodeShotAgent](/agents.md/#CodeShotAgent) that answers questions about Python:

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
