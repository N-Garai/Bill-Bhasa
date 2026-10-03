/* BillBhasha app controller — Saral + Parivar modes, scan flow, voice.
   Bilingual: Hindi (hi) + Bangla (bn). Toggle on the Saral card. */
import { api, famCode, setFamCode } from "./api.js";
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
if (!["hi", "bn", "en"].includes(LANG)) LANG = "hi";
let slowMode = localStorage.getItem("bb-slow") === "1";

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
    slow: "🐢 Dheere", normal: "⚡ Normal",
    detSum: "Photo se kya padha gaya (details)",
    stageHead: "Charan",
    listening: "🔊 Sun rahe hain…", replay: "▶ Dobara suniye",
    again: "🔄 Naya photo", del: "🗑️ Ye hata dijiye",
    famH: "Parivar ki diary 📒", famSub: "Pichhle kagaz, kharcha aur zaroori nishaan — sab ek jagah.",
    pinPh: "Parivar PIN (agar lagaya ho)", load: "Dekhiye", trendH: "Mahine ka kharcha",
    tabHome: "🏠 Saral", tabFam: "📚 Parivar",
    stages: { received: "Mil gaya…", cleaning: "Saaf kar rahe…", reading: "Padh rahe…", thinking: "Samajh rahe…", speaking: "Bole rahe…", done: "Ho gaya!", error: "Arre!" },
    stepNames: { cleaning: "Saaf kar rahe", reading: "Padh rahe", thinking: "Samajh rahe", speaking: "Bole rahe", done: "Ho gaya" },
    notes: { received: "Photo mil gayi, bas shuru kar rahe hain…", cleaning: "Dhool-mitti hata kar saaf kar rahe hain…", reading: "Line by line padh rahe hain…", thinking: "Saral shabdon mein samajh rahe hain…", speaking: "Awaaz taiyaar kar rahe hain…", done: "Taiyaar! Neeche suniye 🌼", error: "Maaf kijiye — dobara koshish kijiye." },
    errRead: "Maaf kijiye, padhne mein dikkat aayi. Roshni mein dobara photo lijiye 🙏",
    ready: "Taiyaar hai! “Suniye” dabakar suniye 🌼",
    deleted: "Hata diya — aapki marzi sabse pehle 🤍",
    writeFirst: "Pehle kuch likhiye ✍️",
    defaultSummary: "Samjha diya hai, sun lijiye 🌼",
    okLine: "✅ Sab theek lag raha hai",
    emptyTrend: (n, total) => n ? `Kul ${n} kagaz • is chart mein ₹${Math.round(total).toLocaleString("en-IN")} ka hisaab` : "Abhi koi hisaab nahi — pehla kagaz bhejiye 🌷",
    pinErr: "PIN sahi daal kar dobara dekhiye 🔑",
    locale: "hi-IN",
    spaceH: "🔐 Apni niji jagah",
    spaceSub: "Har visitor ki apni alag diary hoti hai.",
    spaceCode: "Aapka family code:",
    lblPin: "Apna PIN lagayein (4+ ank)",
    setPin: "PIN rakhein",
    lblJoin: "Rishtedaar ka code jodiye",
    joinBtn: "Jodiye",
    joinCodePh: "CODE-12AB",
    pinSaved: "PIN rakh diya 🔐 Ab is PIN ke bina koi nahi dekh payega.",
    pinNeed: "4 ya zyada ank ka PIN dijiye.",
    pinWrong: "PIN galat hai 🔑",
    joined: "Jud gaye! Ab diary shared hai 🤝",
    joinFail: "Code ya PIN galat — dobara dekhiye.",
    needPinFirst: "Is jagah par PIN laga hai — upar PIN daal kar “Dekhiye” dabaiye 🔑",
    otherLang: "Ye jawab scan wali bhasha mein hai — bhasha badal kar dobara bhejein 🌐",
    copy: "📋 Copy", copied: "✓ Code copy ho gaya — sambhal kar rakhiye",
    errTitle: "Maaf kijiye — photo padha nahi ja saka 😔",
    errTechHead: "Takneeki wajah",
    footDesc: "Photo kheenchiye, suniye, samjhiye — bill, parcha aur raseed, seedhe-saral shabdon mein.",
    footExplore: "Dekhiye", footTrust: "Bharosa",
    trust1: "🔒 Har visitor ki apni niji jagah",
    trust2: "🗑️ Hataane par turant mit jata hai",
    trust3: "👤 Bina account ke chalta hai",
    footRights: "© 2026 BillBhasha • Parivar ke liye, pyaar se 🤍",
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
    slow: "🐢 Aste", normal: "⚡ Sadharon",
    detSum: "Chobi theke ki pora holo (details)",
    stageHead: "Dhap",
    listening: "🔊 Shunchen…", replay: "▶ Abar shunun",
    again: "🔄 Notun chobi", del: "🗑️ Eta muche din",
    famH: "Poribarer diary 📒", famSub: "Ager kagaj, khoroch ar joruri nishan — sob ek jaygay.",
    pinPh: "Poribar PIN (jodi lagano thake)", load: "Dekhun", trendH: "Maasher khoroch",
    tabHome: "🏠 Sohaj", tabFam: "📚 Poribar",
    stages: { received: "Peyechi…", cleaning: "Porishkar korchi…", reading: "Porchi…", thinking: "Bujhchi…", speaking: "Bolchi…", done: "Hoye geche!", error: "Aare!" },
    stepNames: { cleaning: "Porishkar korchi", reading: "Porchi", thinking: "Bujhchi", speaking: "Bolchi", done: "Hoye geche" },
    notes: { received: "Chobi peye gechi, sudhu shuru korchi…", cleaning: "Dhulo-moila sariye porishkar korchi…", reading: "Line dhore dhore porchi…", thinking: "Sohoj kothay bujhchi…", speaking: "Awaaz toiri korchi…", done: "Toiri! Niche shunun 🌼", error: "Dukkhito — abar chesta korun." },
    errRead: "Dukkhito, porte oshubidha holo. Alo te abar chobi tulun 🙏",
    ready: "Toiri! “Shunun” chepe shunun 🌼",
    deleted: "Muche dilam — apnar icchei prothom 🤍",
    writeFirst: "Age kichu likhun ✍️",
    defaultSummary: "Bujhiye diyechi, shune nin 🌼",
    okLine: "✅ Sob thik ache bole mone hocche",
    emptyTrend: (n, total) => n ? `Moṭ ${n} kagaj • ei charte ₹${Math.round(total).toLocaleString("en-IN")} hishab` : "Ekhono kono hishab nei — prothom kagaj pathan 🌷",
    pinErr: "PIN thik kore abar dekhun 🔑",
    locale: "bn-IN",
    spaceH: "🔐 Nijer byaktigoto jayga",
    spaceSub: "Prottek dorshoker nijossho alada diary thake.",
    spaceCode: "Apnar family code:",
    lblPin: "Nijer PIN din (4+ songkha)",
    setPin: "PIN rakhun",
    lblJoin: "Attiyer code jog korun",
    joinBtn: "Jog korun",
    joinCodePh: "CODE-12AB",
    pinSaved: "PIN rekhe deoa hoyeche 🔐 Ebar theke ei PIN chara keu dekhte parbe na.",
    pinNeed: "4 ba tar beshi songkhar PIN din.",
    pinWrong: "PIN vul hoyeche 🔑",
    joined: "Jog hoye geche! Ebar shared diary dekhun 🤝",
    joinFail: "Code ba PIN vul — abar dekhun.",
    needPinFirst: "Ei jagay PIN lagano — upore PIN diye “Dekhun” chapun 🔑",
    otherLang: "Ei uttor scan-er bhashay ache — bhasha bodle abar pathan 🌐",
    copy: "📋 Copy", copied: "✓ Code copy hoye geche — jotno kore rakhun",
    errTitle: "Dukkhito — chobi pora jayni 😔",
    errTechHead: "Karigori karon",
    footDesc: "Chobi tulun, shunun, bujhun — bill, prescription ar roshid, sohoj-sorol kothay.",
    footExplore: "Dekhun", footTrust: "Bishwash",
    trust1: "🔒 Prottek dorshoker nijer jayga",
    trust2: "🗑️ Muchle turonto muche jay",
    trust3: "👤 Account charai chole",
    footRights: "© 2026 BillBhasha • Poribarer jonno, bhalobasha diye 🤍",
  },
  en: {
    taglines: [
      "Every paper, in your language.",
      "Snap a photo, listen with ease.",
      "Bills or prescriptions — all simple.",
      "Big words, clear voice, warm care.",
    ],
    heroL1: "Paper speaks,", heroL2: "your language.",
    heroSub: "Electricity bill or doctor's prescription — just take a photo and hear it in simple words. Big buttons, clear voice, zero confusion.",
    ctaStart: "📷 Let's take a photo", ctaHow: "How does it work?",
    ammaHi: "Hello! 🙏", ammaSub: "To understand any paper, press below",
    camTxt: "Take Photo", pick: "🖼️ Choose from gallery", orWrite: "or write it here",
    ph: "Write here… e.g.: electricity bill 540 rupees", send: "✉️ Send",
    kicker: "Explained for you", play: "▶ Listen", pause: "⏸ Pause",
    slow: "🐢 Slow", normal: "⚡ Normal",
    detSum: "What the photo gave us (details)",
    stageHead: "Stages",
    listening: "🔊 Listening…", replay: "▶ Listen again",
    again: "🔄 New photo", del: "🗑️ Delete this",
    famH: "Family diary 📒", famSub: "Past papers, spending and important flags — all in one place.",
    pinPh: "Family PIN (if set)", load: "View", trendH: "Monthly spending",
    tabHome: "🏠 Simple", tabFam: "📚 Family",
    stages: { received: "Got it…", cleaning: "Cleaning…", reading: "Reading…", thinking: "Understanding…", speaking: "Speaking…", done: "Done!", error: "Oops!" },
    stepNames: { cleaning: "Cleaning", reading: "Reading", thinking: "Understanding", speaking: "Speaking", done: "Done" },
    notes: { received: "Photo received, just starting…", cleaning: "Wiping off dust and cleaning…", reading: "Reading line by line…", thinking: "Understanding in simple words…", speaking: "Preparing the voice…", done: "Ready! Listen below 🌼", error: "Sorry — please try again." },
    errRead: "Sorry, had trouble reading. Please retake the photo in better light 🙏",
    ready: "Ready! Press “Listen” to hear it 🌼",
    deleted: "Deleted — your wish comes first 🤍",
    writeFirst: "Please write something first ✍️",
    defaultSummary: "Explained — have a listen 🌼",
    okLine: "✅ Everything looks fine",
    emptyTrend: (n, total) => n ? `${n} papers • ₹${Math.round(total).toLocaleString("en-IN")} accounted here` : "No records yet — send your first paper 🌷",
    pinErr: "Enter the correct PIN and try again 🔑",
    locale: "en-IN",
    spaceH: "🔐 Your private space",
    spaceSub: "Every visitor gets their own separate diary.",
    spaceCode: "Your family code:",
    lblPin: "Set your own PIN (4+ digits)",
    setPin: "Save PIN",
    lblJoin: "Join a relative's code",
    joinBtn: "Join",
    joinCodePh: "CODE-12AB",
    pinSaved: "PIN saved 🔐 Nobody can view this space without it now.",
    pinNeed: "Please use a PIN of 4 or more digits.",
    pinWrong: "Wrong PIN 🔑",
    joined: "Joined! Now you share one diary 🤝",
    joinFail: "Wrong code or PIN — check again.",
    needPinFirst: "This space has a PIN — enter it above and press “View” 🔑",
    otherLang: "This answer is in the scan's language — switch language and resend 🌐",
    copy: "📋 Copy", copied: "✓ Code copied — keep it safe",
    errTitle: "Sorry — couldn't read the photo 😔",
    errTechHead: "Technical reason",
    footDesc: "Snap, listen, understand — bills, prescriptions and receipts in simple words.",
    footExplore: "Explore", footTrust: "Trust",
    trust1: "🔒 Every visitor gets a private space",
    trust2: "🗑️ Deleted means gone at once",
    trust3: "👤 No account needed",
    footRights: "© 2026 BillBhasha • Made with care for family 🤍",
  },
};
const t = () => STRINGS[LANG];

const ORDER = ["cleaning", "reading", "thinking", "speaking", "done"];
let currentId = null;
let pollTimer = null;

/* ---------- cold-start splash ---------- */
let serverBuild = "";
async function warmup() {
  const splash = $("wake-splash");
  const ctrl = new AbortController();
  const to = setTimeout(() => splash.classList.remove("hidden"), 2500);
  try {
    await Promise.race([
      fetch("/api/ready", { signal: ctrl.signal }).then((r) => r.json()),
      new Promise((_, rej) => setTimeout(() => rej(new Error("t")), 9000)),
    ]);
    api.health().then((h) => { serverBuild = h.build || ""; }).catch(() => {});
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
  document.documentElement.lang = LANG;
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
  const spd = $("btn-speed");
  spd.textContent = slowMode ? s.normal : s.slow;
  spd.classList.toggle("on", slowMode);
  $("btn-again").textContent = s.again;
  $("btn-del").textContent = s.del;
  $("fam-h").textContent = s.famH;
  $("fam-sub").textContent = s.famSub;
  $("pin").placeholder = s.pinPh;
  $("btn-load").textContent = s.load;
  $("trend-h").textContent = s.trendH;
  $("tab-amma").textContent = s.tabHome;
  $("tab-family").textContent = s.tabFam;
  $("space-h").textContent = s.spaceH;
  $("space-sub").textContent = s.spaceSub;
  $("space-code-line").childNodes[0].textContent = s.spaceCode + " ";
  $("lbl-newpin").textContent = s.lblPin;
  $("btn-setpin").textContent = s.setPin;
  $("lbl-join").textContent = s.lblJoin;
  $("btn-join").textContent = s.joinBtn;
  $("join-code").placeholder = s.joinCodePh;
  $("btn-copy").textContent = s.copy;
  $("foot-desc").textContent = s.footDesc;
  $("foot-explore").textContent = s.footExplore;
  $("foot-saral").textContent = s.tabHome;
  $("foot-fam").textContent = s.tabFam;
  $("foot-how").textContent = s.ctaHow;
  $("foot-trust").textContent = s.footTrust;
  $("trust1").textContent = s.trust1;
  $("trust2").textContent = s.trust2;
  $("trust3").textContent = s.trust3;
  $("foot-rights").textContent = s.footRights;
  document.querySelectorAll(".steps li").forEach((li) => {
    const name = s.stepNames[li.dataset.s];
    if (name) li.querySelector("span").textContent = name;
  });
  const pills = { hi: $("lang-hi"), bn: $("lang-bn"), en: $("lang-en") };
  for (const [k, b] of Object.entries(pills)) {
    b.classList.toggle("active", LANG === k);
    b.setAttribute("aria-pressed", LANG === k);
  }
}

function initLang() {
  applyLang();
  const set = (l) => { LANG = l; localStorage.setItem("bb-lang", l); applyLang(); };
  $("lang-hi").onclick = () => set("hi");
  $("lang-bn").onclick = () => set("bn");
  $("lang-en").onclick = () => set("en");
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
  $("foot-saral").onclick = () => go(true);
  $("foot-fam").onclick = () => go(false);
}

/* ---------- scan flow ---------- */
/* Shrink big phone photos in the browser: faster upload + much faster OCR
   on tiny servers. Falls back to the original file on any error. */
function shrinkImage(file, maxSide = 1280) {
  return new Promise((resolve) => {
    try {
      if (!file || !file.type.startsWith("image/")) return resolve(file);
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        try {
          const scale = Math.min(1, maxSide / Math.max(img.width, img.height));
          if (scale >= 1 && file.size < 900 * 1024) {
            URL.revokeObjectURL(url);
            return resolve(file);
          }
          const c = document.createElement("canvas");
          c.width = Math.max(1, Math.round(img.width * scale));
          c.height = Math.max(1, Math.round(img.height * scale));
          c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
          URL.revokeObjectURL(url);
          c.toBlob((b) => resolve(b || file), "image/jpeg", 0.82);
        } catch { URL.revokeObjectURL(url); resolve(file); }
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
      img.src = url;
    } catch { resolve(file); }
  });
}

let scanT0 = 0;
function tickClock() {
  const el = $("proc-time");
  if (el && !$("proc").classList.contains("hidden")) {
    el.textContent = "⏱ " + Math.max(0, Math.round((Date.now() - scanT0) / 1000)) + "s";
  }
}
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
  if (show) {
    $("result").classList.add("hidden");
    $("errbox").classList.add("hidden");
    setSteps("received");
  }
}

function showLocalError(msg) {
  $("err-title").textContent = t().errTitle;
  $("err-tech").textContent = t().errTechHead + ": " + msg;
  $("errbox").classList.remove("hidden");
  toast(msg);
  $("errbox").scrollIntoView({ behavior: calm() ? "auto" : "smooth", block: "center" });
}

function showError(st) {
  const tech = (st.timings && st.timings.error) || st.stage;
  $("err-title").textContent = t().errTitle;
  $("err-tech").textContent = t().errTechHead + ": " + tech;
  $("errbox").classList.remove("hidden");
  toast(t().errRead);
  $("errbox").scrollIntoView({ behavior: calm() ? "auto" : "smooth", block: "center" });
}

async function poll(id) {
  clearInterval(pollTimer);
  scanT0 = Date.now();
  $("proc-time").textContent = "⏱ 0s";
  pollTimer = setInterval(async () => {
    tickClock();
    try {
      const st = await api.status(id);
      setSteps(st.stage);
      if (st.stage === "done") { clearInterval(pollTimer); showResult(id); }
      if (st.stage === "error") {
        clearInterval(pollTimer);
        showProc(false);
        showError(st);
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
    const small = await shrinkImage(file);
    const { id } = await api.scanImage(small, LANG);
    currentId = id;
    poll(id);
  } catch (e) {
    showProc(false);
    showLocalError(e.message);
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
    showLocalError(e.message);
  }
}

async function showResult(id) {
  try {
    const r = await api.result(id);
    showProc(false);
    $("errbox").classList.add("hidden");
    // The answer keeps the language chosen at scan time; say so if the
    // user switched languages mid-scan (avoids "wrong language" confusion).
    if ((r.language || "hi").slice(0, 2) !== LANG) toast(t().otherLang);
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
    $("det-sum").textContent = t().detSum;
    $("ocr-prev").textContent =
      (r.ocr_preview || "—") + (r.ocr_confidence ? `  •  ${Math.round(r.ocr_confidence)}%` : "");
    $("stage-line").textContent = t().stageHead + ": " +
      Object.entries(r.stage_timings || {}).map(([k, v]) => `${k}=${v}`).join(" • ") +
      (serverBuild ? ` • srv=${serverBuild}` : "");

    // Voice: server audio first, phone voice as warm backup.
    const audio = $("audio");
    attachWave(audio, $("wave"));
    const btn = $("btn-play");
    const spd = $("btn-speed");
    const rate = () => (slowMode ? 0.72 : 1);
    spd.onclick = () => {
      slowMode = !slowMode;
      localStorage.setItem("bb-slow", slowMode ? "1" : "0");
      spd.textContent = slowMode ? t().normal : t().slow;
      spd.classList.toggle("on", slowMode);
      try { audio.playbackRate = slowMode ? 0.75 : 1; } catch { /* noop */ }
    };
    const speakText = r.explanation.speech_text ||
      [r.explanation.summary_hi, ...(r.explanation.key_points_hi || []).slice(0, 3), r.anomaly || ""].join(" ");
    let serverOk = false;
    if (r.has_audio) {
      try {
        audio.src = api.audioUrl(id);
        try { audio.playbackRate = slowMode ? 0.75 : 1; } catch { /* noop */ }
        await audio.play();
        serverOk = true;
        btn.textContent = t().pause;
      } catch { serverOk = false; }
    }
    btn.onclick = async () => {
      if (!audio.paused) { audio.pause(); stopBrowser(); btn.textContent = t().play; return; }
      if (serverOk || r.has_audio) {
        try {
          audio.src = api.audioUrl(id);
          try { audio.playbackRate = slowMode ? 0.75 : 1; } catch { /* noop */ }
          await audio.play(); btn.textContent = t().pause; return;
        }
        catch { /* fall through to browser voice */ }
      }
      btn.textContent = t().listening;
      await speakBrowser(speakText, LANG, rate());
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
  en: {
    electricity_bill: "⚡ Electricity bill", water_bill: "💧 Water bill", gas_bill: "🔥 Gas bill",
    phone_bill: "📱 Phone bill", medical_prescription: "🩺 Doctor's prescription",
    medicine_strip: "💊 Medicine strip", receipt: "🧾 Receipt", unknown: "📄 Paper",
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
    $("trend-note").textContent = e.status === 401 ? t().needPinFirst
      : e.message.includes("PIN") ? t().pinErr : e.message;
  }
}

/* ---------- my private space ---------- */
async function ensureSpace() {
  try {
    const r = await api.familyEnsure(
      localStorage.getItem("bb-family") && localStorage.getItem("bb-family") !== "default"
        ? localStorage.getItem("bb-family") : null);
    setFamCode(r.code);
    $("space-code").textContent = r.code;
  } catch { $("space-code").textContent = famCode(); }
}

function initSpace() {
  $("btn-copy").onclick = async () => {
    try {
      await navigator.clipboard.writeText(famCode());
      $("space-msg").textContent = t().copied;
    } catch {
      $("space-msg").textContent = famCode();
    }
  };
  $("btn-setpin").onclick = async () => {
    const np = $("new-pin").value.trim();
    $("space-msg").textContent = "";
    if (np.length < 4) { $("space-msg").textContent = t().pinNeed; return; }
    try {
      const cur = $("pin").value.trim();
      await api.familyPin(famCode(), cur, np);
      $("new-pin").value = "";
      $("space-msg").textContent = t().pinSaved;
      loadFamily();
    } catch (e) {
      $("space-msg").textContent = e.status === 401 ? t().pinWrong : e.message;
    }
  };
  $("btn-join").onclick = async () => {
    const code = $("join-code").value.trim();
    const pin = $("join-pin").value.trim();
    $("space-msg").textContent = "";
    if (!code) return;
    try {
      const r = await api.familyJoin(code, pin);
      setFamCode(r.code);
      $("space-code").textContent = r.code;
      $("join-code").value = ""; $("join-pin").value = "";
      $("space-msg").textContent = t().joined;
      loadFamily();
    } catch {
      $("space-msg").textContent = t().joinFail;
    }
  };
}

/* ---------- wire up ---------- */
function initInputs() {
  const cam = $("file-input"), pick = $("file-pick");
  $("btn-camera").onclick = () => cam.click();
  $("btn-pick").onclick = () => pick.click();
  // Reset the inputs so picking the SAME file twice still fires change.
  cam.onchange = () => { const f = cam.files[0]; cam.value = ""; startScan(f); };
  pick.onchange = () => { const f = pick.files[0]; pick.value = ""; startScan(f); };
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
  $("foot-how").onclick = () => {
    $("how-strip").classList.remove("hidden");
    window.scrollTo({ top: 0, behavior: calm() ? "auto" : "smooth" });
  };
  $("btn-again").onclick = () => {
    stopBrowser();
    $("result").classList.add("hidden");
    window.scrollTo({ top: 0, behavior: calm() ? "auto" : "smooth" });
  };
  $("btn-retry").onclick = () => {
    stopBrowser();
    $("errbox").classList.add("hidden");
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
  initSpace();
  ensureSpace();
  initPWA();
  initHero();
  rotateTagline($("tagline-rot"), () => t().taglines);
  introReveals();
});
