/* Thin JSON client for the BillBhasha API. */
const base = "";

async function req(path, opts = {}) {
  const pin = document.getElementById("pin")?.value?.trim() || "";
  const headers = { ...(opts.headers || {}) };
  if (pin) headers["X-Family-Pin"] = pin;
  const res = await fetch(base + path, { ...opts, headers });
  if (!res.ok) {
    let msg = "Kuch gadbad hui, dobara koshish kijiye";
    try {
      const j = await res.json();
      if (j.detail) msg = j.detail;
    } catch { /* keep friendly default */ }
    throw new Error(msg);
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res.blob();
}

export const api = {
  health: () => req("/api/health"),
  scanImage: async (file, lang = "hi") => {
    const fd = new FormData();
    fd.append("image", file);
    fd.append("lang", lang);
    const res = await fetch("/api/scan", { method: "POST", body: fd });
    if (!res.ok) throw new Error("Photo bhejne mein dikkat aayi");
    return res.json();
  },
  scanText: async (text, lang = "hi") => {
    const res = await fetch("/api/scan-text", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, lang }),
    });
    if (!res.ok) throw new Error("Bhejne mein dikkat aayi");
    return res.json();
  },
  status: (id) => req(`/api/scan/${id}/status`),
  result: (id) => req(`/api/scan/${id}`),
  audioUrl: (id) => `/api/scan/${id}/audio`,
  remove: (id) => req(`/api/scan/${id}`, { method: "DELETE" }),
  history: () => req("/api/history?limit=30"),
  trends: () => req("/api/trends"),
};
