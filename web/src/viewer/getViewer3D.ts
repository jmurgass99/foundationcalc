import * as THREE from "three";
import { FoundationResult } from "../data-model.ts";

export function createFoundationViewer3D(container: HTMLElement): {
  update: (widthBM: number, res: FoundationResult) => void;
} {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x080d14);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
  camera.position.set(7.5, 4.0, 9.5);
  camera.lookAt(0, -3.0, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  container.appendChild(renderer.domElement);

  const ambient = new THREE.AmbientLight(0xffffff, 0.72);
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(8, 12, 10);
  scene.add(ambient, dir);

  const group = new THREE.Group();
  scene.add(group);

  const resize = () => {
    const w = container.clientWidth || 640;
    const h = container.clientHeight || 480;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  };
  window.addEventListener("resize", resize);
  setTimeout(resize, 0);

  const animate = () => {
    requestAnimationFrame(animate);
    group.rotation.y += 0.0025;
    renderer.render(scene, camera);
  };
  animate();

  return {
    update(widthBM: number, res: FoundationResult) {
      while (group.children.length > 0) group.remove(group.children[0]);

      // Zapata de hormigón armado + pedestal
      const footingGeo = new THREE.BoxGeometry(widthBM, 0.6, widthBM);
      const footingMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, roughness: 0.45 });
      const footingMesh = new THREE.Mesh(footingGeo, footingMat);
      footingMesh.position.set(0, 0.3, 0);
      group.add(footingMesh);

      const colGeo = new THREE.BoxGeometry(widthBM * 0.25, 1.4, widthBM * 0.25);
      const colMesh = new THREE.Mesh(colGeo, footingMat);
      colMesh.position.set(0, 1.3, 0);
      group.add(colMesh);

      // Subcapas discretas del bulbo 2:1 coloreadas por exceso de presión intersticial u(z,t)
      const qMax = Math.max(res.qMaxBulbKpa, 1);
      for (const s of res.sublayers) {
        const wZ = widthBM + s.zMidM;
        const ratio = Math.min(1, s.excessPorePressureKpa / qMax);
        const color = new THREE.Color().setHSL(0.58 - 0.52 * ratio, 0.85, 0.48);
        const slabGeo = new THREE.BoxGeometry(wZ, s.dzM * 0.92, wZ);
        const slabMat = new THREE.MeshStandardMaterial({
          color,
          transparent: true,
          opacity: 0.68,
        });
        const slab = new THREE.Mesh(slabGeo, slabMat);
        slab.position.set(0, -s.zMidM, 0);
        group.add(slab);
      }
    },
  };
}
