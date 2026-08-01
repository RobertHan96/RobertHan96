import type { WeddingConfig } from '../types/wedding'

type ShareConfig = WeddingConfig['share']

export function buildKakaoSharePayload(share: ShareConfig) {
  const link = { mobileWebUrl: share.url, webUrl: share.url }

  return {
    objectType: 'feed' as const,
    content: {
      title: share.title,
      description: share.description,
      imageUrl: share.ogImage,
      link,
    },
    buttons: [{ title: '청첩장 보기', link }],
  }
}

export function sendKakaoShare(share: ShareConfig) {
  if (!share.kakaoJavascriptKey) {
    throw new Error('카카오 JavaScript 키가 설정되지 않았습니다.')
  }
  if (!window.Kakao) {
    throw new Error('카카오 SDK를 불러오지 못했습니다.')
  }
  if (!window.Kakao.isInitialized()) {
    window.Kakao.init(share.kakaoJavascriptKey)
  }

  window.Kakao.Share.sendDefault(buildKakaoSharePayload(share))
}
