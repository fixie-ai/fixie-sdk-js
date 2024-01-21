/** Unit tests for client.ts. */

import { jest, afterEach, describe, expect, it } from '@jest/globals';
import { FixieClientBase } from '../src/client';

/** This function mocks out 'fetch' to return the given response. */
const mockFetch = (response: any) => {
  const mock = jest
    .fn<typeof global.fetch>()
    .mockImplementation((_input: RequestInfo | URL, _init?: RequestInit | undefined) => {
      return Promise.resolve({
        ok: true,
        json: () => response,
      } as Response);
    });
  global.fetch = mock;
  return mock;
};

describe('FixieClientBase user tests', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('Returns correct userInfo result', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    mockFetch({
      user: {
        userId: 'fake-user-id',
        email: 'bob@bob.com',
        fullName: 'Bob McBeef',
      },
    });

    const userInfo = await client.userInfo();
    expect(userInfo.userId).toBe('fake-user-id');
    expect(userInfo.email).toBe('bob@bob.com');
    expect(userInfo.fullName).toBe('Bob McBeef');
  });

  it('Sends correct request for updating user', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({
      user: {
        userId: 'fake-user-id',
        email: 'bob@bob.com',
        fullName: 'Frank McBeef',
      },
    });

    const userInfo = await client.updateUser({ fullName: 'Frank McBeef' });
    expect(userInfo.userId).toBe('fake-user-id');
    expect(userInfo.email).toBe('bob@bob.com');
    expect(userInfo.fullName).toBe('Frank McBeef');

    expect(mock.mock.calls.length).toBe(1);
    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/users/me');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('PUT');
    expect(mock.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        user: {
          fullName: 'Frank McBeef',
        },
        updateMask: 'fullName',
      })
    );
  });
});

describe('FixieClientBase corpus tests', () => {
  afterEach(() => {
    jest.clearAllMocks();
  });

  it('getCorpus returns correct result', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({
      corpus: {
        corpusId: 'fake-corpus-id',
        description: 'Fake Corpus description',
      },
    });

    const corpus = (await client.getCorpus('fake-corpus-id')) as { corpus: { corpusId: string; description: string } };
    expect(corpus.corpus.corpusId).toBe('fake-corpus-id');
    expect(corpus.corpus.description).toBe('Fake Corpus description');

    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/corpora/fake-corpus-id');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('GET');
  });

  it('createCorpus returns correct result', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({
      corpus: {
        corpusId: 'fake-corpus-id',
        description: 'Fake Corpus description',
      },
    });

    const corpus = (await client.createCorpus({
      name: 'Test Corpus',
      description: 'Fake Corpus description',
      teamId: 'fake-team-id',
    })) as { corpus: { corpusId: string; description: string } };
    expect(corpus.corpus.corpusId).toBe('fake-corpus-id');
    expect(corpus.corpus.description).toBe('Fake Corpus description');

    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/corpora');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('POST');
    expect(mock.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        teamId: 'fake-team-id',
        corpus: {
          display_name: 'Test Corpus',
          description: 'Fake Corpus description',
        },
      })
    );
  });

  it('updateCorpus returns correct result', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({
      corpus: {
        corpusId: 'fake-corpus-id',
        description: 'Fake Corpus description',
      },
    });

    const corpus = (await client.updateCorpus({
      corpusId: 'fake-corpus-id',
      displayName: 'Test Corpus',
    })) as { corpus: { corpusId: string; description: string } };
    expect(corpus.corpus.corpusId).toBe('fake-corpus-id');
    expect(corpus.corpus.description).toBe('Fake Corpus description');

    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/corpora/fake-corpus-id');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('PUT');
    expect(mock.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        corpus: {
          corpus_id: 'fake-corpus-id',
          displayName: 'Test Corpus',
        },
        updateMask: 'displayName',
      })
    );
  });

  it('queryCorpus returns correct result', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({ results: [] });

    const result = (await client.queryCorpus({
      corpusId: 'fake-corpus-id',
      query: 'Some random query',
      maxChunks: 25,
    })) as { results: any[] };

    expect(result.results).toStrictEqual([]);

    expect(mock.mock.calls[0][0].toString()).toStrictEqual(
      'https://fake.api.fixie.ai/api/v1/corpora/fake-corpus-id:query'
    );
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('POST');
    expect(mock.mock.calls[0][1]?.body).toBe(
      JSON.stringify({
        corpus_id: 'fake-corpus-id',
        query: 'Some random query',
        max_chunks: 25,
      })
    );
  });

  it('deleteCorpus returns correct result', async () => {
    const client = new FixieClientBase({ url: 'https://fake.api.fixie.ai' });
    const mock = mockFetch({});

    await client.deleteCorpus({
      corpusId: 'fake-corpus-id',
    });
    expect(mock.mock.calls[0][0].toString()).toStrictEqual('https://fake.api.fixie.ai/api/v1/corpora/fake-corpus-id');
    expect(mock.mock.calls[0][1]?.method).toStrictEqual('DELETE');
  });
});
