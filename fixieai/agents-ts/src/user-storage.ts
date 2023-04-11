import got, { Got, Response } from 'got';
import { Jsonifiable, JsonValue } from 'type-fest';

class GotError extends Error {
  constructor(message: string, public readonly response: Response) {
    super(message);
  }
}

/**
 * https://docs.fixie.ai/agents/#user-storage
 *
 * A client for Fixie's user storage API.
 *
 * This TS is the analogue of this Python: fixieai/agents/user_storage.py.
 */
export class UserStorage {
  private readonly gotClient: Got;

  constructor(apiUrl: string, agentId: string, authToken: string) {
    this.gotClient = got.extend({
      prefixUrl: `${apiUrl}/${agentId}/`,
      responseType: 'json',
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
  }

  /**
   * Get the value for a key. If the key does not exist, an error will be thrown.
   *
   * Use the <T> type parameter to set the expected return type. This is essentially a cast, so be careful that your
   * assertion is accurate. 😀
   *
   * @example
   *  await userStorage.get<string[]>('my-list-of-strings');
   */
  get<T extends JsonValue>(key: string): Promise<T> {
    return this.gotClient.get(key).json();
  }

  /**
   * Get all saved keys.
   */
  getKeys(): Promise<string[]> {
    return this.gotClient.get('').json();
  }

  /**
   * Set a value for a key.
   */
  async set(key: string, value: Jsonifiable): Promise<void> {
    await this.gotClient.post(key, {
      // Got's types are incorrectly restrictive, so we'll cast.
      json: value as Record<string, any>,
    });
  }

  /**
   * Check if a key exists in storage.
   */
  async has(key: string): Promise<boolean> {
    const response = await this.gotClient.head(key, {
      throwHttpErrors: false,
    });
    if (response.statusCode === 404) {
      return false;
    }
    if (response.statusCode === 200) {
      return true;
    }
    throw new GotError(
      `Fixie API: Unexpected status code ${response.statusCode} when checking for key ${key}. This is probably not your fault.`,
      response,
    );
  }

  /**
   * Delete a key. If the key does not already exist, an error will be thrown.
   */
  async delete(key: string): Promise<void> {
    await this.gotClient.delete(key);
  }
}
