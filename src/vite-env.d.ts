/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_RETRACE_API_URL?: string;
  readonly DEV: boolean;
  readonly PROD: boolean;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
