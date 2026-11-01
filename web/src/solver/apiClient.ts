export async function fetchIsolatedFootingApi(
  apiBaseUrl: string,
  widthBM: number,
  qNetKpa: number
): Promise<{ ok: boolean; data?: Record<string, unknown> }> {
  try {
    const res = await fetch(`${apiBaseUrl}/api/footings/isolated`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        B: widthBM,
        L: widthBM,
        D: 0.6,
        P: qNetKpa * widthBM * widthBM,
        Mx: 25.0,
        My: 15.0,
        q_allowable: 220.0,
      }),
    });
    if (!res.ok) return { ok: false };
    return { ok: true, data: (await res.json()) as Record<string, unknown> };
  } catch {
    return { ok: false };
  }
}
