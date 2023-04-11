import { Embed } from '../embed';

test('returns binary data', async () => {
  const embed = Embed.fromBase64('text/plain', 'hello world');
  expect((await embed.getDataAsBinary()).toString('utf-8')).toBe('hello world');
  await expect(embed.loadDataAsText()).resolves.toBe('hello world');
});

test('returns binary data when the input is binary', async () => {
  const buffer = Buffer.from('hello world', 'utf-8');
  const embed = Embed.fromBinary('text/plain', buffer);
  expect((await embed.getDataAsBinary()).toString('utf-8')).toBe(buffer.toString('utf-8'));
});
