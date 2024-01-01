# Fixie Javascript SDK

This is a monorepo providing a TypeScript / JavaScript SDK to the
[Fixie](https://fixie.ai) platform. It contains the following packages:

* `fixie`: A NodeJS SDK and CLI.
* `fixie-web`: A browser-based SDK.
* `fixie-common`: A shared package containing code used by both the
  NodeJS and browser SDKs.

Full documentation is provided at [https://fixie.ai/docs](https://fixie.ai/docs).

## Development

This repository uses [Yarn workspaces](https://classic.yarnpkg.com/en/docs/workspaces/). To build and test the repo locally, run the following
commands:

```bash
$ yarn
$ yarn build
$ yarn test
```

You can use `yarn format` to format the code using [Prettier](https://prettier.io/), and `yarn lint` to lint the code.
