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

export interface SerializedEmbed {
  content_type: string;
  uri: string;
}

/**
 * A binary object attached to a Message.
 *
 * You can create an embed with from base64 data or from a URI.
 *
 * You can also always read either the base64 data or the URI; creating an Embed from one will populate the other.
 */
export class Embed {
  private constructor(
    /**
     * The MIME content type of the object, e.g., "image/png" or "application/json".
     *
     * https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types
     */
    public readonly contentType: string,
    /**
     * The base64-encoded data for this embed.
     */
    private readonly base64Data: string,
    /**
     * The URI for this embed.
     *
     * If this embed was constructed from base64 data, then this URI will be a data URI. This URL is not guaranteed to point to an external resource.
     */
    public readonly uri: string,
  ) {
  }

  /**
   * Format this Embed for sending to the Fixie API.
   */
  serialize(): SerializedEmbed {
    return {
      content_type: this.contentType,
      uri: uriFromBase64(this.base64Data),
    };
  }

  /**
   * @returns this embed's data as a UTF-8 string.
   */
  getDataAsText() {
    return this.getDataAsBinary().toString('utf-8');
  }

  /**
   * @returns this embed's data as a [Buffer](https://nodejs.org/docs/latest/api/buffer.html).
   */
  getDataAsBinary() {
    return Buffer.from(this.base64Data, 'base64');
  }

  /**
   * Create an embed from base64 data.
   *
   * @param contentType The MIME content type of the object, e.g., "image/png" or "application/json" (https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types)
   * @param textData The base64-encoded data for this embed.
   */
  static fromText(contentType: string, textData: string): Embed {
    // This won't catch every type of non-base64 string, but it will catch a common mistake.
    if (isURL(textData)) {
      throw new Error(
        `Invalid base64 data: "${textData}". If you're trying to pass a URI, use Embed.fromUri() instead.`,
      );
    }

    // convert textData to base64
    const base64 = Buffer.from(textData, 'utf-8').toString('base64');
    const uri = uriFromBase64(base64);

    return new Embed(contentType, base64, uri);
  }

  static fromBinary(contentType: string, binaryData: Buffer): Embed {
    return Embed.fromText(contentType, binaryData.toString('base64'));
  }

  /**
   * Create an embed from a URI of an external resource.
   *
   * @param contentType The MIME content type of the object, e.g., "image/png" or "application/json" (https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types/Common_types)
   * @param uri
   */
  static async fromUri(contentType: string, uri: string): Promise<Embed> {
    if (base64FromUri(uri)) {
      return new Embed(contentType, base64FromUri(uri), uri);
    }

    const response = await got(uri, {
      responseType: 'buffer',
    });

    if (response.statusCode !== 200) {
      throw new Error(`Got status code ${response.statusCode} when fetching ${uri}`);
    }

    return new Embed(contentType, response.body.toString('base64'), uri);
  }
}
