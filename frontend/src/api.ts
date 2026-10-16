export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch('/api' + path, {
      ...options,
      headers: options.body instanceof FormData ? options.headers : { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new Error('无法连接后端，请确认 Python 服务已启动，且 NOVEL_API_URL 与前端代理一致。')
  }
  if (!response.ok) {
    let message = '操作失败，请稍后重试。'
    try {
      const body = await response.json()
      message = typeof body.detail === 'string' ? body.detail : body.detail?.map((item: { msg: string }) => item.msg).join('；') || message
    } catch { /* Keep the readable fallback for a proxy or non-JSON error. */ }
    throw new Error(message)
  }
  return response.json() as Promise<T>
}

export const post = <T>(path: string, body: unknown) => api<T>(path, { method: 'POST', body: JSON.stringify(body) })
