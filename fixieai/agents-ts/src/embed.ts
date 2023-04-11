import got from 'got';

function isURL(str: string) {
  try {
    new URL(str);
    return true;
  } catch {
    return false;
  }
}

function uriFromBase64(base64Data: string): string {
  return `data:base64,${base64Data}`;
}

export function base64FromUri(uri: string): string {
  const [, base64Data] = uri.split('data:base64,');
  return base64Data;
}

export interface SerializedEmbed extends Pick<Embed, 'uri'> {
  content_type: string;
}

/**
 * A data object attached to a Message. This is useful when you want to pass data between agents. For
 * instance, you might want to generate and pass an image. Or, if you have text, and you want to pass that text
 * atomically (so it doesn't get munged by other LLMs), you can pass it as an embed.
 */
export class Embed {
  public constructor(
    /**
     * The MIME content type of the object, e.g., "image/png" or "application/json".
     *
     * https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
     */
    public readonly contentType: string,
    /**
     * The URI for this embed.
     *
     * This URI could either point to an external resource, or be a base64-encoded data URI.
     */
    public readonly uri: string,
  ) {}

  /**
   * Format this Embed for sending to the Fixie API.
   */
  serialize(): SerializedEmbed {
    return {
      content_type: this.contentType,
      uri: this.uri,
    };
  }

  /**
   * Get the embed's contents as text. If the embed was created from a URI pointing to an external resource, this method will fetch the URI. If the embed was created from base64 data, this method will decode the base64 data.
   *
   * @returns this embed's data as a UTF-8 string.
   */
  async loadDataAsText() {
    return (await this.getDataAsBinary()).toString('utf-8');
  }

  /**
   * Get the embed's contents as text. If the embed was created from a URI pointing to an external resource, this method will fetch the URI. If the embed was created from base64 data, this method will decode the base64 data.
   *
   * @returns this embed's data as a [Buffer](https://nodejs.org/docs/latest/api/buffer.html).
   */
  async getDataAsBinary() {
    if (this.uri.startsWith('data:base64,')) {
      return Buffer.from(base64FromUri(this.uri), 'base64');
    }

    const response = await got(this.uri, {
      responseType: 'buffer',
    });

    if (response.statusCode !== 200) {
      throw new Error(
        `Got status code ${response.statusCode} when fetching ${this.uri}`,
      );
    }

    return response.body;
  }

  /**
   * Create an embed from base64 data.
   *
   * @param contentType The MIME content type of the object, e.g., "image/png" or "application/json" (https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types)
   * @param textData The base64-encoded data for this embed.
   */
  static fromBase64(contentType: string, textData: string): Embed {
    // This won't catch every type of non-base64 string, but it will catch a common mistake.
    if (isURL(textData)) {
      throw new Error(
        `Invalid base64 data: "${textData}". If you're trying to pass a URI, use Embed.fromUri() instead.`,
      );
    }

    const base64 = Buffer.from(textData, 'utf-8').toString('base64');
    const uri = uriFromBase64(base64);

    return new Embed(contentType, uri);
  }

  static fromBinary(contentType: string, binaryData: Buffer): Embed {
    return Embed.fromBase64(contentType, binaryData.toString('base64'));
  }
}
