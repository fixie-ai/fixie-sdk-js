# TODO


## Local Development & Testing
When adding new features to the SDK, you can test them locally using [`yalc`](https://github.com/wclr/yalc).

The workflow is as follows:
1. In the `fixie-sdk-js` project run `yalc publish`. This copies everything that would be published to npm.
1. In the dependent project where you want to test the updates, run `yalc add fixie`. This copies the new version locally and adds it as a dependency in `package.json`.
1. `yalc remove fixie` will remove it.