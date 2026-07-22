import js from '@eslint/js';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

/**
 * ESLint flat config.
 *
 * `npm run lint` was declared in package.json but no config file existed, so
 * linting failed with "couldn't find an eslint.config file" and had therefore
 * never run against this codebase.
 */
export default tseslint.config(
  { ignores: ['dist', 'node_modules', '.next'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.browser,
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // `any` is used deliberately at the SSE parsing boundary, where the payload
      // shape is validated at runtime rather than by the type system.
      '@typescript-eslint/no-explicit-any': 'warn',
    },
  },
);
