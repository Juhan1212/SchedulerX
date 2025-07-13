export function getBrowserTimezoneOffset() {
  const offsetInMinutes = new Date().getTimezoneOffset()
  const offsetInHours = -offsetInMinutes / 60
  return offsetInHours
}

export function intervalInSeconds(interval: string): number {
  switch (interval) {
    case '1m':
      return 60
    case '5m':
      return 300
    case '15m':
      return 900
    case '30m':
      return 1800
    case '1h':
      return 3600
    case '4h':
      return 14400
    case '8h':
      return 28800
    case '1d':
      return 86400
    case '7d':
      return 604800
    case '30d':
      return 2592000
    default:
      throw new Error(`Unsupported interval: ${interval}`)
  }
}

/**
 * 타임스탬프를 인터벌에 맞게 내림 처리하는 함수
 * @param timestamp 유닉스 타임스탬프 (초 단위)
 * @param interval 인터벌 문자열 (1m, 5m, 15m, 30m, 1h, 4h, 1d 등)
 * @returns 인터벌에 맞게 내림 처리된 타임스탬프
 */
export function alignTimeToInterval(
  timestamp: number,
  interval: string,
): number {
  const date = new Date(timestamp * 1000)

  // 인터벌에 따라 시간 정렬
  switch (interval) {
    case '1m':
      // 초만 0으로 설정
      date.setSeconds(0, 0)
      break
    case '5m':
      // 5분 단위로 내림
      date.setMinutes(Math.floor(date.getMinutes() / 5) * 5, 0, 0)
      break
    case '15m':
      // 15분 단위로 내림
      date.setMinutes(Math.floor(date.getMinutes() / 15) * 15, 0, 0)
      break
    case '30m':
      // 30분 단위로 내림
      date.setMinutes(Math.floor(date.getMinutes() / 30) * 30, 0, 0)
      break
    case '1h':
      // 시간 단위로 내림 (분, 초 = 0)
      date.setMinutes(0, 0, 0)
      break
    case '4h':
      // 4시간 단위로 내림
      date.setHours(Math.floor(date.getHours() / 4) * 4, 0, 0, 0)
      break
    case '1d':
      // 일 단위로 내림 (시간, 분, 초 = 0)
      date.setHours(0, 0, 0, 0)
      break
    case '1w': {
      // 주 단위로 내림 (일요일 기준)
      const day = date.getDay() // 0 = 일요일, 6 = 토요일
      date.setDate(date.getDate() - day)
      date.setHours(0, 0, 0, 0)
      break
    }
    case '1M':
      // 월 단위로 내림
      date.setDate(1)
      date.setHours(0, 0, 0, 0)
      break
  }

  return Math.floor(date.getTime() / 1000)
}
