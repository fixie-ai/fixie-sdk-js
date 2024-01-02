import type { Config } from '@jest/types';

const config: Config.InitialOptions = {
  // The following preset allows Jest to use ts-jest to process Typescript
  // files, and to support ESM modules.
  preset: 'ts-jest/presets/default-esm',
  verbose: true,
  // We only want tests to run directly from the 'tests' directory,
  // not from compiled JS code.
  testPathIgnorePatterns: ['^dist/'],
  testMatch: ['**/tests/*.test.ts'],
  automock: false,
  // This is necessary so that Jest can deal with an import of a
  // TS file as ".js" as required by TypeScript and ESM.
  moduleNameMapper: {
    "(.+)\\.js": "$1"
  },
};
export default config;
