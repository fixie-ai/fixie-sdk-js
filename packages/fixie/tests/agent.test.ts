/** Unit tests for agent.ts. */

import { jest, afterEach, describe, expect, it } from '@jest/globals';
import { FixieAgent } from '../src/agent';

describe('FixieAgent config file tests', () => {
  it('LoadConfig reads agent config', async () => {
    const config = FixieAgent.LoadConfig('tests/fixtures/test-agent');
    expect(config.handle).toBe('test-agent');
    expect(config.description).toBe('Test agent description');
    expect(config.moreInfoUrl).toBe('http://fake.url.com/');
  });
  it('LoadConfig ignores unknown fields', async () => {
    const config = FixieAgent.LoadConfig('tests/fixtures/test-agent-ignore-fields');
    expect(config.handle).toBe('test-agent');
    expect(config.description).toBe('Test agent description');
    expect(config.moreInfoUrl).toBe('http://fake.url.com/');
  });
});
