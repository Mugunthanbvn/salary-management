type RequestInfo = { pathname: string; search: string; hasSession: boolean };

export function loginRedirectFor(request: RequestInfo): string | null {
  void request;
  throw new Error("loginRedirectFor is not implemented yet");
}
