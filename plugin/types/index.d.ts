export type Estado = {
  avisos: Record<string, string | null>
  falhas: Record<string, string>
}

declare module 'claude-code' {
  interface PluginState {
    arkos: { estado: Estado }
  }
}
