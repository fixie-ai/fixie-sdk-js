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
};
export default config;
