/* BillBhasha app controller — Saral + Parivar modes, scan flow, voice.
   Bilingual: Hindi (hi) + Bangla (bn). Toggle on the Saral card. */
import { api } from "./api.js";
import { speakBrowser, stopBrowser } from "./speech.js";
import {
  attachWave, calm, flagShake, flipIn, introReveals,
  lampSweep, revealPoints, rotateTagline, sparkline, typewriter,
} from "./animations.js";
import { initHero } from "./three-hero.js";

const $ = (id) => document.getElementById(id);
const toast = (msg) => {
  const t = $("toast");
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._h);
  t._h = setTimeout(() => t.classList.remove("show"), 3200);
};

let LANG = (localStorage.getItem("bb-lang") || "hi").slice(0, 2);
if (!["hi", "bn"].includes(LANG)) LANG = "hi";

const STRINGS = {
  hi: {
    taglines: [
      "Har kagaz, aapki bhasha mein.",
      "Photo lijiye, aaraam se suniye.",
      "Bill ho ya parcha — sab saral.",
      "Bade shabd, saaf awaaz, apnapan.",
    ],
    heroL1: "Kagaz bole,", heroL2: "aapki bhasha mein.",
    heroSub: "Bijli ka bill ho ya doctor ka parcha — bas photo lijiye, aur suniye seedhe-saral shabdon mein. Bade button, saaf awaaz, koi chakkar nahi.",
    ctaStart: "📷 Chalo, photo lete hain", ctaHow: "Kaise kaam karta hai?",
    ammaHi: "Namaste! 🙏", ammaSub: "Koi kagaz samajhna ho to neeche dabaiye",
    camTxt: "Photo Lijiye", pick: "🖼️ Gallery se chuniye", orWrite: "ya likh kar bhejiye",
    ph: "Yahaan likhiye… jaise: bijli bill 540 rupaye", send: "✉️ Bhejiye",
    kicker: "Aapke liye samjhaya", play: "▶ Suniye", pause: "⏸ Rukiye",
    listening: "🔊 Sun rahe hain…", replay: "▶ Dobara suniye",
    again: "🔄 Naya photo", del: "🗑️ Ye hata dijiye",
    famH: "Parivar ki diary 📒", famSub: "Pichhle kagaz, kharcha aur zaroori nishaan — sab ek jagah.",
    pinPh: "Parivar PIN (agar lagaya ho)", load: "Dekhiye", trendH: "Mahine ka kharcha",
    tabHome: "🏠 Saral", tabFam: "📚 Parivar",
    stages: { received: "Mil gaya…", cleaning: "Saaf kar rahe…", reading: "Padh rahe…", thinking: "Samajh rahe…", speaking: "Bole rahe…", done: "Ho gaya!", error: "Arre!" },
    notes: { received: "Photo mil gayi, bas shuru kar rahe hain…", cleaning: "Dhool-mitti hata kar saaf kar rahe hain…", reading: "Akshar-akshar padh rahe hain…", thinking: "Saral shabdon mein samajh rahe hain…", speaking: "Awaaz taiyaar kar rahe hain…", done: "Taiyaar! Neeche suniye 🌼", error: "Maaf kijiye — dobara koshish kijiye." },
    errRead: "Maaf kijiye, padhne mein dikkat aayi. Roshni mein dobara photo lijiye 🙏",
    ready: "Taiyaar hai! “Suniye” dabakar suniye 🌼",
    deleted: "Hata diya — aapki marzi sabse pehle 🤍",
    writeFirst: "Pehle kuch likhiye ✍️",
    defaultSummary: "Samjha diya hai, sun lijiye 🌼",
    okLine: "✅ Sab theek lag raha hai",
    emptyTrend: (n, total) => n ? `Kul ${n} kagaz • is chart mein ₹${Math.round(total).toLocaleString("en-IN")} ka hisaab` : "Abhi koi hisaab nahi — pehla kagaz bhejiye 🌷",
    pinErr: "PIN sahi daal kar dobara dekhiye 🔑",
    locale: "hi-IN",
  },
  bn: {
    taglines: [
      "Prottek kagaj, apnar bhashay.",
      "Chobi tulun, aaram kore shunun.",
      "Bill hok ba prescription — sob sohoj.",
      "Boro akkhor, sposto awaaz, apon.",
    ],
    heroL1: "Kagaj bolbe,", heroL2: "apnar bhashay.",
    heroSub: "Bijli bill hok ba daktarer prescription — sudhu chobi tulun, ar shunun sohoj-sorol kothay. Boro button, sposto awaaz, kono jhamela nei.",
    ctaStart: "📷 Cholun, chobi tuli", ctaHow: "Eta kivabe kaaj kore?",
    ammaHi: "Nomoskar! 🙏", ammaSub: "Kono kagaj bujhte hole niche chap din",
    camTxt: "Chobi Tulun", pick: "🖼️ Gallery theke bachun", orWrite: "ba likhe pathan",
    ph: "Ekhane likhun… jemon: bijli bill 540 taka", send: "✉️ Pathan",
    kicker: "Apnar jonno bujhiye dilam", play: "▶ Shunun", pause: "⏸ Thaman",
    listening: "🔊 Shunchen…", replay: "▶ Abar shunun",
    again: "🔄 Notun chobi", del: "🗑️ Eta muche din",
    famH: "Poribarer diary 📒", famSub: "Ager kagaj, khoroch ar joruri nishan — sob ek jaygay.",
    pinPh: "Poribar PIN (jodi lagano thake)", load: "Dekhun", trendH: "Maasher khoroch",
    tabHome: "🏠 Sohaj", tabFam: "📚 Poribar",
    stages: { received: "Peyechi…", cleaning: "Porishkar korchi…", reading: "Porchi…", thinking: "Bujhchi…", speaking: "Bolchi…", done: "Hoye geche!", error: "Aare!" },
    notes: { received: "Chobi peye gechi, sudhu shuru korchi…", cleaning: "Dhulo-moila sariye porishkar korchi…", reading: "Akkhor-akkor pore porchi…", thinking: "Sohoj kothay bujhchi…", speaking: "Awaaz toiri korchi…", done: "Toiri! Niche shunun 🌼", error: "Dukkhito — abar chesta korun." },
    errRead: "Dukkhito, porte oshubidha holo. Alo te abar chobi tulun 🙏",
    ready: "Toiri! “Shunun” chepe shunun 🌼",
    deleted: "Muche dilam — apnar icchei prothom 🤍",
    writeFirst: "Age kichu likhun ✍️",
    defaultSummary: "Bujhiye diyechi, shune nin 🌼",
    okLine: "✅ Sob thik ache bole mone hocche",
    emptyTrend: (n, total) => n ? `Moṭ ${n} kagaj • ei charte ₹${Math.round(total).toLocaleString("en-IN")} hishab` : "Ekhono kono hishab nei — prothom kagaj pathan 🌷",
    pinErr: "PIN thik kore abar dekhun 🔑",
    locale: "bn-IN",
  },
};
const t = () => STRINGS[LANG];

const ORDER = ["cleaning", "reading", "thinking", "speaking", "done"];
let currentId = null;
let pollTimer = null;

/* ---------- cold-start splash ---------- */
async function warmup() {
  const splash = $("wake-splash");
  const ctrl = new AbortController();
  const to = setTimeout(() => splash.classList.remove("hidden"), 2500);
  try {
    await Promise.race([
      fetch("/api/ready", { signal: ctrl.signal }).then((r) => r.json()),
      new Promise((_, rej) => setTimeout(() => rej(new Error("t")), 9000)),
    ]);
  } catch { /* splash already showing; app still works */ }
  finally {
    clearTimeout(to);
    splash.classList.add("hidden");
    setTimeout(() => splash.remove(), 600);
  }
}

/* ---------- language ---------- */
function applyLang() {
  const s = t();
  document.documentElement.lang = LANG === "bn" ? "bn" : "hi";
  $("tagline-rot").textContent = s.taglines[0];
  $("hero-l1").textContent = s.heroL1;
  $("hero-l2").textContent = s.heroL2;
  $("hero-sub").textContent = s.heroSub;
  $("cta-start").textContent = s.ctaStart;
  $("cta-how").textContent = s.ctaHow;
  $("amma-hi").textContent = s.ammaHi;
  $("amma-sub").textContent = s.ammaSub;
  document.querySelector(".cam-txt").textContent = s.camTxt;
  $("btn-pick").textContent = s.pick;
  $("or-write").textContent = s.orWrite;
  $("text-input").placeholder = s.ph;
  $("btn-send").textContent = s.send;
  $("res-kicker").textContent = s.kicker;
  $("btn-again").textContent = s.again;
  $("btn-del").textContent = s.del;
  $("fam-h").textContent = s.famH;
  $("fam-sub").textContent = s.famSub;
  $("pin").placeholder = s.pinPh;
  $("btn-load").textContent = s.load;
  $("trend-h").textContent = s.trendH;
  $("tab-amma").textContent = s.tabHome;
  $("tab-family").textContent = s.tabFam;
  const hb = $("lang-hi"), bb = $("lang-bn");
  hb.classList.toggle("active", LANG === "hi");
  bb.classList.toggle("active", LANG === "bn");
  hb.setAttribute("aria-pressed", LANG === "hi");
  bb.setAttribute("aria-pressed", LANG === "bn");
}

function initLang() {
  applyLang();
  $("lang-hi").onclick = () => { LANG = "hi"; localStorage.setItem("bb-lang", "hi"); applyLang(); };
  $("lang-bn").onclick = () => { LANG = "bn"; localStorage.setItem("bb-lang", "bn"); applyLang(); };
}

/* ---------- mode tabs ---------- */
function initTabs() {
  const amma = $("tab-amma"), fam = $("tab-family");
  const va = $("view-amma"), vf = $("view-family");
  const go = (isAmma) => {
    amma.classList.toggle("active", isAmma);
    fam.classList.toggle("active", !isAmma);
    amma.setAttribute("aria-selected", isAmma);
    fam.setAttribute("aria-selected", !isAmma);
    va.classList.toggle("active", isAmma);
    vf.classList.toggle("active", !isAmma);
    if (!isAmma) loadFamily();
    window.scrollTo({ top: 0, behavior: calm() ? "auto" : "smooth" });
  };
  amma.onclick = () => go(true);
  fam.onclick = () => go(false);
}

/* ---------- scan flow ---------- */
function setSteps(stage) {
  document.querySelectorAll(".steps li").forEach((li) => {
    const s = li.dataset.s;
    li.classList.toggle("on", s === stage);
    li.classList.toggle("done", ORDER.indexOf(s) < ORDER.indexOf(stage));
  });
  $("proc-fill").style.width = `${(ORDER.indexOf(stage) / (ORDER.length - 1)) * 100}%`;
  $("proc-title").textContent = t().stages[stage] || t().stages.reading;
  $("proc-note").textContent = t().notes[stage] || "";
}

function showProc(show) {
  $("proc").classList.toggle("hidden", !show);
  if (show) { $("result").classList.add("hidden"); setSteps("received"); }
}

async function poll(id) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const st = await api.status(id);
      setSteps(st.stage);
      if (st.stage === "done") { clearInterval(pollTimer); showResult(id); }
      if (st.stage === "error") {
        clearInterval(pollTimer);
        showProc(false);
        toast(t().errRead);
      }
    } catch { /* retry next tick */ }
  }, 1500);
}

async function startScan(file) {
  if (!file) return;
  stopBrowser();
  currentId = null;
  showProc(true);
  $("proc").scrollIntoView({ behavior: calm() ? "auto" : "smooth", block: "center" });
  try {
    const { id } = await api.scanImage(file, LANG);
    currentId = id;
    poll(id);
  } catch (e) {
    showProc(false);
    toast(e.message);
  }
}

async function startText(text) {
  stopBrowser();
  showProc(true);
  try {
    const { id } = await api.scanText(text, LANG);
    currentId = id;
    poll(id);
  } catch (e) {
    showProc(false);
    toast(e.message);
  }
}

async function showResult(id) {
  try {
    const r = await api.result(id);
    showProc(false);
    const card = $("result");
    card.classList.remove("hidden");
    lampSweep(card);
    await typewriter($("res-summary"), r.explanation.summary_hi || t().defaultSummary);
    revealPoints($("res-points"), r.explanation.key_points_hi || []);
    if (r.anomaly) { $("res-flag-t").textContent = r.anomaly; flagShake($("res-flag")); }
    else $("res-flag").classList.add("hidden");
    $("res-action").textContent = r.explanation.action_hi ? "👉 " + r.explanation.action_hi : "";
    const disc = r.explanation.disclaimer_hi;
    $("res-disc").classList.toggle("hidden", !disc);
    if (disc) $("res-disc").textContent = "🩺 " + disc;

    // Voice: server audio first, phone voice as warm backup.
    const audio = $("audio");
    attachWave(audio, $("wave"));
    const btn = $("btn-play");
    const speakText = [r.explanation.summary_hi, ...(r.explanation.key_points_hi || []).slice(0, 3), r.anomaly || ""].join(" ");
    let serverOk = false;
    if (r.has_audio) {
      try {
        audio.src = api.audioUrl(id);
        await audio.play();
        serverOk = true;
        btn.textContent = t().pause;
      } catch { serverOk = false; }
    }
    btn.onclick = async () => {
      if (!audio.paused) { audio.pause(); stopBrowser(); btn.textContent = t().play; return; }
      if (serverOk || r.has_audio) {
        try { audio.src = api.audioUrl(id); await audio.play(); btn.textContent = t().pause; return; }
        catch { /* fall through to browser voice */ }
      }
      btn.textContent = t().listening;
      await speakBrowser(speakText, LANG);
      btn.textContent = t().replay;
    };
    audio.onended = () => { btn.textContent = t().replay; };
    audio.onpause = () => { if (btn.textContent.startsWith("⏸")) btn.textContent = t().play; };
    if (!serverOk) {
      btn.textContent = t().play;
      toast(t().ready);
    }
    card.scrollIntoView({ behavior: calm() ? "auto" : "smooth", block: "start" });
  } catch (e) {
    showProc(false);
    toast(e.message);
  }
}

/* ---------- family mode ---------- */
const TYPE_NAME = {
  hi: {
    electricity_bill: "⚡ Bijli bill", water_bill: "💧 Paani bill", gas_bill: "🔥 Gas bill",
    phone_bill: "📱 Phone bill", medical_prescription: "🩺 Doctor ka parcha",
    medicine_strip: "💊 Dawa ki patti", receipt: "🧾 Raseed", unknown: "📄 Kagaz",
  },
  bn: {
    electricity_bill: "⚡ Bijli bill", water_bill: "💧 Joler bill", gas_bill: "🔥 Gas bill",
    phone_bill: "📱 Phone bill", medical_prescription: "🩺 Daktarer prescription",
    medicine_strip: "💊 Oshudher pata", receipt: "🧾 Roshid", unknown: "📄 Kagaj",
  },
};

async function loadFamily() {
  const box = $("cards");
  try {
    const [items, trends] = await Promise.all([api.history(), api.trends()]);
    sparkline($("spark"), trends.monthly || []);
    const total = (trends.monthly || []).reduce((a, m) => a + m.total, 0);
    $("trend-note").textContent = t().emptyTrend(items.length, total);
    box.innerHTML = "";
    const names = TYPE_NAME[LANG];
    items.forEach((d) => {
      const el = document.createElement("div");
      el.className = "doc-card" + (d.anomaly ? " flagged" : "");
      el.innerHTML = `<div class="t">${names[d.doc_type] || names.unknown}</div>
        <div class="amt">${d.amount != null ? "₹" + Number(d.amount).toLocaleString("en-IN") : "—"}</div>
        <p class="sum">${d.summary || ""}</p>
        ${d.anomaly ? `<p>⚠️ ${d.anomaly}</p>` : `<p>${t().okLine}</p>`}
        <small>${d.created_at ? new Date(d.created_at).toLocaleDateString(t().locale) : ""}</small>`;
      box.appendChild(el);
    });
    flipIn([...box.children]);
  } catch (e) {
    $("trend-note").textContent = e.message.includes("PIN") ? t().pinErr : e.message;
  }
}

/* ---------- wire up ---------- */
function initInputs() {
  const cam = $("file-input"), pick = $("file-pick");
  $("btn-camera").onclick = () => cam.click();
  $("btn-pick").onclick = () => pick.click();
  cam.onchange = () => startScan(cam.files[0]);
  pick.onchange = () => startScan(pick.files[0]);
  $("text-form").onsubmit = (e) => {
    e.preventDefault();
    const v = $("text-input").value.trim();
    if (!v) return toast(t().writeFirst);
    $("text-input").value = "";
    startText(v);
  };
  $("cta-start").onclick = () =>
    $("view-amma").scrollIntoView({ behavior: calm() ? "auto" : "smooth" });
  $("cta-how").onclick = () => $("how-strip").classList.toggle("hidden");
  $("btn-again").onclick = () => {
    stopBrowser();
    $("result").classList.add("hidden");
    window.scrollTo({ top: 0, behavior: calm() ? "auto" : "smooth" });
  };
  $("btn-del").onclick = async () => {
    if (!currentId) return;
    try {
      await api.remove(currentId);
      stopBrowser();
      $("result").classList.add("hidden");
      toast(t().deleted);
    } catch (e) { toast(e.message); }
  };
  $("btn-load").onclick = loadFamily;
  $("pin").addEventListener("keydown", (e) => { if (e.key === "Enter") loadFamily(); });
}

function initPWA() {
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () =>
      navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }
}

document.addEventListener("DOMContentLoaded", () => {
  warmup();
  initLang();
  initTabs();
  initInputs();
  initPWA();
  initHero();
  rotateTagline($("tagline-rot"), () => t().taglines);
  introReveals();
});
