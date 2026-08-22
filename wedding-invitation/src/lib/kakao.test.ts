import { afterEach, describe, expect, it, vi } from 'vitest'

import { wedding } from '../config/wedding'
import { buildKakaoSharePayload, sendKakaoShare } from './kakao'

const share = {
  title: '이다예 한영신 결혼합니다',
  description: '2026년 11월 15일 오후 3시 50분 · 더컨벤션 잠실',
  ogImage: 'https://roberthan96.pages.dev/images/location/map.jpeg',
  url: 'https://roberthan96.pages.dev/',
  kakaoJavascriptKey: 'javascript-key',
}

describe('Kakao Talk sharing', () => {
  afterEach(() => {
    delete window.Kakao
  })

  it('builds a feed template with the deployed invitation URL', () => {
    expect(wedding.share.title).toBe('이다예 한영신 결혼합니다')
    expect(buildKakaoSharePayload(share)).toEqual({
      objectType: 'feed',
      content: {
        title: share.title,
        description: share.description,
        imageUrl: share.ogImage,
        link: { mobileWebUrl: share.url, webUrl: share.url },
      },
      buttons: [
        {
          title: '청첩장 보기',
          link: { mobileWebUrl: share.url, webUrl: share.url },
        },
      ],
    })
  })

  it('initializes the SDK and opens the Kakao Talk share picker', () => {
    const init = vi.fn()
    const sendDefault = vi.fn()
    window.Kakao = {
      init,
      isInitialized: vi.fn(() => false),
      Share: { sendDefault },
    }

    sendKakaoShare(share)

    expect(init).toHaveBeenCalledWith('javascript-key')
    expect(sendDefault).toHaveBeenCalledWith(buildKakaoSharePayload(share))
  })

  it('fails clearly when the SDK has not loaded', () => {
    expect(() => sendKakaoShare(share)).toThrow('카카오 SDK를 불러오지 못했습니다.')
  })
})
