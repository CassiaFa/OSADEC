// Tab widget used by templates/account.html (Analyse / Explore files).
// Implements the WAI-ARIA "tabs" pattern: roving tabindex (only the active
// tab is in the Tab sequence), Left/Right/Home/End to move between tabs, and
// each panel labelled by its tab via aria-labelledby.

Array.from(document.querySelectorAll('.tabs')).forEach((tabContainer, tabId) => {
  const registers = tabContainer.querySelector('.tab-registers');
  const bodies = tabContainer.querySelector('.tab-bodies');
  const tabs = Array.from(registers.children);
  const panels = Array.from(bodies.children);

  tabs.forEach((tab, i) => {
    const panel = panels[i];
    const isActive = tab.classList.contains('active-tab');

    tab.id = tab.id || `${tabId}_tab_${i}`;
    if (panel) {
      panel.id = panel.id || `${tabId}_panel_${i}`;
      panel.setAttribute('aria-labelledby', tab.id);
      panel.setAttribute('tabindex', '0');
    }
    tab.setAttribute('aria-controls', panel ? panel.id : '');
    tab.setAttribute('tabindex', isActive ? '0' : '-1');

    tab.addEventListener('click', () => activate(tab));
  });

  registers.addEventListener('keydown', (ev) => {
    const currentIndex = tabs.indexOf(document.activeElement);
    if (currentIndex === -1) return;

    let nextIndex = null;
    if (ev.key === 'ArrowRight') nextIndex = (currentIndex + 1) % tabs.length;
    else if (ev.key === 'ArrowLeft') nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
    else if (ev.key === 'Home') nextIndex = 0;
    else if (ev.key === 'End') nextIndex = tabs.length - 1;

    if (nextIndex !== null) {
      ev.preventDefault();
      tabs[nextIndex].focus();
      activate(tabs[nextIndex]);
    }
  });

  function activate(activeTab) {
    tabs.forEach((tab) => {
      const isActive = tab === activeTab;
      tab.classList.toggle('active-tab', isActive);
      tab.setAttribute('aria-selected', isActive ? 'true' : 'false');
      tab.setAttribute('tabindex', isActive ? '0' : '-1');
    });
    changeBody(tabs, panels, activeTab);
  }
});

function changeBody(tabs, panels, activeTab) {
  tabs.forEach((tab, i) => {
    const panel = panels[i];
    if (!panel) return;
    const isActive = tab === activeTab;
    panel.style.display = isActive ? 'block' : 'none';
    panel.hidden = !isActive;
  });
}
