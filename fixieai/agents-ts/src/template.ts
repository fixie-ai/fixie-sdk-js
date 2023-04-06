// TODO: Move this to `fixie-examples/agents/template.ts` when we're ready.
/**
 * A templated Fixie agent
 *
 * Fixie docs:
 *     https://docs.fixie.ai
 *
 * Fixie agent example:
 *     https://github.com/fixie-ai/fixie-examples
 */

export const BASE_PROMPT = `I'm an agent that rolls virtual dice!`;

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

export function roll(query: { text: string; }): string {
  const [dsize, num_dice] = query.text.split(' ');
  const dice = Array.from({ length: Number(num_dice) }, () => Math.floor(Math.random() * Number(dsize)) + 1);
  return dice.join(' ');
}
