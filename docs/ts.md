# NodeJS Functions
You can implement agent funcs in NodeJS. To get started:

```
$ fixie agent init --language ts
```

This generates a TypeScript project template, and all the examples in the docs will be in TypeScript, but you can also use JS if you preferl

## Example
To make funcs available to your agent, export them from your module:

```ts
import type { AgentFunc } from '@fixieai/sdk';

export const getRandomNumber: AgentFunc = (query) => {
  const [min, max] = query.text.split(' ');

  return Math.floor(Math.random() * (max - min + 1)) + min;
}

export const makeAPICall: AgentFunc = async () => {
  const result = await makeMyAPICall('my', 'params');
  return result.json();
}
```

Use `npm install --save @fixieai/sdk` to get the SDK.

## TypeScript


## Contract
* Fixie expects your funcs to be exported from [the `main` module of your package](https://docs.npmjs.com/cli/v9/configuring-npm/package-json#main). 

* Fixie will invoke your functions in Node 18.

* If a `package-lock.json` or `yarn.lock` file is available, Fixie will install them via `npm ci`. If no lockfile is available, Fixie will install your package dependencies via `npm install`.

* If your code is in TypeScript, it'll be loaded with [`ts-node`](https://typestrong.org/ts-node/). `ts-node` will look for a `tsconfig.json` in your project. The `@fixieai/sdk` dependency declared in your `package.json` will transitively pull in `ts-node`.
    * If you want to control the TypeScript compilation yourself:
        1. Create a `tsc` command that will emit JS.
        1. Call that command from [the `prepublishOnly` hook](https://docs.npmjs.com/cli/v9/using-npm/scripts#prepare-and-prepublish).
        1. Update your `package.json` `main` field to point to the emitted JS entrypoint.

### Limitations

* You can't pass [flags/env vars to NodeJS](https://nodejs.org/api/cli.html).

* Your funcs can't depend on private repository packages.