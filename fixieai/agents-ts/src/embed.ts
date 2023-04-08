import got from 'got';
import * as base64 from 'base-64';

// interface Embed2 {
//   contentType: string;
//   content: Uint8Array;
//   uri: string;
//   text: string;
// }

// async function createEmbed()

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
    public contentType: string,
  ) {}

  /**
   * A public URL where the object can be downloaded. This can be a data URI.
   */
  private uri?: string;

  get content(): Uint8Array {
    /* Retrieves the content for this Embed object. */
    if (this.uri?.startsWith('data:')) {
      return base64.toByteArray(this.uri.split(',')[1]);
    }
    return new Uint8Array(await (await axios.get(this.uri, { responseType: 'arraybuffer' })).data);
  }

  set content(content: Uint8Array) {
    /* Sets the content of the Embed object as a data URI. */
    this.uri = `data:base64,${base64.fromByteArray(content)}`;
  }

  /** Retrieve the content of the Embed object as a string. */
  get text(): string {
    return new TextDecoder('utf-8').decode(this.content);
  }

  /** Set the content of the Embed object as a string. */
  set text(text: string) {
    this.content = new TextEncoder().encode(text);
  }
}

export async function createEmbedFromUri(contentType: string, uri: string): Promise<Embed> {
  // Get the contents via got, then create a base64 data URI
  const content = await got(uri).buffer();
  

  const embed = new Embed(contentType, content);
  embed.uri = uri;
  return embed;
} 
