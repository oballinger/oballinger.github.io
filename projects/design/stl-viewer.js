// Interactive STL viewer for design pages: drag to rotate, slow auto-spin.
// Loaded on demand by scrolly.js (and by the editor) the first time a model is shown.
import * as THREE from 'https://cdn.jsdelivr.net/npm/three@0.160.0/+esm';
import { STLLoader } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/loaders/STLLoader.js/+esm';
import { OrbitControls } from 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/controls/OrbitControls.js/+esm';

export function mount(el, url, opts) {
	opts = opts || {};
	if (el._stl) return el._stl;

	var renderer;
	try {
		renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
	} catch (e) {
		el.classList.add('is-error');
		return (el._stl = {});
	}
	renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
	renderer.outputColorSpace = THREE.SRGBColorSpace;
	el.appendChild(renderer.domElement);

	var scene = new THREE.Scene();
	scene.add(new THREE.HemisphereLight(0xffffff, 0x2a2c30, 1.6));
	var key = new THREE.DirectionalLight(0xffffff, 2.2);
	key.position.set(1, 1.4, 1.2);
	scene.add(key);
	var rim = new THREE.DirectionalLight(0xffffff, 0.8);
	rim.position.set(-1.2, 0.4, -1);
	scene.add(rim);

	var camera = new THREE.PerspectiveCamera(35, 1, 0.01, 1000);
	var controls = new OrbitControls(camera, renderer.domElement);
	controls.enableDamping = true;
	controls.enablePan = false;
	// On the page the wheel must keep scrolling, so zoom is only on in the editor.
	controls.enableZoom = !!opts.zoom;
	controls.autoRotate = true;
	controls.autoRotateSpeed = 1.2;
	// Let vertical swipes keep scrolling the page on touch screens; horizontal drags rotate.
	if (!opts.zoom) renderer.domElement.style.touchAction = 'pan-y';
	controls.addEventListener('start', function() { controls.autoRotate = false; });

	function resize() {
		var w = el.clientWidth, h = el.clientHeight;
		if (!w || !h) return;
		renderer.setSize(w, h, false);
		renderer.domElement.style.width = '100%';
		renderer.domElement.style.height = '100%';
		camera.aspect = w / h;
		camera.updateProjectionMatrix();
	}
	new ResizeObserver(resize).observe(el);
	resize();

	var material = function(geom, o) {
		o = o || {};
		// Binary STLs with per-facet colours (Materialise "COLOR=" header) keep their colours.
		return new THREE.MeshStandardMaterial({
			vertexColors: !!geom.hasColors, color: geom.hasColors ? 0xffffff : (o.color || 0xdedede),
			roughness: 0.55, metalness: 0.05,
			transparent: o.opacity < 1, opacity: o.opacity || 1
		});
	};

	// Fit the box as it spins about the vertical axis (its footprint radius across, its
	// height up), not the bounding sphere, so long or flat layouts don't start tiny.
	// data-zoom on the element scales that further.
	function frame(box) {
		var size = box.getSize(new THREE.Vector3());
		var rh = Math.hypot(size.x, size.z) / 2, hh = size.y / 2, r = Math.max(rh, hh);
		var tv = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)), th = tv * (camera.aspect || 1.6);
		var dist = (Math.max(hh / tv, rh / th) + rh * 0.5) * 1.1 / (parseFloat(el.getAttribute('data-zoom')) || 1);
		camera.position.set(dist * 0.66, dist * 0.35, dist * 0.66);
		camera.near = r / 100;
		camera.far = dist * 10;
		camera.updateProjectionMatrix();
		controls.minDistance = r * 1.2;
		controls.maxDistance = dist * 3;
		controls.target.set(0, 0, 0);
		controls.update();
		el.classList.add('is-loaded');
	}
	function fail() { el.classList.add('is-error'); }
	var loader = new STLLoader();
	var flights = null;   // mushrooms flying in (scene.json parts with flyIn)

	if (/\.json$/i.test(url)) loadScene(); else loader.load(url, function(geom) {
		geom.computeVertexNormals();
		geom.center();
		// STL files are usually Z-up; turn them Y-up so they stand upright.
		geom.rotateX(-Math.PI / 2);
		geom.computeBoundingBox();
		scene.add(new THREE.Mesh(geom, material(geom)));
		frame(geom.boundingBox);
	}, undefined, fail);

	// A scene is several STLs in shared (Z-up) coordinates; a part with "instances"
	// (column-major 4x4s) is drawn once per placement.
	function loadScene() {
		var base = new URL('.', new URL(url, location.href)).href;
		fetch(url).then(function(r) { return r.json(); }).then(function(def) {
			return Promise.all(def.parts.map(function(part) {
				return loader.loadAsync(base + part.stl).then(function(geom) { geom.computeVertexNormals(); geom.computeBoundingBox(); return [part, geom]; });
			}));
		}).then(function(loaded) {
			var group = new THREE.Group(), box = new THREE.Box3(), b = new THREE.Box3();
			group.rotation.x = -Math.PI / 2;
			flights = [];
			loaded.forEach(function(pg) {
				var part = pg[0], geom = pg[1], mat = material(geom, { color: part.color, opacity: part.opacity });
				if (!part.instances) {
					group.add(new THREE.Mesh(geom, mat));
					box.union(geom.boundingBox);
					return;
				}
				var mesh = new THREE.InstancedMesh(geom, mat, part.instances.length);
				part.instances.forEach(function(arr, i) {
					var m = new THREE.Matrix4().fromArray(arr);
					mesh.setMatrixAt(i, m);
					box.union(b.copy(geom.boundingBox).applyMatrix4(m));
					if (part.flyIn) flights.push({ mesh: mesh, i: i, m: m, dir: new THREE.Vector3().setFromMatrixPosition(m).normalize() });
				});
				group.add(mesh);
			});
			scene.add(group);
			// Shuffle so they arrive from all round the sphere, then park each one out along its stem axis.
			for (var i = flights.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = flights[i]; flights[i] = flights[j]; flights[j] = t; }
			flights.reach = box.getSize(new THREE.Vector3()).length() * 0.3;
			fly(0);
			var yUp = box.clone().applyMatrix4(new THREE.Matrix4().makeRotationX(-Math.PI / 2));
			frame(yUp.translate(yUp.getCenter(new THREE.Vector3()).negate()));
		}).catch(fail);
	}

	// Position every flying part for elapsed time t (ms): staggered starts, ease-out landing.
	var FLY_SPREAD = 2600, FLY_TIME = 1400, tmp = new THREE.Matrix4();
	function fly(t) {
		var meshes = new Set(), done = true;
		flights.forEach(function(f, k) {
			var u = Math.min(1, Math.max(0, (t - k / flights.length * FLY_SPREAD) / FLY_TIME));
			if (u < 1) done = false;
			var off = (1 - Math.pow(1 - u, 3)) - 1;   // -1 -> 0
			tmp.copy(f.m).setPosition(new THREE.Vector3().setFromMatrixPosition(f.m).addScaledVector(f.dir, -off * flights.reach));
			f.mesh.setMatrixAt(f.i, tmp);
			meshes.add(f.mesh);
		});
		meshes.forEach(function(m) { m.instanceMatrix.needsUpdate = true; m.computeBoundingSphere(); });
		return done;
	}

	// Only draw while the element is actually on screen.
	var visible = false;
	new IntersectionObserver(function(entries) { visible = entries[0].isIntersecting; }).observe(el);
	(function loop() {
		requestAnimationFrame(loop);
		if (!visible || el.offsetParent === null || getComputedStyle(el.closest('.layer') || el).visibility === 'hidden') return;
		if (flights && flights.length) {
			var now = performance.now();
			if (flights.start === undefined) flights.start = now + 400;
			if (fly(now - flights.start)) flights = null;
		}
		controls.update();
		renderer.render(scene, camera);
	})();

	el._stl = { renderer: renderer };
	return el._stl;
}
