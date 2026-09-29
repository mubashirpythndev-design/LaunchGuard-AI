import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "./openapi.json",
  output: "./src",
  plugins: [
    "@hey-api/typescript",
    {
      name: "zod",
      compatibilityVersion: 4,
      types: { infer: true },
    },
  ],
});
