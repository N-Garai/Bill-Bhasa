/* Soothing motion: tagline rotation, typewriter, staged reveals,
   live waveform, sparklines. All respect prefers-reduced-motion. */
export const calm = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const LINES = [
  "Har kagaz, aapki bhasha mein.",
  "Photo lijiye, aaraam se suniye.",
  "Bill ho ya parcha — sab saral.",
  "Bade shabd, saaf awaaz, apnapan.",
];

export function rotateTagline(el, getLines = null) {
  if (!el || calm()) return;
  const lines = () => (getLines ? getLines() : LINES);
  let i = 0;
  setInterval(() => {
    const arr = lines();
    i = (i + 1) % arr.length;
    if (window.gsap) {
      gsap.to(el, { opacity: 0, y: -6, duration: 0.3, onComplete: () => {
        el.textContent = arr[i];
        gsap.to(el, { opacity: 1, y: 0, duration: 0.4 });
      }});
    } else {
      el.textContent = arr[i];
    }
  }, 3600);
}

export function introReveals() {
  if (!window.gsap || calm()) return;
  gsap.from(".hero-title .line", { opacity: 0, y: 34, duration: 0.9, stagger: 0.15, ease: "power3.out" });
  gsap.from(".hero-sub, .hero-cta, .eyebrow", { opacity: 0, y: 20, duration: 0.7, stagger: 0.1, delay: 0.25 });
  gsap.from(".amma-card", { opacity: 0, y: 26, duration: 0.7, delay: 0.2 });
}

export function typewriter(el, text) {
  return new Promise((resolve) => {
    if (calm() || !text) { el.textContent = text || ""; return resolve(); }
    el.innerHTML = "";
    const caret = document.createElement("span");
    caret.className = "caret";
    let i = 0;
    const step = () => {
      el.textContent = text.slice(0, ++i);
      el.appendChild(caret);
      if (i < text.length) setTimeout(step, 18);
      else { caret.remove(); resolve(); }
    };
    step();
  });
}

export function revealPoints(list, points) {
  list.innerHTML = "";
  points.forEach((p) => {
    const li = document.createElement("li");
    li.textContent = "🌼 " + p;
    list.appendChild(li);
  });
  const items = [...list.children];
  if (!window.gsap || calm()) {
    items.forEach((li) => { li.style.opacity = 1; li.style.transform = "none"; });
    return;
  }
  gsap.to(items, { opacity: 1, y: 0, duration: 0.5, stagger: 0.18, ease: "power2.out", delay: 0.2 });
}

export function lampSweep(card) {
  if (!window.gsap || calm()) return;
  gsap.fromTo(card.querySelector(".res-glow"),
    { opacity: 0 }, { opacity: 1, duration: 1.2, ease: "sine.inOut" });
}

export function flagShake(flag) {
  flag.classList.remove("hidden");
  if (calm()) return;
  flag.classList.remove("shake");
  void flag.offsetWidth;
  flag.classList.add("shake");
}

/* --- live waveform synced to <audio> via AnalyserNode --- */
let actx = null;
export function attachWave(audio, waveEl) {
  const N = 36;
  waveEl.innerHTML = "";
  const bars = [];
  for (let i = 0; i < N; i++) { const b = document.createElement("i"); waveEl.appendChild(b); bars.push(b); }
  const idle = () => bars.forEach((b, i) => {
    b.style.height = calm() ? "30%" : `${18 + 10 * Math.abs(Math.sin(Date.now() / 500 + i / 2))}%`;
  });
  let timer = setInterval(() => { if (audio.paused) idle(); }, 120);
  idle();
  try {
    audio.addEventListener("play", () => {
      if (calm()) return;
      actx = actx || new (window.AudioContext || window.webkitAudioContext)();
      const src = actx.createMediaElementSource(audio);
      const an = actx.createAnalyser();
      an.fftSize = 64;
      src.connect(an); an.connect(actx.destination);
      const buf = new Uint8Array(an.frequencyBinCount);
      clearInterval(timer);
      const tick = () => {
        if (audio.paused) return requestAnimationFrame(tick);
        an.getByteFrequencyData(buf);
        bars.forEach((b, i) => {
          const v = buf[i % buf.length] / 255;
          b.style.height = `${12 + v * 88}%`;
        });
        requestAnimationFrame(tick);
      };
      tick();
    }, { once: true });
  } catch { /* pretty bars still animate */ }
}

/* --- sparkline for family trends --- */
export function sparkline(canvas, series) {
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  ctx.clearRect(0, 0, W, H);
  if (!series.length) {
    ctx.fillStyle = "#c9bfa8"; ctx.font = "16px Nunito";
    ctx.fillText("Abhi koi hisaab nahi — pehla kagaz bhejiye 🌷", 16, H / 2);
    return;
  }
  const max = Math.max(...series.map((s) => s.total), 1);
  ctx.strokeStyle = "#ffb84d"; ctx.lineWidth = 3; ctx.beginPath();
  series.forEach((s, i) => {
    const x = 20 + (i * (W - 40)) / Math.max(series.length - 1, 1);
    const y = H - 16 - (s.total / max) * (H - 40);
    i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.stroke();
  ctx.fillStyle = "#c9bfa8"; ctx.font = "13px Nunito";
  series.forEach((s, i) => {
    const x = 20 + (i * (W - 40)) / Math.max(series.length - 1, 1);
    ctx.fillText(s.month.slice(5), x - 8, H - 2);
  });
}

export function flipIn(cards) {
  if (!window.gsap || calm()) return;
  gsap.from(cards, { opacity: 0, rotationX: -35, y: 24, duration: 0.55, stagger: 0.08, ease: "back.out(1.4)" });
}
