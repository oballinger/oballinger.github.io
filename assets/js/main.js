/*
	Multiverse by HTML5 UP
	html5up.net | @ajlkn
	Free for personal and commercial use under the CCA 3.0 license (html5up.net/license)
*/

(function($) {

	var	$window = $(window),
		$body = $('body'),
		$wrapper = $('#wrapper');

	// Breakpoints.
		breakpoints({
			xlarge:  [ '1281px',  '1680px' ],
			large:   [ '981px',   '1280px' ],
			medium:  [ '737px',   '980px'  ],
			small:   [ '481px',   '736px'  ],
			xsmall:  [ null,      '480px'  ]
		});

	// Hack: Enable IE workarounds.
		if (browser.name == 'ie')
			$body.addClass('ie');

	// Touch?
		if (browser.mobile)
			$body.addClass('touch');

	// Transitions supported?
		if (browser.canUse('transition')) {

			// Play initial animations on page load.
				$window.on('load', function() {
					window.setTimeout(function() {
						$body.removeClass('is-preload');
					}, 100);
				});

			// Prevent transitions/animations on resize.
				var resizeTimeout;

				$window.on('resize', function() {

					window.clearTimeout(resizeTimeout);

					$body.addClass('is-resizing');

					resizeTimeout = window.setTimeout(function() {
						$body.removeClass('is-resizing');
					}, 100);

				});

		}

	// Scroll back to top.
		$window.scrollTop(0);

	// Panels.
		var $panels = $('.panel');

		$panels.each(function() {

			var $this = $(this),
				$toggles = $('[href="#' + $this.attr('id') + '"]'),
				$closer = $('<div class="closer" />').appendTo($this);

			// Closer.
				$closer
					.on('click', function(event) {
						$this.trigger('---hide');
					});

			// Events.
				$this
					.on('click', function(event) {
						event.stopPropagation();
					})
					.on('---toggle', function() {

						if ($this.hasClass('active'))
							$this.triggerHandler('---hide');
						else
							$this.triggerHandler('---show');

					})
					.on('---show', function() {

						// Hide other content.
							if ($body.hasClass('content-active'))
								$panels.trigger('---hide');

						// Activate content, toggles.
							$this.addClass('active');
							$toggles.addClass('active');

						// Activate body.
							$body.addClass('content-active');

					})
					.on('---hide', function() {

						// Deactivate content, toggles.
							$this.removeClass('active');
							$toggles.removeClass('active');

						// Deactivate body.
							$body.removeClass('content-active');

					});

			// Toggles.
				$toggles
					.removeAttr('href')
					.css('cursor', 'pointer')
					.on('click', function(event) {

						event.preventDefault();
						event.stopPropagation();

						$this.trigger('---toggle');

					});

		});

		// Global events.
			$body
				.on('click', function(event) {

					if ($body.hasClass('content-active')) {

						event.preventDefault();
						event.stopPropagation();

						$panels.trigger('---hide');

					}

				});

			$window
				.on('keyup', function(event) {

					if (event.keyCode == 27
					&&	$body.hasClass('content-active')) {

						event.preventDefault();
						event.stopPropagation();

						$panels.trigger('---hide');

					}

				});

	// Header.
		var $header = $('#header');

		// Links.
			$header.find('a').each(function() {

				var $this = $(this),
					href = $this.attr('href');

				// Internal link? Skip.
					if (!href
					||	href.charAt(0) == '#')
						return;

				// Redirect on click.
					$this
						.removeAttr('href')
						.css('cursor', 'pointer')
						.on('click', function(event) {

							event.preventDefault();
							event.stopPropagation();

							window.location.href = href;

						});

			});

	// Footer.
		var $footer = $('#footer');

		// Copyright.
		// This basically just moves the copyright line to the end of the *last* sibling of its current parent
		// when the "medium" breakpoint activates, and moves it back when it deactivates.
			$footer.find('.copyright').each(function() {

				var $this = $(this),
					$parent = $this.parent(),
					$lastParent = $parent.parent().children().last();

				breakpoints.on('<=medium', function() {
					$this.appendTo($lastParent);
				});

				breakpoints.on('>medium', function() {
					$this.appendTo($parent);
				});

			});

	// Main.
		var $main = $('#main');

	// Thumbs: images and videos load only when their card nears the viewport.
	// Cards on hidden tabs are display:none, so they never intersect until shown.
		function loadThumb(thumb) {
			var $this = $(thumb);
			if ($this.data('loaded')) return;
			$this.data('loaded', true);

			var $image = $this.children('.image'),
				$img = $image.children('img'),
				src = $img.attr('data-src') || $img.attr('src');

			if ($image.length && src) {
				$image.css('background-image', 'url(' + src + ')');
				if ($img.data('position'))
					$image.css('background-position', $img.data('position'));
				$img.hide();
			}

			$this.find('video[data-src]').each(function() {
				this.poster = this.getAttribute('data-poster') || '';
				this.src = this.getAttribute('data-src');
				this.removeAttribute('data-src');
				// Start straight away; the player observer pauses it again once it leaves the screen.
				var p = this.play();
				if (p && p.catch) p.catch(function() {});
			});
		}

		function setPlaying(thumb, on) {
			$(thumb).find('video').each(function() {
				if (on) { var p = this.play(); if (p && p.catch) p.catch(function() {}); }
				else this.pause();
			});
		}

		var $allThumbs = $main.children('.thumb');

		if ('IntersectionObserver' in window) {
			var loader = new IntersectionObserver(function(entries) {
				entries.forEach(function(entry) {
					if (entry.isIntersecting) loadThumb(entry.target);
				});
			}, { rootMargin: '400px 0px' });

			var player = new IntersectionObserver(function(entries) {
				entries.forEach(function(entry) {
					setPlaying(entry.target, entry.isIntersecting);
				});
			}, { threshold: 0.1 });

			$allThumbs.each(function() {
				// Hide the placeholder <img> right away; the image shows as a background once loaded.
				$(this).children('.image').children('img').hide();
				loader.observe(this);
				if ($(this).find('video').length) player.observe(this);
			});
		}
		else {
			$allThumbs.each(function() { loadThumb(this); setPlaying(this, true); });
		}

	// Hover overlay with the description (mouse/trackpad only; touch layouts show it inline).
		if (window.matchMedia('(hover: hover)').matches) {
			$('.thumb').on('mouseenter', function() {
				var s = $(this).find('p')[0].innerHTML;
				$(this).append('<div class="overlay"><p>' + s + '</p></div>');
				// Shrink the text until it clears the title pinned at the bottom of the card.
				var p = $('.overlay p', this)[0], h2 = $(this).find('h2')[0], size = parseFloat(getComputedStyle(p).fontSize);
				while (size > 9 && p.getBoundingClientRect().bottom > h2.getBoundingClientRect().top - 12) {
					size -= 0.5;
					p.style.fontSize = size + 'px';
				}
			}).on('mouseleave', function() {
				$('.overlay', this).remove();
			});
		}

	// Whole card is a link (the title and description sit outside the <a> on touch layouts).
		$('.thumb').on('click', function(event) {
			if ($(event.target).closest('a').length)
				return;
			var href = $(this).find('a').attr('href');
			if (href && href != '#')
				window.location.href = href;
		});

	// Tabs.
		var $tabs = $('#tabs button'),
			$thumbs = $main.children('.thumb'),
			$empty = $('#tab-empty');

		function showTab(name) {
			if (!$tabs.filter('[data-tab="' + name + '"]').length)
				name = $tabs.first().data('tab');

			$tabs.each(function() {
				$(this).attr('aria-selected', $(this).data('tab') == name ? 'true' : 'false');
			});

			var $visible = $thumbs.filter('[data-tab="' + name + '"]');
			$thumbs.addClass('is-hidden');
			$visible.removeClass('is-hidden');
			$('.tab-section').each(function() {
				var show = $(this).data('tab') == name;
				$(this).prop('hidden', !show);
				// Images in a section only start loading once its tab is opened (then lazily by the browser).
				if (show)
					$(this).find('img[data-src]').each(function() {
						this.src = this.getAttribute('data-src');
						this.removeAttribute('data-src');
					});
			});
			$empty.prop('hidden', $visible.length > 0);
		}

		$tabs.on('click', function() {
			var name = $(this).data('tab');
			showTab(name);
			if (history.replaceState)
				history.replaceState(null, '', '#' + name);
		});

		$window.on('hashchange', function() {
			showTab(location.hash.slice(1));
		});

		showTab(location.hash.slice(1));

})(jQuery);