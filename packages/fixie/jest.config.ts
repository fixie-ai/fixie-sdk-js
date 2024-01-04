import type { Config } from '@jest/types';

const config: Config.InitialOptions = {
  verbose: true,
  // We only want tests to run directly from the 'tests' directory,
  // not from compiled JS code.
  testPathIgnorePatterns: ['^dist/'],
  testMatch: ['**/tests/*.test.ts'],
  automock: false,
  // This is necessary so that Jest can deal with an import of a
  // TS file as ".js" as required by TypeScript and ESM.
  moduleNameMapper: {
    '(.+)\\.js': '$1',
  },
  // The below is necessary to ensure ts-jest will work properly with ESM.
  extensionsToTreatAsEsm: ['.ts', '.tsx', '.mts'],
  transform: {
    '^.+\\.tsx?$': [
      'ts-jest',
      {
        useESM: true,
        // This is necessary to prevent ts-jest from hanging on certain TS errors.
        isolatedModules: true,
      },
    ],
  },
};
export default config;
