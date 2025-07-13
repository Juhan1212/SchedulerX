export type SuccessResponseParam = {
  data: string
  status: number
  headers?: Record<string, string>
}

export type SuccessResponseValue = SuccessResponseParam & {
  code: 'ok'
}

export type ErrorResponseParam = {
  error: unknown
  status: number
}
export type ErrorResponseValue = ErrorResponseParam & {
  code: 'fail'
}
