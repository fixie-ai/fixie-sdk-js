module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/strict',
    'nth',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    project: 'tsconfig.json',
  },
  plugins: ['@typescript-eslint',],
  root: true,

  env: {
    node: true,
  },

  rules: {
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': 'warn',

    'no-magic-numbers': 'off',
    '@typescript-eslint/no-magic-numbers': [
      'warn',
      {
        ignoreReadonlyClassProperties: true,
        ignore: [0, 1, 2,],
        ignoreTypeIndexes: true,
      },
    ],

    'no-use-before-define': ['error', { functions: false, variables: true, },],

    'no-trailing-spaces': 'warn',

    // Disable style rules to let dprint own it
    'object-curly-spacing': 'off',
    'comma-dangle': 'off',
    'max-len': 'off',
    indent: 'off',
    'no-mixed-operators': 'off',
    'no-console': 'off',
    'arrow-parens': 'off',

    // Add additional strictness beyond the recommended set
    '@typescript-eslint/parameter-properties': ['warn', { prefer: 'parameter-properties', },],
    '@typescript-eslint/prefer-readonly': 'warn',
    '@typescript-eslint/strict-boolean-expressions': 'warn',
    '@typescript-eslint/switch-exhaustiveness-check': 'warn',
  },
};
