/* Thin JSON client for the BillBhasha API.
   Every request carries X-Family-Code so each visitor stays in their
   own private space; X-Family-Pin unlocks spaces that set one. */
const base = "";

export const famCode = () => localStorage.getItem("bb-family") || "default";
export const setFamCode = (c) => localStorage.setItem("bb-family", c);

async function req(path, opts = {}) {
  const pin = document.getElementById("pin")?.value?.trim() || "";
  const headers = {
    "X-Family-Code": famCode(),
    ...(opts.headers || {}),
  };
  if (pin) headers["X-Family-Pin"] = pin;
  const res = await fetch(base + path, { ...opts, headers });
  if (!res.ok) {
    let msg = "Kuch gadbad hui, dobara koshish kijiye";
    try {
      const j = await res.json();
      if (j.detail) msg = j.detail;
    } catch { /* keep friendly default */ }
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  const ct = res.headers.get("content-type") || "";
  return ct.includes("json") ? res.json() : res.blob();
}

async function postJSON(path, body) {
  const res = await fetch(base + path, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Family-Code": famCode() },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || "Kuch gadbad hui");
    err.status = res.status;
    throw err;
  }
  return data;
}

export const api = {
  health: () => req("/api/health"),
  scanImage: async (file, lang = "hi") => {
    const fd = new FormData();
    fd.append("image", file);
    fd.append("lang", lang);
    fd.append("family", famCode());
    // Shrunk photos arrive as nameless Blobs — FastAPI's File() rejects
    // parts without a filename (422), so always send one.
    if (!(fd.get("image") instanceof File)) {
      fd.set("image", new File([file], "photo.jpg", { type: "image/jpeg" }));
    }
    const res = await fetch("/api/scan", { method: "POST", body: fd });
    if (!res.ok) throw new Error("Photo bhejne mein dikkat aayi");
    return res.json();
  },
  scanText: (text, lang = "hi") => postJSON("/api/scan-text", { text, lang }),
  status: (id) => req(`/api/scan/${id}/status`),
  result: (id) => req(`/api/scan/${id}`),
  audioUrl: (id) => `/api/scan/${id}/audio`,
  remove: (id) => req(`/api/scan/${id}`, { method: "DELETE" }),
  history: () => req("/api/history?limit=30"),
  trends: () => req("/api/trends"),
  familyEnsure: (code) => postJSON("/api/family/ensure", code ? { code } : {}),
  familyJoin: (code, pin) => postJSON("/api/family/join", { code, pin }),
  familyPin: (code, pin, newPin) =>
    postJSON("/api/family/pin", { code, pin, new_pin: newPin }),
};
