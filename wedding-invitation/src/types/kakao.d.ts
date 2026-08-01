interface Window {
  Kakao?: {
    init: (javascriptKey: string) => void
    isInitialized: () => boolean
    Share: {
      sendDefault: (payload: unknown) => void
    }
  }
}
