/* =============================================================
   gallery.js — Hotel Inside Image Gallery with Lightbox
   Auto-injected on /place/<id> pages via gallery_blueprint.py.
   No existing files were modified.
============================================================= */

(function () {
  'use strict';

  // ── 1. Only run on place detail pages ─────────────────────────────────────
  const pathMatch = window.location.pathname.match(/^\/place\/(\d+)$/);
  if (!pathMatch) return;
  const placeId = pathMatch[1];

  // ── 2. Fetch hotel inside images from API ──────────────────────────────────
  fetch('/api/place/' + placeId + '/images')
    .then(function (res) {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.json();
    })
    .then(function (images) {
      if (!images || images.length === 0) return; // no images, silently exit
      buildGallery(images);
    })
    .catch(function (err) {
      console.warn('[LocalVocal Gallery] Could not load hotel images:', err);
    });

  // ── 3. Build gallery section ───────────────────────────────────────────────
  function buildGallery(images) {
    var section = document.createElement('section');
    section.className = 'hotel-gallery-section';

    var itemsHtml = images.map(function (img, i) {
      return (
        '<div class="gallery-item" data-index="' + i + '" ' +
        'role="button" tabindex="0" ' +
        'aria-label="View photo: ' + (img.caption || 'Hotel photo') + '">' +
        '<img src="' + img.image_url + '" ' +
        'alt="' + (img.caption || 'Hotel interior photo') + '" ' +
        'loading="lazy">' +
        (img.caption
          ? '<div class="gallery-caption">' + img.caption + '</div>'
          : '') +
        '</div>'
      );
    }).join('');

    section.innerHTML =
      '<div class="gallery-container">' +
        '<div class="gallery-header">' +
          '<h2 class="gallery-title">' +
            '<span class="gallery-icon">🏨</span> Inside the Property' +
          '</h2>' +
          '<p class="gallery-subtitle">' + images.length + ' photos from this property</p>' +
        '</div>' +
        '<div class="gallery-grid" id="hotelGalleryGrid">' +
          itemsHtml +
        '</div>' +
      '</div>';

    // Insert between the hero banner and the main container
    var hero = document.querySelector('.detail-hero');
    if (hero && hero.nextSibling) {
      hero.parentNode.insertBefore(section, hero.nextSibling);
    } else {
      var main = document.querySelector('main');
      if (main) main.insertBefore(section, main.firstChild);
    }

    // Attach click & keyboard events
    section.querySelectorAll('.gallery-item').forEach(function (item) {
      item.addEventListener('click', function () {
        openLightbox(images, parseInt(item.dataset.index, 10));
      });
      item.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openLightbox(images, parseInt(item.dataset.index, 10));
        }
      });
    });
  }

  // ── 4. Lightbox state ──────────────────────────────────────────────────────
  var _images  = [];
  var _current = 0;

  function buildLightbox() {
    if (document.getElementById('galleryLightbox')) return;

    var lb = document.createElement('div');
    lb.id = 'galleryLightbox';
    lb.className = 'gallery-lightbox';
    lb.setAttribute('role', 'dialog');
    lb.setAttribute('aria-modal', 'true');
    lb.setAttribute('aria-label', 'Hotel photo viewer');

    lb.innerHTML =
      '<div class="lightbox-backdrop" id="lbBackdrop"></div>' +
      '<div class="lightbox-content">' +
        '<button class="lightbox-nav lightbox-prev" id="lbPrev" aria-label="Previous photo">&#10094;</button>' +
        '<div class="lightbox-img-wrap">' +
          '<img id="lightboxImg" src="" alt="">' +
          '<div class="lightbox-caption-text" id="lbCaption"></div>' +
        '</div>' +
        '<button class="lightbox-nav lightbox-next" id="lbNext" aria-label="Next photo">&#10095;</button>' +
      '</div>' +
      '<button class="lightbox-close" id="lbClose" aria-label="Close gallery">&#10005;</button>' +
      '<div class="lightbox-thumbs" id="lbThumbs"></div>' +
      '<div class="lightbox-counter" id="lbCounter"></div>';

    document.body.appendChild(lb);

    document.getElementById('lbBackdrop').addEventListener('click', closeLightbox);
    document.getElementById('lbClose').addEventListener('click', closeLightbox);
    document.getElementById('lbPrev').addEventListener('click', function () { navigate(-1); });
    document.getElementById('lbNext').addEventListener('click', function () { navigate(1); });
    document.addEventListener('keydown', handleKey);
  }

  function openLightbox(images, index) {
    _images  = images;
    _current = index;

    buildLightbox();
    buildThumbs();

    var lb = document.getElementById('galleryLightbox');
    lb.classList.add('active');
    document.body.style.overflow = 'hidden';
    showImage(_current);
  }

  function closeLightbox() {
    var lb = document.getElementById('galleryLightbox');
    if (lb) lb.classList.remove('active');
    document.body.style.overflow = '';
  }

  function navigate(dir) {
    _current = (_current + dir + _images.length) % _images.length;
    showImage(_current);
  }

  function showImage(index) {
    var img     = _images[index];
    var lbImg   = document.getElementById('lightboxImg');
    var caption = document.getElementById('lbCaption');
    var counter = document.getElementById('lbCounter');

    // Fade out → update → fade in
    lbImg.style.opacity = '0';
    setTimeout(function () {
      lbImg.src     = img.image_url;
      lbImg.alt     = img.caption || 'Hotel photo';
      caption.textContent = img.caption || '';
      counter.textContent = (index + 1) + ' / ' + _images.length;
      lbImg.style.opacity = '1';
    }, 160);

    // Sync thumbnail strip
    var thumbs = document.querySelectorAll('.lb-thumb');
    thumbs.forEach(function (t, i) {
      t.classList.toggle('active', i === index);
    });
    // Scroll active thumb into view
    if (thumbs[index]) {
      thumbs[index].scrollIntoView({ inline: 'center', behavior: 'smooth' });
    }
  }

  function buildThumbs() {
    var strip = document.getElementById('lbThumbs');
    if (!strip) return;
    strip.innerHTML = _images.map(function (img, i) {
      return (
        '<div class="lb-thumb" data-idx="' + i + '" ' +
        'role="button" tabindex="0" ' +
        'aria-label="Photo ' + (i + 1) + '">' +
        '<img src="' + img.image_url + '" alt="thumb ' + (i + 1) + '" loading="lazy">' +
        '</div>'
      );
    }).join('');

    strip.querySelectorAll('.lb-thumb').forEach(function (el) {
      el.addEventListener('click', function () {
        _current = parseInt(el.dataset.idx, 10);
        showImage(_current);
      });
      el.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          _current = parseInt(el.dataset.idx, 10);
          showImage(_current);
        }
      });
    });
  }

  function handleKey(e) {
    var lb = document.getElementById('galleryLightbox');
    if (!lb || !lb.classList.contains('active')) return;
    if (e.key === 'ArrowLeft')  { e.preventDefault(); navigate(-1); }
    if (e.key === 'ArrowRight') { e.preventDefault(); navigate(1);  }
    if (e.key === 'Escape')     { closeLightbox(); }
  }

})();
