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

export const BASE_PROMPT = 'General info about what this agent does and the tone it should use.';

export const FEW_SHOTS = `
Q: Sample query to this agent
A: Sample response

Q: Another sample query
Ask Func[example]: input
Func[example] says: output
A: The other response is output
`;

export function example(query: any): string {
  if (query.text === 'input') {
    return 'output';
  }
  throw new Error('Invalid input');
}
