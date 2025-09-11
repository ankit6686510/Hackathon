/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_API_BASE_URL: string
  readonly VITE_NODE_ENV: string
  readonly VITE_GOOGLE_CLIENT_ID: string
  readonly VITE_ENABLE_FEEDBACK: string
  readonly VITE_ENABLE_SEARCH_HISTORY: string
  readonly VITE_MAX_SEARCH_HISTORY: string
  readonly VITE_ENABLE_AUTH: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_DESCRIPTION: string
  readonly VITE_DEBUG: string
  readonly VITE_LOG_LEVEL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
