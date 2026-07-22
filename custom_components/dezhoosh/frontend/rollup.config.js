import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/dezhoosh-cards.ts",
  output: {
    file: "../www/dezhoosh-cards.js",
    format: "es",
    inlineDynamicImports: true,
    sourcemap: false,
  },
  plugins: [
    resolve(),
    typescript({ tsconfig: "./tsconfig.json", outDir: undefined, declaration: false }),
  ],
};
