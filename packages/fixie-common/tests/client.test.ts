/** Unit tests for client.ts. */

import { FixieClientBase } from '../src/client';

describe('Create client', () => {
  it('Should have the correct URL', () => {
    const client = new FixieClientBase({ url: 'https://example.com' });
    expect(client.url).toBe('https://example.com');
  });
});
