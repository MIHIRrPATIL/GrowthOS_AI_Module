import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import typescript from '@rollup/plugin-typescript';
import terser from '@rollup/plugin-terser';

export default [
  // 1. UMD bundle for standalone <script> tag on merchant websites
  {
    input: 'src/index.ts',
    output: {
      name: 'GrowthOS',
      file: 'dist/growthos.min.js',
      format: 'umd',
      sourcemap: true,
      exports: 'named',
      inlineDynamicImports: true
    },
    plugins: [
      resolve({ browser: true }),
      commonjs(),
      typescript({
        tsconfig: './tsconfig.json',
        declaration: false,
        declarationDir: undefined
      }),
      terser({
        compress: {
          drop_console: false,
          drop_debugger: true
        }
      })
    ]
  },
  // 2. ESM & CommonJS builds for npm package usage
  {
    input: 'src/index.ts',
    output: [
      {
        file: 'dist/index.esm.js',
        format: 'esm',
        sourcemap: true,
        inlineDynamicImports: true
      },
      {
        file: 'dist/index.cjs.js',
        format: 'cjs',
        sourcemap: true,
        exports: 'named',
        inlineDynamicImports: true
      }
    ],
    plugins: [
      resolve({ browser: true }),
      commonjs(),
      typescript({ tsconfig: './tsconfig.json' })
    ]
  }
];
