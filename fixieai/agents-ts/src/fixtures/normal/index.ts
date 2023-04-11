/**
 * A templated Fixie agent
 *
 * Fixie docs:
 *     https://docs.fixie.ai
 *
 * Fixie agent example:
 *     https://github.com/fixie-ai/fixie-examples
 */
import fs from 'fs';
import path from 'path';
import { AgentFunc, Embed } from '../../';

export const BASE_PROMPT = "I'm an agent that rolls virtual dice!";

export const FEW_SHOTS = `
Q: Roll a d20
Ask Func[roll]: 20 1
Func[roll] says: 12
A: You rolled a 12!

Q: Roll two dice and blow on them first for good luck
Ask Func[roll]: 6 2
Func[roll] says: 4 3
A: You rolled a 4 and a 3, with a total of 7.

Q: Roll 3d8
Ask Func[roll]: 8 3
Func[roll] says: 5 3 8
A: You rolled 5, 3, and 8, for a total of 16.
`;

export const roll = (query: Parameters<AgentFunc>[0]): ReturnType<AgentFunc> => {
  const [diceSize, numDice] = query.text.split(' ');
  const dice = Array.from({ length: Number(numDice) }, () => Math.floor(Math.random() * Number(diceSize)) + 1);
  return dice.join(' ');
};

export const willThrowError: AgentFunc = () => {
  throw new Error('This is an error');
};

export const willThrowErrorAsync: AgentFunc = () => Promise.reject(new Error('This is an async error'));

export const rollAsync: AgentFunc = (query) => Promise.resolve(roll(query));

export const chartFromBinary: AgentFunc = () => {
  const chartData = fs.readFileSync(path.join(__dirname, 'chart.webp'));
  return {
    text: 'here is your chart #chart',
    embeds: {
      chart: Embed.fromBinary('image/webp', chartData),
    },
  };
};

export const chartFromText: AgentFunc = () => ({
  text: 'here is your chart #chart',
  embeds: {
    chart: Embed.fromBase64('text/plain', 'my text data'),
  },
});

export const chartFromUri: AgentFunc = () => ({
  text: 'here is your chart #chart',
  embeds: {
    chart: new Embed('image/webp', 'https://sample-url-to-embed.com/image.webp'),
  },
});

export const getTextOfEmbed: AgentFunc = (query) => query.embeds[query.text].loadDataAsText();

export const saveItem: AgentFunc = async (query, userStorage) => {
  const [key, value] = query.text.split(':');
  await userStorage.set(key, value);
  return 'Set value';
};

export const getItem: AgentFunc = (query, userStorage) => userStorage.get<string>(query.text);

export const getItems: AgentFunc = async (_query, userStorage) => {
  const items = await userStorage.getKeys();
  return JSON.stringify(items);
};

export const deleteItem: AgentFunc = async (query, userStorage) => {
  await userStorage.delete(query.text);
  return 'Deleted value';
};

export const hasItem: AgentFunc = async (query, userStorage) => (await userStorage.has(query.text)).toString();
