/* Gentle 3D paper hero — a floating card that unfolds on click.
   Lazy, lightweight, skipped entirely under reduced-motion or no WebGL. */
export function initHero() {
  const canvas = document.getElementById("paper3d");
  if (!canvas || !window.THREE) return;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    canvas.parentElement.style.display = "none";
    return;
  }
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, alpha: true, antialias: true });
  } catch { canvas.parentElement.style.display = "none"; return; }
  const scene = new THREE.Scene();
  const cam = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
  cam.position.set(0, 0.4, 4.2);

  scene.add(new THREE.AmbientLight(0xfff2dd, 0.9));
  const lamp = new THREE.PointLight(0xffb84d, 12, 20);
  lamp.position.set(1.5, 2.5, 2.5);
  scene.add(lamp);

  // Paper = warm plane with soft fold illusion (two planes, slight angle).
  const paperMat = new THREE.MeshStandardMaterial({ color: 0xf7f1e3, roughness: 0.9 });
  const group = new THREE.Group();
  const top = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.1, 1, 1), paperMat);
  top.position.y = 0.55;
  const bottom = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 1.1, 1, 1), paperMat);
  bottom.position.y = -0.55;
  group.add(top, bottom);
  // Amber text-lines drawn as thin boxes on the paper.
  const lineMat = new THREE.MeshBasicMaterial({ color: 0xc98f2e });
  for (let i = 0; i < 5; i++) {
    const w = 1.6 - i * 0.18;
    const line = new THREE.Mesh(new THREE.BoxGeometry(w, 0.045, 0.01), lineMat);
    line.position.set(-0.15 + (i % 2) * 0.1, 0.85 - i * 0.22, 0.012);
    group.add(line);
  }
  scene.add(group);

  const resize = () => {
    const r = canvas.parentElement.getBoundingClientRect();
    renderer.setSize(r.width, r.height, false);
    cam.aspect = r.width / Math.max(r.height, 1);
    cam.updateProjectionMatrix();
  };
  resize();
  window.addEventListener("resize", resize);

  let mx = 0, my = 0, unfolded = 0.35;
  window.addEventListener("pointermove", (e) => {
    mx = (e.clientX / window.innerWidth - 0.5) * 0.6;
    my = (e.clientY / window.innerHeight - 0.5) * 0.4;
  });
  document.getElementById("cta-start")?.addEventListener("click", () => { unfolded = 0.02; });

  const clock = new THREE.Clock();
  (function loop() {
    requestAnimationFrame(loop);
    const t = clock.getElapsedTime();
    group.rotation.y += ((mx + Math.sin(t * 0.4) * 0.12) - group.rotation.y) * 0.05;
    group.rotation.x += ((my + 0.1) - group.rotation.x) * 0.05;
    group.position.y = Math.sin(t * 0.8) * 0.08;
    top.rotation.x += (unfolded - top.rotation.x) * 0.04;
    bottom.rotation.x += (-unfolded - bottom.rotation.x) * 0.04;
    renderer.render(scene, cam);
  })();

  // Settle the fold shortly after load for the "unfolding" moment.
  setTimeout(() => { unfolded = 0.02; }, 900);
}
