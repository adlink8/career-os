document.addEventListener('DOMContentLoaded', () => {
  const store = self.CareerOsOverlay;
  const form = document.getElementById('overlay-form');
  const toggle = document.getElementById('overlay-enabled');
  const switchLabel = document.getElementById('switch-label');
  const msgEl = document.getElementById('msg');

  function showMsg(text, isErr) {
    msgEl.hidden = false;
    msgEl.textContent = text;
    msgEl.className = 'msg' + (isErr ? ' err' : '');
  }

  function updateSwitchLabel() {
    switchLabel.textContent = toggle.checked ? '打开 · 用本页填表（插件单独用）' : '关闭 · 若已装 Career OS 则读编排器';
  }

  const MAX_LIST = 12;
  const LIST_SPECS = {
    intern: {
      path: 'application.internships',
      mount: 'list-intern',
      title: '实习',
      fields: [
        { key: 'name', label: '单位名称' },
        { key: 'role', label: '职位名称' },
        { key: 'start_date', label: '开始时间', ph: 'YYYY-MM' },
        { key: 'end_date', label: '结束时间', ph: 'YYYY-MM' },
        { key: 'duty', label: '实习内容', textarea: true, wide: true, rows: 3 }
      ]
    },
    projects: {
      path: 'application.projects',
      mount: 'list-projects',
      title: '项目',
      fields: [
        { key: 'name', label: '项目名称' },
        { key: 'role', label: '担任角色' },
        { key: 'keywords', label: '技术栈' },
        { key: 'start_date', label: '开始时间', ph: 'YYYY-MM' },
        { key: 'end_date', label: '结束时间', ph: 'YYYY-MM' },
        { key: 'full_text', label: '项目描述', textarea: true, wide: true, rows: 4 }
      ]
    },
    campus_roles: {
      path: 'application.campus_roles',
      mount: 'list-campus_roles',
      title: '职务',
      fields: [
        { key: 'name', label: '职务名称' },
        { key: 'description', label: '职务描述', textarea: true, wide: true, rows: 2 }
      ]
    },
    campus_practices: {
      path: 'application.campus_practices',
      mount: 'list-campus_practices',
      title: '实践',
      fields: [
        { key: 'name', label: '实践名称' },
        { key: 'description', label: '实践描述', textarea: true, wide: true, rows: 2 }
      ]
    },
    awards: {
      path: 'application.award_records',
      mount: 'list-awards',
      title: '获奖',
      fields: [
        { key: 'name', label: '获奖项' },
        { key: 'date', label: '获奖时间', ph: 'YYYY-MM' },
        { key: 'level', label: '获奖级别' },
        { key: 'description', label: '获奖描述', textarea: true, wide: true, rows: 2 }
      ]
    },
    certs: {
      path: 'application.certificate_records',
      mount: 'list-certs',
      title: '证书',
      fields: [
        { key: 'name', label: '证书名称' },
        { key: 'date', label: '获得时间', ph: 'YYYY-MM' }
      ]
    },
    langs: {
      path: 'application.languages',
      mount: 'list-langs',
      title: '语种',
      fields: [
        { key: 'type', label: '语言类型', ph: '英语' },
        { key: 'level', label: '掌握程度' }
      ]
    }
  };

  function listCount(id) {
    const spec = LIST_SPECS[id];
    const mount = document.getElementById(spec.mount);
    return mount ? mount.querySelectorAll('.repeat-card').length : 0;
  }

  function renderList(id, rows) {
    const spec = LIST_SPECS[id];
    const mount = document.getElementById(spec.mount);
    if (!spec || !mount) return;
    const items = Array.isArray(rows) ? rows.slice() : [];
    mount.textContent = '';
    if (!items.length) {
      const empty = document.createElement('div');
      empty.className = 'repeat-empty';
      empty.textContent = '还没有' + spec.title + '。需要几段就点右上角「添加」。';
      mount.appendChild(empty);
      return;
    }
    items.forEach((row, idx) => {
      const card = document.createElement('div');
      card.className = 'repeat-card';
      const head = document.createElement('div');
      head.className = 'repeat-card-head';
      const title = document.createElement('div');
      title.className = 'repeat-card-title';
      title.textContent = spec.title + ' ' + (idx + 1);
      const del = document.createElement('button');
      del.type = 'button';
      del.className = 'btn danger';
      del.textContent = '删除';
      del.addEventListener('click', () => {
        const current = readList(id);
        current.splice(idx, 1);
        renderList(id, current);
      });
      head.appendChild(title);
      head.appendChild(del);
      const grid = document.createElement('div');
      grid.className = 'grid';
      spec.fields.forEach((f) => {
        const lab = document.createElement('label');
        if (f.wide) lab.className = 'wide';
        lab.appendChild(document.createTextNode(f.label + ' '));
        const el = document.createElement(f.textarea ? 'textarea' : 'input');
        el.name = spec.path + '.' + idx + '.' + f.key;
        if (f.textarea) el.rows = f.rows || 3;
        if (f.ph) el.placeholder = f.ph;
        const val = row && row[f.key];
        el.value = val == null ? '' : String(val);
        lab.appendChild(el);
        grid.appendChild(lab);
      });
      card.appendChild(head);
      card.appendChild(grid);
      mount.appendChild(card);
    });
  }

  function readList(id) {
    const spec = LIST_SPECS[id];
    const n = listCount(id);
    const rows = [];
    for (let i = 0; i < n; i++) {
      const row = store.emptyRow();
      spec.fields.forEach((f) => {
        const el = form.querySelector('[name="' + spec.path + '.' + i + '.' + f.key + '"]');
        row[f.key] = el ? (el.value || '').trim() : '';
      });
      rows.push(row);
    }
    return rows;
  }

  function addListItem(id) {
    if (listCount(id) >= MAX_LIST) {
      showMsg('最多 ' + MAX_LIST + ' 段', true);
      return;
    }
    const rows = readList(id);
    rows.push(store.emptyRow());
    renderList(id, rows);
  }

  function fillLists(profile) {
    Object.keys(LIST_SPECS).forEach((id) => {
      const spec = LIST_SPECS[id];
      const rows = store.getByPath(profile, spec.path);
      renderList(id, Array.isArray(rows) ? rows : []);
    });
  }

  function fillForm(profile) {
    fillLists(profile);
    form.querySelectorAll('input[name], textarea[name]').forEach((el) => {
      if (el.closest('.repeat-list')) return;
      const val = store.getByPath(profile, el.name);
      el.value = val == null ? '' : String(val);
    });
  }

  function readForm() {
    const profile = store.emptyProfile();
    form.querySelectorAll('input[name], textarea[name]').forEach((el) => {
      if (el.closest('.repeat-list')) return;
      const v = (el.value || '').trim();
      if (!v) return;
      store.setByPath(profile, el.name, v);
    });
    Object.keys(LIST_SPECS).forEach((id) => {
      const spec = LIST_SPECS[id];
      store.setByPath(profile, spec.path, readList(id));
    });
    return store.compactProfile(profile);
  }

  async function persist(enabled, profile, notice) {
    await store.saveState(enabled, profile);
    toggle.checked = !!enabled;
    updateSwitchLabel();
    showMsg(notice || (enabled ? '已导入并启用设置页画像' : '已保存（开关关闭，填表仍读本地 JSON）'));
  }

  function applyImported(raw, notice) {
    const profile = store.normalizeImport(raw);
    fillForm(profile);
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
  let fillGroups = policyApi ? policyApi.defaults() : {};

  function renderFillPolicy() {
    const grid = document.getElementById('fill-policy-grid');
    if (!grid || !policyApi) return;
    grid.textContent = '';
    policyApi.GROUPS.forEach((g) => {
      const lab = document.createElement('label');
      lab.className = 'fill-policy-item';
      const box = document.createElement('input');
      box.type = 'checkbox';
      box.checked = fillGroups[g.id] !== false;
      box.addEventListener('change', async () => {
        fillGroups[g.id] = box.checked;
        fillGroups = await policyApi.save(fillGroups);
        const n = policyApi.selectedIds(fillGroups).length;
        showMsg('一键填充将写入 ' + n + ' / ' + policyApi.GROUPS.length + ' 类。格子旁「填入」不受影响。');
      });
      lab.appendChild(box);
      lab.appendChild(document.createTextNode(g.label));
      grid.appendChild(lab);
    });
  }

  async function setFillPolicyAll(on) {
    if (!policyApi) return;
    const next = {};
    policyApi.GROUPS.forEach((g) => { next[g.id] = !!on; });
    fillGroups = await policyApi.save(next);
    renderFillPolicy();
    showMsg(on ? '已全选：一键填充会写本页能对上的类别' : '已全不选：一键填充不会写任何类别，请用格子旁「填入」');
  }

  document.querySelectorAll('[data-add-list]').forEach((btn) => {
    btn.addEventListener('click', () => addListItem(btn.getAttribute('data-add-list')));
  });

  store.loadState().then((state) => {
    toggle.checked = !!state.enabled;
    updateSwitchLabel();
    fillForm(state.profile);
  });
  if (policyApi) {
    policyApi.load().then((map) => {
      fillGroups = map;
      renderFillPolicy();
    });
    const allBtn = document.getElementById('btn-fill-all');
    const noneBtn = document.getElementById('btn-fill-none');
    if (allBtn) allBtn.addEventListener('click', () => setFillPolicyAll(true));
    if (noneBtn) noneBtn.addEventListener('click', () => setFillPolicyAll(false));
  }

  toggle.addEventListener('change', async () => {
    await persist(toggle.checked, readForm(), toggle.checked
      ? '开关已打开：网申页将用本页内容填'
      : '开关已关闭：网申页改读本地 JSON / 专投海投');
  });

  document.getElementById('btn-import').addEventListener('click', async () => {
    const profile = readForm();
    const name = store.getByPath(profile, 'universal.personal.name');
    if (!name) {
      showMsg('请至少填写姓名后再导入', true);
      return;
    }
    await persist(true, profile, '已一键导入并启用。打开北森/Moka 页点「一键填充」即可。');
  });

  document.getElementById('btn-from-json').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'GET_PROFILE' }, (res) => {
      if (!res || !res.ok || !res.data) {
        showMsg((res && res.error) || '读本地 JSON 失败。请先运行 python bin/sync_autofill_profile.py', true);
        return;
      }
      fillForm(res.data);
      showMsg('已把本地 profile.json 填进本页，确认后点「一键导入并启用」');
    });
  });

  document.getElementById('btn-from-page').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'IMPORT_FROM_ACTIVE_TAB' }, (res) => {
      if (!res || !res.ok) {
        showMsg((res && res.error) || '当前页没有可读的表单，请先打开北森报名页', true);
        return;
      }
      const profile = store.emptyProfile();
      const counts = {};
      (res.fields || []).forEach((item) => {
        if (!item.slot || !item.value) return;
        const key = item.slot;
        const idx = counts[key] || 0;
        store.applySlot(profile, item.slot, item.value, idx);
        counts[key] = idx + 1;
      });
      fillForm(profile);
      showMsg('已从当前网申页导入 ' + (res.fields || []).filter((x) => x.value).length + ' 项，确认后点「一键导入并启用」');
    });
  });

  document.getElementById('btn-clear').addEventListener('click', async () => {
    fillForm(store.emptyProfile());
    await persist(false, store.emptyProfile(), '已清空本页，并关闭开关');
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

  const dropzone = document.getElementById('sec-import') || document.getElementById('dropzone');
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

  const toc = document.getElementById('toc');
  if (toc) {
    const links = Array.from(toc.querySelectorAll('a[href^="#"]'));
    const targets = links
      .map((a) => document.getElementById(a.getAttribute('href').slice(1)))
      .filter(Boolean);
    function setActive(id) {
      links.forEach((a) => {
        a.classList.toggle('active', a.getAttribute('href') === '#' + id);
      });
    }
    toc.addEventListener('click', (e) => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      e.preventDefault();
      const el = document.getElementById(a.getAttribute('href').slice(1));
      if (!el) return;
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      setActive(el.id);
    });
    if ('IntersectionObserver' in window && targets.length) {
      const io = new IntersectionObserver((entries) => {
        const vis = entries
          .filter((en) => en.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (vis && vis.target && vis.target.id) setActive(vis.target.id);
      }, { rootMargin: '-90px 0px -55% 0px', threshold: [0.15, 0.4, 0.8] });
      targets.forEach((el) => io.observe(el));
    }
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
