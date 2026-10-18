document.addEventListener('DOMContentLoaded', () => {
  const store = self.CareerOsOverlay;
  const toggle = document.getElementById('overlay-enabled');
  const switchLabel = document.getElementById('switch-label');
  const msgEl = document.getElementById('msg');
  const root = document.getElementById('notebook-root');

  let notebook = store.emptyNotebook();

  function showMsg(text, isErr) {
    msgEl.hidden = false;
    msgEl.textContent = text;
    msgEl.className = 'msg' + (isErr ? ' err' : '');
  }

  function updateSwitchLabel() {
    switchLabel.textContent = toggle.checked ? '打开 · 用本页填表（插件单独用）' : '关闭 · 若已装 Career OS 则读编排器';
  }

  function starterNotebook() {
    const nb = store.emptyNotebook();
    store.upsertModule(nb, { id: 'm1', title: '个人信息' });
    store.addItem(nb, 'm1');
    ['姓名', '手机号', '邮箱', '身份证号'].forEach((lab) => store.setField(nb, 'm1', 0, lab, ''));
    return nb;
  }

  function renderNotebook() {
    if (!root) return;
    root.textContent = '';
    (notebook.modules || []).forEach((mod, mi) => {
      const sec = document.createElement('section');
      sec.id = 'mod-' + (mod.id || mi);
      const head = document.createElement('div');
      head.className = 'list-head';
      const titleWrap = document.createElement('label');
      titleWrap.textContent = '模块名';
      const titleInp = document.createElement('input');
      titleInp.value = mod.title || '';
      titleInp.addEventListener('input', () => {
        mod.title = titleInp.value;
        renderFillPolicy();
        renderToc();
      });
      titleWrap.appendChild(titleInp);
      const tools = document.createElement('div');
      tools.className = 'module-tools';
      const addItemBtn = document.createElement('button');
      addItemBtn.type = 'button';
      addItemBtn.className = 'btn';
      addItemBtn.textContent = '添加一段';
      addItemBtn.addEventListener('click', () => {
        store.addItem(notebook, mod.id);
        const last = mod.items[mod.items.length - 1];
        const prev = mod.items[0];
        if (prev && prev.fields && last) {
          last.fields = prev.fields.map((f) => ({ label: f.label, value: '' }));
        }
        renderNotebook();
      });
      const addFieldBtn = document.createElement('button');
      addFieldBtn.type = 'button';
      addFieldBtn.className = 'btn';
      addFieldBtn.textContent = '添加字段';
      addFieldBtn.addEventListener('click', () => {
        if (!mod.items.length) store.addItem(notebook, mod.id);
        store.setField(notebook, mod.id, 0, '新字段', '');
        renderNotebook();
      });
      const delMod = document.createElement('button');
      delMod.type = 'button';
      delMod.className = 'btn danger';
      delMod.textContent = '删除模块';
      delMod.addEventListener('click', () => {
        notebook.modules = notebook.modules.filter((m) => m !== mod);
        renderNotebook();
      });
      tools.appendChild(addItemBtn);
      tools.appendChild(addFieldBtn);
      tools.appendChild(delMod);
      head.appendChild(titleWrap);
      head.appendChild(tools);
      sec.appendChild(head);

      const list = document.createElement('div');
      list.className = 'repeat-list';
      if (!mod.items || !mod.items.length) {
        const empty = document.createElement('div');
        empty.className = 'repeat-empty';
        empty.textContent = '还没有内容。点「添加一段」或「添加字段」。';
        list.appendChild(empty);
      }
      (mod.items || []).forEach((item, ii) => {
        const card = document.createElement('div');
        card.className = 'repeat-card';
        const cardHead = document.createElement('div');
        cardHead.className = 'repeat-card-head';
        const cardTitle = document.createElement('div');
        cardTitle.className = 'repeat-card-title';
        cardTitle.textContent = (mod.title || '模块') + ' ' + (ii + 1);
        const delItem = document.createElement('button');
        delItem.type = 'button';
        delItem.className = 'btn danger';
        delItem.textContent = '删除这段';
        delItem.addEventListener('click', () => {
          mod.items.splice(ii, 1);
          renderNotebook();
        });
        cardHead.appendChild(cardTitle);
        cardHead.appendChild(delItem);
        const grid = document.createElement('div');
        grid.className = 'grid';
        (item.fields || []).forEach((field, fi) => {
          const lab = document.createElement('label');
          if (fi === item.fields.length - 1 || String(field.value || '').length > 40) lab.className = 'wide';
          const nameInp = document.createElement('input');
          nameInp.value = field.label || '';
          nameInp.placeholder = '字段名';
          nameInp.addEventListener('input', () => { field.label = nameInp.value; });
          const valEl = document.createElement(String(field.value || '').length > 60 ? 'textarea' : 'input');
          if (valEl.tagName === 'TEXTAREA') valEl.rows = 3;
          valEl.value = field.value || '';
          valEl.placeholder = '内容';
          valEl.addEventListener('input', () => { field.value = valEl.value; });
          const delF = document.createElement('button');
          delF.type = 'button';
          delF.className = 'btn danger';
          delF.textContent = '删字段';
          delF.addEventListener('click', () => {
            item.fields.splice(fi, 1);
            renderNotebook();
          });
          lab.appendChild(nameInp);
          lab.appendChild(valEl);
          lab.appendChild(delF);
          grid.appendChild(lab);
        });
        const extra = document.createElement('button');
        extra.type = 'button';
        extra.className = 'btn';
        extra.textContent = '本段加字段';
        extra.addEventListener('click', () => {
          store.setField(notebook, mod.id, ii, '新字段', '');
          renderNotebook();
        });
        card.appendChild(cardHead);
        card.appendChild(grid);
        card.appendChild(extra);
        list.appendChild(card);
      });
      sec.appendChild(list);
      root.appendChild(sec);
    });
    renderFillPolicy();
    renderToc();
  }

  async function persist(enabled, notice) {
    await store.saveState(enabled, notebook);
    toggle.checked = !!enabled;
    updateSwitchLabel();
    showMsg(notice || (enabled ? '已导入并启用内容库' : '已保存（开关关闭，填表仍读本地 JSON）'));
  }

  function applyImported(raw, notice) {
    const incoming = store.normalizeImport(raw);
    if (!notebook.modules.length) notebook = incoming;
    else store.mergeNotebook(notebook, incoming);
    renderNotebook();
    showMsg(notice || '已导入 JSON，确认后点「一键导入并启用」');
  }

  function importFile(file) {
    if (!file) return;
    const name = (file.name || '').toLowerCase();
    if (name && !name.endsWith('.json')) {
      showMsg('请拖入 .json 文件', true);
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      try {
        applyImported(reader.result, '已从文件导入：' + (file.name || 'json'));
      } catch (err) {
        showMsg(String(err && err.message ? err.message : err), true);
      }
    };
    reader.onerror = () => showMsg('读取文件失败', true);
    reader.readAsText(file, 'utf-8');
  }

  const policyApi = self.CareerOsFillPolicy;
  let fillGroups = {};

  function renderFillPolicy() {
    const grid = document.getElementById('fill-policy-grid');
    if (!grid || !policyApi) return;
    grid.textContent = '';
    const groups = policyApi.groupsFrom(notebook);
    if (!groups.length) {
      const empty = document.createElement('div');
      empty.className = 'repeat-empty';
      empty.textContent = '还没有模块。添加模块后可在这里勾选一键范围。';
      grid.appendChild(empty);
      return;
    }
    fillGroups = policyApi.normalize(fillGroups, notebook);
    groups.forEach((g) => {
      const lab = document.createElement('label');
      lab.className = 'fill-policy-item';
      const box = document.createElement('input');
      box.type = 'checkbox';
      box.checked = fillGroups[g.id] !== false;
      box.addEventListener('change', async () => {
        fillGroups[g.id] = box.checked;
        fillGroups = await policyApi.save(fillGroups);
        const n = policyApi.selectedIds(fillGroups, notebook).length;
        showMsg('一键填充将写入 ' + n + ' / ' + groups.length + ' 个模块。格子旁「填入」不受影响。');
      });
      lab.appendChild(box);
      lab.appendChild(document.createTextNode(g.label));
      grid.appendChild(lab);
    });
  }

  async function setFillPolicyAll(on) {
    if (!policyApi) return;
    const next = {};
    policyApi.groupsFrom(notebook).forEach((g) => { next[g.id] = !!on; });
    fillGroups = await policyApi.save(next);
    renderFillPolicy();
    showMsg(on ? '已全选：一键填充会写对上的模块' : '已全不选：一键填充不会写任何模块，请用格子旁「填入」');
  }

  function renderToc() {
    const box = document.getElementById('toc-links');
    if (!box) return;
    box.textContent = '';
    const links = [
      { href: '#sec-import', text: '导入 JSON' },
      { href: '#sec-keys', text: '快捷键' },
      { href: '#sec-fill-policy', text: '一键范围' }
    ].concat((notebook.modules || []).map((m, i) => ({
      href: '#mod-' + (m.id || i),
      text: m.title || ('模块 ' + (i + 1))
    })));
    links.forEach((row) => {
      const a = document.createElement('a');
      a.href = row.href;
      a.textContent = row.text;
      box.appendChild(a);
    });
    bindToc();
  }

  let tocBound = false;
  function bindToc() {
    const toc = document.getElementById('toc');
    if (!toc || tocBound) {
      if (toc && toc._setActive) {
        const first = toc.querySelector('a[href^="#"]');
        if (first) toc._setActive(first.getAttribute('href').slice(1));
      }
      return;
    }
    tocBound = true;
    const links = () => Array.from(toc.querySelectorAll('a[href^="#"]'));
    function setActive(id) {
      links().forEach((a) => {
        a.classList.toggle('active', a.getAttribute('href') === '#' + id);
      });
    }
    toc._setActive = setActive;
    let tocLock = '';
    let tocUnlockTimer = 0;
    function headerOffset() {
      const top = document.querySelector('.top');
      return (top ? top.getBoundingClientRect().height : 72) + 12;
    }
    function unlockToc() {
      tocLock = '';
      if (tocUnlockTimer) {
        clearTimeout(tocUnlockTimer);
        tocUnlockTimer = 0;
      }
    }
    toc.addEventListener('click', (e) => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      e.preventDefault();
      const el = document.getElementById(a.getAttribute('href').slice(1));
      if (!el) return;
      setActive(el.id);
      tocLock = el.id;
      if (tocUnlockTimer) clearTimeout(tocUnlockTimer);
      const y = window.scrollY + el.getBoundingClientRect().top - headerOffset();
      window.scrollTo({ top: Math.max(0, y), behavior: 'smooth' });
      tocUnlockTimer = setTimeout(unlockToc, 700);
    });
  }

  document.getElementById('btn-add-module').addEventListener('click', () => {
    const mod = store.upsertModule(notebook, { title: '新模块' });
    store.addItem(notebook, mod.id);
    store.setField(notebook, mod.id, 0, '新字段', '');
    renderNotebook();
  });

  store.loadState().then((state) => {
    toggle.checked = !!state.enabled;
    updateSwitchLabel();
    notebook = state.notebook && state.notebook.modules && state.notebook.modules.length
      ? state.notebook
      : starterNotebook();
    renderNotebook();
  });
  if (policyApi) {
    policyApi.load().then((map) => {
      fillGroups = map || {};
      renderFillPolicy();
    });
    const allBtn = document.getElementById('btn-fill-all');
    const noneBtn = document.getElementById('btn-fill-none');
    if (allBtn) allBtn.addEventListener('click', () => setFillPolicyAll(true));
    if (noneBtn) noneBtn.addEventListener('click', () => setFillPolicyAll(false));
  }

  toggle.addEventListener('change', async () => {
    await persist(toggle.checked, toggle.checked
      ? '开关已打开：网申页将用本页内容填'
      : '开关已关闭：网申页改读本地 JSON / 专投海投');
  });

  document.getElementById('btn-import').addEventListener('click', async () => {
    const name = store.valueByLabel(notebook, '姓名', 0);
    if (!name) {
      showMsg('请至少填写姓名后再导入', true);
      return;
    }
    await persist(true, '已一键导入并启用。打开网申页点「一键填充」即可。');
  });

  document.getElementById('btn-from-json').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'GET_PROFILE' }, (res) => {
      if (!res || !res.ok || !res.data) {
        showMsg((res && res.error) || '读本地 JSON 失败。请先运行 python bin/sync_autofill_profile.py', true);
        return;
      }
      applyImported(res.data, '已把本地 profile.json 灌进内容库，确认后点「一键导入并启用」');
    });
  });

  document.getElementById('btn-from-page').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'ADAPTIVE_FROM_TAB' }, (res) => {
      if (!res || !res.ok) {
        showMsg((res && res.error) || '当前页没有可读的表单，请先打开报名表', true);
        return;
      }
      const ingested = store.ingestPageFields(notebook, res.fields || []);
      notebook = ingested.notebook;
      renderNotebook();
      showMsg('已按本页生成骨架并补空字段，已填值按标签写入。无关模块正文未覆盖。');
    });
  });

  document.getElementById('btn-apply-shape').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'APPLY_SAVED_SHAPE' }, (res) => {
      if (!res || !res.ok) {
        showMsg((res && res.error) || '这页还没有骨架，先点自适应', true);
        return;
      }
      const applied = store.applySavedShape(notebook, res.shapes || {}, res.pageKey);
      if (!applied.ok) {
        showMsg(applied.reason || '这页还没有骨架，先点自适应', true);
        return;
      }
      notebook = applied.notebook;
      renderNotebook();
      showMsg('已套用本页上次骨架，内容库正文未改。');
    });
  });

  document.getElementById('btn-clear').addEventListener('click', async () => {
    notebook = store.emptyNotebook();
    renderNotebook();
    await persist(false, '已清空本页，并关闭开关');
  });

  const keysApi = self.CareerOsShortcuts;
  const editor = document.getElementById('shortcut-editor');
  let shortcutMap = keysApi ? keysApi.cloneDefaults() : {};

  function renderShortcuts() {
    if (!editor || !keysApi) return;
    editor.textContent = '';
    Object.keys(keysApi.DEFAULTS).forEach((id) => {
      const row = document.createElement('div');
      row.className = 'shortcut-row';
      const lab = document.createElement('span');
      lab.textContent = keysApi.DEFAULTS[id].label;
      const inp = document.createElement('input');
      inp.readOnly = true;
      inp.value = keysApi.format(shortcutMap[id]);
      inp.placeholder = '点击后按下组合键';
      inp.addEventListener('keydown', async (e) => {
        e.preventDefault();
        const rec = keysApi.fromEvent(e);
        if (!rec) return;
        rec.label = keysApi.DEFAULTS[id].label;
        shortcutMap[id] = rec;
        inp.value = keysApi.format(rec);
        await keysApi.save(shortcutMap);
        showMsg('已保存快捷键：' + rec.label + ' = ' + keysApi.format(rec));
      });
      row.appendChild(lab);
      row.appendChild(inp);
      editor.appendChild(row);
    });
  }

  const dropzone = document.getElementById('sec-import');
  const fileInput = document.getElementById('file-json');
  if (dropzone) {
    ['dragenter', 'dragover'].forEach((ev) => {
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('drag');
      });
    });
    ['dragleave', 'drop'].forEach((ev) => {
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (ev === 'dragleave') dropzone.classList.remove('drag');
      });
    });
    dropzone.addEventListener('drop', (e) => {
      dropzone.classList.remove('drag');
      const file = e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files[0];
      importFile(file);
    });
    dropzone.addEventListener('click', (e) => {
      if (e.target.closest('button')) return;
      if (fileInput) fileInput.click();
    });
  }
  const pickBtn = document.getElementById('btn-pick-json');
  if (pickBtn && fileInput) {
    pickBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
    fileInput.addEventListener('change', () => {
      importFile(fileInput.files && fileInput.files[0]);
      fileInput.value = '';
    });
  }
  const promptBtn = document.getElementById('btn-copy-prompt');
  if (promptBtn) {
    promptBtn.addEventListener('click', async () => {
      const text = store.buildAiPrompt();
      try {
        await navigator.clipboard.writeText(text);
        showMsg('已复制 AI 提示词。把简历贴到提示词末尾，让模型只输出 JSON，再拖回本页导入。');
      } catch (_) {
        showMsg('复制失败，请检查剪贴板权限', true);
      }
    });
  }

  if (keysApi) {
    keysApi.load().then((map) => {
      shortcutMap = map;
      renderShortcuts();
    });
    const resetBtn = document.getElementById('btn-shortcut-reset');
    if (resetBtn) {
      resetBtn.addEventListener('click', async () => {
        shortcutMap = keysApi.cloneDefaults();
        await keysApi.save(shortcutMap);
        renderShortcuts();
        showMsg('快捷键已恢复默认（Alt+Shift+字母）');
      });
    }
  }
});
