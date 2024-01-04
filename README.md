# Fixie Javascript SDK

This is a monorepo providing a TypeScript / JavaScript SDK to the
[Fixie](https://fixie.ai) platform. It contains the following packages:

- `fixie`: A NodeJS SDK and CLI.
- `fixie-web`: A browser-based SDK.
- `fixie-common`: A shared package containing code used by both the
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

When adding new features to the SDK, you can test them locally using [`yalc`](https://github.com/wclr/yalc).

The workflow is as follows:

1. In the `fixie-sdk-js` project run `yalc publish`. This copies everything that would be published to npm.
1. In the dependent project where you want to test the updates, run `yalc add fixie`. This copies the new version locally and adds it as a dependency in `package.json`.
1. `yalc remove fixie` will remove it.

## Publishing changes

Please submit a `changeset` file along with your PR, which is used to automatically bump package
versions and publish to `npm`. To do this, run:

```bash
$ yarn changeset 
```

at the root of this tree, and follow the instructions to select which packages should
get a version bump. Then `git commit` the resulting `changeset` file.

You can then publish the changesets by running:

```bash
$ yarn changeset publish --tag unstable
```

at the top level.
