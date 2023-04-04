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

import { CodeShotAgent, Message } from 'fixieai';

const BASE_PROMPT = 'General info about what this agent does and the tone it should use.';

const FEW_SHOTS = `
Q: Sample query to this agent
A: Sample response

Q: Another sample query
Ask Func[example]: input
Func[example] says: output
A: The other response is output
`;

const agent = new CodeShotAgent(BASE_PROMPT, FEW_SHOTS);

agent.registerFunc((query: Message): string => {
  if (query.text === 'input') {
    return 'output';
  } else {
    throw new Error('Invalid input');
  }
});
