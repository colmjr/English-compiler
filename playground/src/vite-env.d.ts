/// <reference types="vite/client" />

declare module '*.json' {
  const value: {
    generatedAt: string;
    count: number;
    examples: Array<{
      id: string;
      name: string;
      category: string;
      source: string;
      expectedOutput: string;
      version: string;
    }>;
  };
  export default value;
}
