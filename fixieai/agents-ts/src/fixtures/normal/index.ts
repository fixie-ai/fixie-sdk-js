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

export const roll: AgentFunc = (query) => {
  const [diceSize, numDice] = query.text.split(' ');
  const dice = Array.from({ length: Number(numDice) }, () => Math.floor(Math.random() * Number(diceSize)) + 1);
  return dice.join(' ');
};

export const willThrowError: AgentFunc = () => {
  throw new Error('This is an error');
};

export const willThrowErrorAsync: AgentFunc = () => Promise.reject(new Error('This is an async error'));

export const rollAsync: AgentFunc = (query) => Promise.resolve(roll(query));

export const chartAsBase64: AgentFunc = () => {
  const chartData = fs.readFileSync(path.join(__dirname, 'chart-data.txt'), 'utf8');
  return {
    text: 'here is your chart #chart',
    embeds: {
      chart: Embed.fromBase64('image/webp', chartData),
    },
  };
};

export const chartAsUri: AgentFunc = async () => ({
  text: 'here is your chart #chart',
  embeds: {
    chart: await Embed.fromUri('image/webp', 'https://sample-url-to-embed.com/image.webp'),
  },
});
