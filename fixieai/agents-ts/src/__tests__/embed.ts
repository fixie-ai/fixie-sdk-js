import { Embed } from '../embed';

it('returns binary data', () => {
  const buffer = Buffer.from('hello world', 'utf-8');
  const embed = Embed.fromBase64('image/webp', buffer.toString('base64'));
  expect(embed.getDataAsBinary()).toEqual(buffer);
});
