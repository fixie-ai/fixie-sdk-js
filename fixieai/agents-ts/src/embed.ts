import got from 'got';

function isBase64String(str: string) {
  // Lifted from https://github.com/Hexagon/base64/blob/f83c673ded56edf4976c123d7c0cf40e46910452/src/base64.js#L164.
  return /^[-A-Za-z0-9+/]*={0,3}$/.test(str);
}

/**
 * A binary object attached to a Message.
 */
export class Embed {
  constructor(
    /**
     * The MIME content type of the object, e.g., "image/png" or "application/json".
     *
     * https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
     */
    public readonly contentType: string,
    /**
     * The base64-encoded data for this embed.
     */
    public readonly base64Data: string,
  ) {
    if (!isBase64String(base64Data)) {
      throw new Error(`Invalid base64 data: ${base64Data}. If you're trying to pass a URI, use Embed.fromUri() instead.`);
    }
  }

  static async fromUri(contentType: string, uri: string): Promise<Embed> {
    const response = await got(uri, {
      responseType: 'buffer',
    });

    if (response.statusCode !== 200) {
      throw new Error(`Got status code ${response.statusCode} when fetching ${uri}`);
    }

    console.log(response.body);

    return new Embed(contentType, response.body.toString('base64'));
  }
}
