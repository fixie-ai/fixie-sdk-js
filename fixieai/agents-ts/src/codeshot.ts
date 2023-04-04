import bodyParser from 'body-parser';
import express from 'express';

interface Handshake {
  basePrompt: string;
  fewShots: string[];
}

interface Message {
  text: string;
}

class AgentResponse {
  constructor(readonly message: Message) {}
}

type AgentFunc = (args: string) => string;

export class CodeShotAgent {
  basePrompt: string;
  fewShots: string[];
  funcs = new Map<string, AgentFunc>();

  constructor(prompt: string, shots: string[]) {
    this.basePrompt = prompt;
    this.fewShots = shots;
  }

  registerFunction(func: AgentFunc) {
    this.funcs.set(func.name, func);
  }

  runFunction(funcName: string, args: string): string | null {
    const func = this.funcs.get(funcName);
    if (func) {
      return func(args).toString();
    }
    return null;
  }

  _handshake(): Handshake {
    const body: Handshake = {
      basePrompt: this.basePrompt,
      fewShots: this.fewShots,
    };
    return body;
  }

  async serve(
    // eslint-disable-next-line @typescript-eslint/no-magic-numbers
    port = 8181,
  ) {
    const app = express();
    app.use(bodyParser.json());
    app.get('/', (req, res) => res.send(this._handshake()));
    app.post('/:funcName', (req, res) => {
      const funcName = req.params.funcName;
      const body = req.body;
      const result = this.runFunction(funcName, body.message.text);
      res.send({ message: { text: result } } as AgentResponse);
    });
    await new Promise<void>((resolve) => app.listen(port, () => resolve()));
    console.log(`Codeshot agent listening on port ${port}.`);
  }
}
