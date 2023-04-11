import { Embed } from '../embed';

it.only('returns binary data', () => {
  const embed = Embed.fromText('text/plain', 'hello world');
  expect(embed.getDataAsBinary().toString('utf-8')).toEqual('hello world');
  expect(embed.getDataAsText()).toEqual('hello world');
});

it('returns binary data when the input is binary', () => {
  const buffer = Buffer.from('hello world', 'utf-8');
  const embed = Embed.fromBinary('text/plain', buffer);
  expect(embed.getDataAsBinary().toString('utf-8')).toEqual(buffer.toString('utf-8'));
});
