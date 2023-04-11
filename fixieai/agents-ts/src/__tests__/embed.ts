import { Embed } from '../embed';

it('returns binary data', async () => {
  const embed = Embed.fromBase64('text/plain', 'hello world');
  expect((await embed.getDataAsBinary()).toString('utf-8')).toEqual('hello world');
  expect(embed.loadDataAsText()).resolves.toEqual('hello world');
});

it('returns binary data when the input is binary', async () => {
  const buffer = Buffer.from('hello world', 'utf-8');
  const embed = Embed.fromBinary('text/plain', buffer);
  expect((await embed.getDataAsBinary()).toString('utf-8')).toEqual(buffer.toString('utf-8'));
});
