/* Browser voice fallback — speaks Hindi with the phone's own voice.
   Used whenever the server has no audio ready (small boxes, offline). */
let voice = null;
let voiceBn = null;

function pickVoice() {
  try {
    const vs = speechSynthesis.getVoices();
    voice = vs.find((v) => v.lang?.toLowerCase().startsWith("hi")) ||
            vs.find((v) => v.lang?.toLowerCase().startsWith("en-in")) ||
            null;
    voiceBn = vs.find((v) => v.lang?.toLowerCase().startsWith("bn")) || null;
  } catch { /* speech unavailable */ }
}
if ("speechSynthesis" in window) {
  pickVoice();
  speechSynthesis.onvoiceschanged = pickVoice;
}

export function speakBrowser(text, lang = "hi") {
  const bn = (lang || "hi").slice(0, 2) === "bn";
  return new Promise((resolve) => {
    try {
      if (!("speechSynthesis" in window)) return resolve();
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = bn ? "bn-IN" : "hi-IN";
      u.rate = 0.92;
      u.pitch = 1.05;
      const v = bn ? (voiceBn || voice) : voice;
      if (v) u.voice = v;
      u.onend = () => resolve();
      u.onerror = () => resolve();
      speechSynthesis.speak(u);
      setTimeout(resolve, 30000); // safety
    } catch { resolve(); }
  });
}

export function stopBrowser() {
  try { speechSynthesis?.cancel(); } catch { /* noop */ }
}
