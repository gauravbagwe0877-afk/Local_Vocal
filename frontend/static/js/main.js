/* =============================================================
   LOCAL VOCAL — main.js
   Handles: star rating UI, flash message dismiss, delete confirm,
            and optional AJAX place fetch.
============================================================= */

document.addEventListener('DOMContentLoaded', () => {

  // ── 1. STAR RATING UI ─────────────────────────────────────────────────────
  const starsContainer = document.querySelector('.star-rating');
  if (starsContainer) {
    const stars       = starsContainer.querySelectorAll('.star');
    const ratingInput = document.getElementById('rating-input');

    stars.forEach(star => {
      // Highlight on hover
      star.addEventListener('mouseover', () => {
        const val = parseInt(star.dataset.value);
        stars.forEach(s => {
          s.classList.toggle('active', parseInt(s.dataset.value) <= val);
        });
      });

      // Reset to selected value on mouse-out
      star.addEventListener('mouseout', () => {
        const selected = ratingInput ? parseInt(ratingInput.value) || 0 : 0;
        stars.forEach(s => {
          s.classList.toggle('active', parseInt(s.dataset.value) <= selected);
        });
      });

      // Click to select rating
      star.addEventListener('click', () => {
        const val = parseInt(star.dataset.value);
        if (ratingInput) ratingInput.value = val;
        stars.forEach(s => {
          s.classList.toggle('active', parseInt(s.dataset.value) <= val);
          s.classList.toggle('selected', parseInt(s.dataset.value) <= val);
        });
      });
    });

    // Restore already-selected rating (e.g. edit review page)
    if (ratingInput && ratingInput.value) {
      const selected = parseInt(ratingInput.value);
      stars.forEach(s => {
        s.classList.toggle('active',   parseInt(s.dataset.value) <= selected);
        s.classList.toggle('selected', parseInt(s.dataset.value) <= selected);
      });
    }
  }

  // ── 2. FLASH MESSAGE AUTO-DISMISS ─────────────────────────────────────────
  const flashMessages = document.querySelectorAll('.alert[data-auto-dismiss]');
  flashMessages.forEach(msg => {
    const delay = parseInt(msg.dataset.autoDismiss) || 3000;
    setTimeout(() => {
      msg.style.transition = 'opacity 0.6s ease';
      msg.style.opacity    = '0';
      setTimeout(() => msg.remove(), 650);
    }, delay);
  });

  // Close button on flash messages
  document.querySelectorAll('.alert .close-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const alert = btn.closest('.alert');
      if (alert) alert.remove();
    });
  });

  // ── 3. DELETE CONFIRMATION ─────────────────────────────────────────────────
  document.querySelectorAll('[data-confirm]').forEach(el => {
    el.addEventListener('click', e => {
      const message = el.dataset.confirm || 'Are you sure you want to delete this?';
      if (!confirm(message)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  // Also for forms with data-confirm on the submit button
  document.querySelectorAll('form[data-confirm]').forEach(form => {
    form.addEventListener('submit', e => {
      const message = form.dataset.confirm || 'Are you sure?';
      if (!confirm(message)) {
        e.preventDefault();
      }
    });
  });

  // ── 4. SEARCH BAR — clear button ──────────────────────────────────────────
  const searchInput = document.getElementById('search-input');
  const clearBtn    = document.getElementById('search-clear');
  if (searchInput && clearBtn) {
    searchInput.addEventListener('input', () => {
      clearBtn.style.display = searchInput.value ? 'inline' : 'none';
    });
    clearBtn.addEventListener('click', () => {
      searchInput.value       = '';
      clearBtn.style.display  = 'none';
      searchInput.focus();
    });
  }

  // ── 5. MOBILE NAV TOGGLE ──────────────────────────────────────────────────
  const navToggle = document.getElementById('nav-toggle');
  const navMenu   = document.getElementById('nav-menu');
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      navMenu.classList.toggle('open');
      navToggle.setAttribute('aria-expanded',
        navMenu.classList.contains('open').toString()
      );
    });
  }

  // ── 6. OPTIONAL: AJAX — fetch places and render cards ─────────────────────
  const placesGrid = document.getElementById('places-ajax-grid');
  if (placesGrid && placesGrid.dataset.ajax === 'true') {
    fetchPlaces();
  }

  async function fetchPlaces() {
    try {
      const res    = await fetch('/api/places');
      const places = await res.json();
      placesGrid.innerHTML = '';

      if (!places.length) {
        placesGrid.innerHTML = '<p class="no-results">No places found.</p>';
        return;
      }

      places.forEach(p => {
        const card = document.createElement('div');
        card.className = 'place-card';
        card.innerHTML = `
          <a href="/place/${p.id}">
            <img src="${p.image_url || '/static/img/placeholder.jpg'}"
                 alt="${p.name}" loading="lazy" />
            <div class="card-body">
              <span class="badge">${p.category_icon || ''} ${p.category || ''}</span>
              <h3>${p.name}</h3>
              <p class="address">${p.address || ''}</p>
              <div class="card-footer">
                <span class="rating">⭐ ${p.rating || 'N/A'}</span>
                <span class="price">${p.price_range || ''}</span>
              </div>
            </div>
          </a>
        `;
        placesGrid.appendChild(card);
      });
    } catch (err) {
      console.error('Failed to fetch places:', err);
      placesGrid.innerHTML = '<p class="error">Could not load places. Please refresh.</p>';
    }
  }

});
