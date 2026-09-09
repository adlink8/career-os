document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('btn-gear').addEventListener('click', () => {
    chrome.runtime.openOptionsPage();
  });

  const table = document.getElementById('shortcut-table');
  const api = self.CareerOsShortcuts;
  if (!api) return;
  api.load().then((map) => {
    table.textContent = '';
    Object.keys(api.DEFAULTS).forEach((id) => {
      const s = map[id];
      const tr = document.createElement('tr');
      const k = document.createElement('td');
      k.className = 'k';
      k.textContent = api.format(s);
      const l = document.createElement('td');
      l.className = 'l';
      l.textContent = s.label;
      tr.appendChild(k);
      tr.appendChild(l);
      table.appendChild(tr);
    });
  });
});
