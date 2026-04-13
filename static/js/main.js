// ─── Local Vocal — Main JavaScript ──────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

  // ── Mobile Nav Toggle ──────────────────────────────────────────────────
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
      navToggle.setAttribute('aria-expanded', navLinks.classList.contains('open'));
    });

    // Close nav on outside click
    document.addEventListener('click', (e) => {
      if (!navToggle.contains(e.target) && !navLinks.contains(e.target)) {
        navLinks.classList.remove('open');
      }
    });
  }

  // ── Auto-dismiss Flash Messages ────────────────────────────────────────
  document.querySelectorAll('.flash').forEach(flash => {
    setTimeout(() => {
      flash.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      flash.style.opacity = '0';
      flash.style.transform = 'translateX(20px)';
      setTimeout(() => flash.remove(), 400);
    }, 4000);
  });

  // ── Animate Rating Bars on Scroll ──────────────────────────────────────
  const ratingBars = document.querySelectorAll('.bar-fill');
  if (ratingBars.length > 0) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          // Bars animate via CSS transition — trigger by ensuring width is applied
          entry.target.style.width = entry.target.style.width;
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.3 });

    // Reset widths initially then let them animate in
    ratingBars.forEach(bar => {
      const targetWidth = bar.style.width;
      bar.style.width = '0';
      requestAnimationFrame(() => {
        setTimeout(() => { bar.style.width = targetWidth; }, 300);
      });
      observer.observe(bar);
    });
  }

  // ── Card Stagger Animation ──────────────────────────────────────────────
  const cards = document.querySelectorAll('.place-card, .featured-card');
  if (cards.length > 0) {
    const cardObserver = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          setTimeout(() => {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
          }, i * 60);
          cardObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });

    cards.forEach((card, i) => {
      card.style.opacity = '0';
      card.style.transform = 'translateY(24px)';
      card.style.transition = `opacity 0.45s ease ${i * 0.05}s, transform 0.45s ease ${i * 0.05}s`;
      cardObserver.observe(card);
    });
  }

  // ── Star Picker Interaction ─────────────────────────────────────────────
  const starPicker = document.getElementById('starPicker');
  if (starPicker) {
    const inputs = starPicker.querySelectorAll('input[type=radio]');
    const labels = starPicker.querySelectorAll('label.star-pick');

    // The CSS flex-direction: row-reverse handles visual order
    // Ensure keyboard accessibility
    inputs.forEach(input => {
      input.addEventListener('change', () => {
        const val = parseInt(input.value);
        updateStarDisplay(val);
      });
    });

    function updateStarDisplay(val) {
      labels.forEach(label => {
        const labelVal = parseInt(label.getAttribute('for').replace('star', ''));
        label.style.color = labelVal <= val ? 'var(--saffron)' : '#D1C4A8';
      });
    }

    // Show current state if editing
    const checkedInput = starPicker.querySelector('input:checked');
    if (checkedInput) {
      updateStarDisplay(parseInt(checkedInput.value));
    }
  }

  // ── Password Toggle ────────────────────────────────────────────────────
  window.togglePwd = function(inputId, btn) {
    const input = document.getElementById(inputId);
    if (!input) return;
    const isPassword = input.type === 'password';
    input.type = isPassword ? 'text' : 'password';
    btn.textContent = isPassword ? '🙈' : '👁';
  };

  // ── Search Input Enhancement ───────────────────────────────────────────
  const searchInput = document.querySelector('.search-input');
  if (searchInput) {
    // Debounce is handled by form submission; add Enter key visual feedback
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        searchInput.value = '';
        searchInput.blur();
      }
    });
  }

  // ── Active Nav Link ────────────────────────────────────────────────────
  const currentPath = window.location.pathname;
  document.querySelectorAll('.nav-link').forEach(link => {
    if (link.getAttribute('href') === currentPath) {
      link.classList.add('active');
    }
  });

  // ── Smooth Scroll for Anchor Links ─────────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Admin Table Search ─────────────────────────────────────────────────
  const adminSearchInput = document.getElementById('adminSearch');
  if (adminSearchInput) {
    adminSearchInput.addEventListener('input', () => {
      const query = adminSearchInput.value.toLowerCase();
      document.querySelectorAll('.admin-table tbody tr').forEach(row => {
        row.style.display = row.textContent.toLowerCase().includes(query) ? '' : 'none';
      });
    });
  }

  // ── Image Lazy Load Error Fallback ─────────────────────────────────────
  document.querySelectorAll('img').forEach(img => {
    img.addEventListener('error', () => {
      img.src = 'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&auto=format';
      img.removeEventListener('error', arguments.callee);
    });
  });

  // ── Scroll-triggered hero elements ─────────────────────────────────────
  const heroContent = document.querySelector('.hero-content');
  if (heroContent) {
    heroContent.style.opacity = '0';
    heroContent.style.transform = 'translateY(20px)';
    heroContent.style.transition = 'opacity 0.7s ease, transform 0.7s ease';
    requestAnimationFrame(() => {
      setTimeout(() => {
        heroContent.style.opacity = '1';
        heroContent.style.transform = 'translateY(0)';
      }, 100);
    });
  }

  console.log('🏘️ Local Vocal — Sawantwadi loaded');
});
