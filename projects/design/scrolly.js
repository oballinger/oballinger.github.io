// Scrollytelling: each .step shows the .layer with the same data-index.
(function() {
	document.documentElement.classList.remove('no-js');

	var here = document.currentScript.src;
	var viewer = null;
	function showModel(el) {
		if (el._stl) return;
		viewer = viewer || import(new URL('stl-viewer.js', here).href);
		viewer.then(function(m) { m.mount(el, el.getAttribute('data-stl')); });
	}

	var steps = Array.prototype.slice.call(document.querySelectorAll('.step'));
	var layers = Array.prototype.slice.call(document.querySelectorAll('.layer'));
	var counter = document.querySelector('.counter');
	var scrolly = document.querySelector('.scrolly');
	var topbar = document.querySelector('.topbar');
	var narrow = window.matchMedia('(max-width: 800px)');

	// Cards with no heading or text are dropped entirely, not drawn as empty boxes.
	document.querySelectorAll('.step .card').forEach(function(card) {
		if (!card.textContent.trim()) card.classList.add('is-empty');
	});
	var current = -1;
	var ticking = false;

	function activate(i) {
		if (i === current) return;
		current = i;

		steps.forEach(function(step, n) {
			step.classList.toggle('is-active', n === i);
		});

		layers.forEach(function(layer, n) {
			var on = n === i;
			layer.classList.toggle('is-active', on);
			layer.setAttribute('aria-hidden', on ? 'false' : 'true');

			var model = layer.querySelector('.model');
			if (model && on) showModel(model);

			var video = layer.querySelector('video');
			if (!video) return;
			if (on) {
				var p = video.play();
				if (p && p.catch) p.catch(function() {});
			} else {
				video.pause();
			}
		});

		var full = steps[i].getAttribute('data-layout') === 'full';
		if (scrolly)
			scrolly.classList.toggle('is-full', full);
		// The top bar steps aside so it doesn't cover full-screen media.
		document.documentElement.classList.toggle('is-full-panel', full);

		if (counter)
			counter.textContent = String(i + 1).padStart(2, '0') + ' / ' + String(layers.length).padStart(2, '0');
	}

	// The active step is the last one whose top has crossed the trigger line.
	// On narrow screens the media covers the top half, so the line sits lower.
	function update() {
		ticking = false;
		var line = window.innerHeight * (narrow.matches ? 0.8 : 0.55);
		var active = 0;
		for (var n = 0; n < steps.length; n++) {
			if (steps[n].getBoundingClientRect().top < line) active = n;
		}
		activate(active);

		// Safari refuses play() for a video that isn't on screen yet (the first panel sits
		// below the intro at load), so keep nudging the active video while scrolling.
		var video = layers[active] && layers[active].querySelector('video');
		if (video && video.paused) {
			var p = video.play();
			if (p && p.catch) p.catch(function() {});
		}

		// Shrink the top bar to the text column while the media fills the window.
		var box = scrolly.getBoundingClientRect();
		document.documentElement.classList.toggle('is-pinned',
			!narrow.matches && box.top <= 0 && box.bottom > topbar.offsetHeight);
	}

	function onScroll() {
		if (!ticking) {
			ticking = true;
			window.requestAnimationFrame(update);
		}
	}

	window.addEventListener('scroll', onScroll, { passive: true });
	window.addEventListener('resize', onScroll);
	update();
})();
