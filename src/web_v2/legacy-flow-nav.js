'use strict';

// Anchors retain native keyboard, URL and back/forward behavior.
(function () {
  const links = [...document.querySelectorAll('.flow-links a')];
  if (!links.length) return;
  const nav = links[0].closest('nav');
  const sections = links.map(link => document.querySelector(link.getAttribute('href')));
  let queued = false;

  function updateCurrent() {
    queued = false;
    const readingLine = nav.offsetHeight + 38;
    let active = 0;
    sections.forEach((section, index) => {
      if (section.getBoundingClientRect().top <= readingLine) active = index;
    });
    if (window.scrollY > 0 && window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2) {
      active = sections.length - 1;
    }
    links.forEach((link, index) => {
      if (index === active) link.setAttribute('aria-current', 'location');
      else link.removeAttribute('aria-current');
    });
  }

  function scheduleUpdate() {
    if (queued) return;
    queued = true;
    requestAnimationFrame(updateCurrent);
  }

  function updateOffset() {
    document.documentElement.style.setProperty('--flow-offset', `${nav.offsetHeight + 36}px`);
    scheduleUpdate();
  }

  links.forEach((link, index) => link.addEventListener('click', () => {
    const details = sections[index].querySelector('.audit');
    if (details) details.open = true;
  }));
  window.addEventListener('scroll', scheduleUpdate, { passive: true });
  window.addEventListener('resize', updateOffset);
  window.addEventListener('hashchange', scheduleUpdate);
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(updateOffset).observe(nav);
  updateOffset();
})();
