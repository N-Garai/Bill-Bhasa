/* Browser voice — the phone speaks Hindi/Bangla/English itself.
   Used whenever the server has no audio ready (small boxes, offline).

   Three things make it sound genuinely better than a naive call:
   1. Smart voice pick — scores every installed voice per language and
      prefers good ones (Google/Microsoft natural voices, exact locale).
   2. Speech cleanup — our explanations are romanized ("Nomoskar", "moṭ")
      with ₹ signs; voices mumble those, so we convert to spoken words
      ("taka", "mot") and strip diacritics/emoji first.
   3. Sentence chunking — long paragraphs get cut off or rushed; we speak
      sentence by sentence with a natural pause.
 */
const best = { hi: null, bn: null, en: null };

function scoreVoice(v, want) {
  const l = (v.lang || "").toLowerCase();
  const n = (v.name || "").toLowerCase();
  if (!l.startsWith(want)) return -1;
  let s = 0;
  if (l === `${want}-in` || l === want) s += 10;
  else s += 6;
  if (n.includes("google")) s += 5;      // Google hi/bn voices are the best free ones
  if (n.includes("microsoft")) s += 3;   // Edge natural voices
  if (n.includes("natural")) s += 2;
  if (v.localService) s += 1;            // on-device = no network stutter
  return s;
}

function pickVoices() {
  try {
    const vs = speechSynthesis.getVoices();
    if (!vs.length) return;
    for (const want of ["hi", "bn", "en"]) {
      let top = null, topScore = -1;
      for (const v of vs) {
        const s = scoreVoice(v, want);
        if (s > topScore) { topScore = s; top = v; }
      }
      best[want] = top;
    }
  } catch { /* speech unavailable */ }
}
if ("speechSynthesis" in window) {
  pickVoices();
  speechSynthesis.onvoiceschanged = pickVoices;
  // Some browsers populate voices late — retry a few times.
  setTimeout(pickVoices, 1500);
  setTimeout(pickVoices, 4000);
}

const MONEY_WORD = { hi: " rupaye ", bn: " taka ", en: " rupees " };

export function cleanForSpeech(text, lang = "hi") {
  const short = (lang || "hi").slice(0, 2);
  let s = String(text || "");
  s = s.replace(/₹/g, MONEY_WORD[short] || MONEY_WORD.hi);
  s = s.replace(/[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}\u{2B00}-\u{2BFF}]/gu, " "); // no spoken emoji
  try {
    s = s.normalize("NFD").replace(/[\u0300-\u036f]/g, ""); // moṭ -> mot, ā -> a
  } catch { /* keep original */ }
  s = s.replace(/[*_#<>]/g, " ").replace(/\s+/g, " ").trim();
  return s;
}

function chunkSentences(text) {
  const parts = String(text).split(/(?<=[.!?।\n])\s+/).map((p) => p.trim()).filter(Boolean);
  if (!parts.length) return [];
  // Merge tiny fragments so speech doesn't stutter on abbreviations.
  const out = [];
  for (const p of parts) {
    if (out.length && (out[out.length - 1].length + p.length) < 90) {
      out[out.length - 1] += " " + p;
    } else out.push(p);
  }
  return out.slice(0, 24); // safety cap (~3 min of speech)
}

let speakToken = 0;

export function speakBrowser(text, lang = "hi", rate = 1) {
  const short = (lang || "hi").slice(0, 2);
  const tag = short === "bn" ? "bn-IN" : short === "en" ? "en-IN" : "hi-IN";
  const my = ++speakToken;
  return new Promise((resolve) => {
    const finish = () => resolve();
    try {
      if (!("speechSynthesis" in window)) return finish();
      speechSynthesis.cancel();
      const chunks = chunkSentences(cleanForSpeech(text, short));
      if (!chunks.length) return finish();
      let i = 0;
      const voice = best[short] || best.en || null;
      const next = () => {
        if (my !== speakToken) return finish(); // superseded / stopped
        if (i >= chunks.length) return finish();
        const u = new SpeechSynthesisUtterance(chunks[i++]);
        u.lang = tag;
        u.rate = rate || 1;
        u.pitch = 1.0;
        if (voice) u.voice = voice;
        u.onend = () => setTimeout(next, 180); // breath between sentences
        u.onerror = () => setTimeout(next, 120);
        speechSynthesis.speak(u);
      };
      next();
      setTimeout(() => { if (my === speakToken) { try { speechSynthesis.cancel(); } catch {} finish(); } }, 180000);
    } catch { finish(); }
  });
}

export function stopBrowser() {
  speakToken++;
  try { speechSynthesis?.cancel(); } catch { /* noop */ }
}
