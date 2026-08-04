import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';

function jsxRootIdentifier(node) {
  if (node.type === 'JSXIdentifier') return node.name;
  if (node.type === 'JSXMemberExpression') return jsxRootIdentifier(node.object);
  return null;
}

const skydataJsx = {
  rules: {
    'uses-vars': {
      meta: {
        type: 'problem',
        docs: {
          description: 'Mark component identifiers referenced by JSX as used.',
        },
        schema: [],
      },
      create(context) {
        const sourceCode = context.sourceCode;

        return {
          JSXOpeningElement(node) {
            const name = jsxRootIdentifier(node.name);
            if (name && /^[A-Z]/u.test(name)) {
              sourceCode.markVariableAsUsed(name, node);
            }
          },
        };
      },
    },
  },
};

export default [
  { ignores: ['dist'] },
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 'latest',
      globals: globals.browser,
      parserOptions: { ecmaFeatures: { jsx: true }, sourceType: 'module' },
    },
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
      'skydata-jsx': skydataJsx,
    },
    rules: {
      ...js.configs.recommended.rules,
      ...reactHooks.configs.recommended.rules,
      'skydata-jsx/uses-vars': 'error',
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
];
