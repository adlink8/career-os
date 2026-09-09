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

  function fillForm(profile) {
    form.querySelectorAll('input[name], textarea[name]').forEach((el) => {
      const val = store.getByPath(profile, el.name);
      el.value = val == null ? '' : String(val);
    });
  }

  function readForm() {
    const profile = store.emptyProfile();
    form.querySelectorAll('input[name], textarea[name]').forEach((el) => {
      const v = (el.value || '').trim();
      if (!v) return;
      store.setByPath(profile, el.name, v);
    });
    return profile;
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

  store.loadState().then((state) => {
    toggle.checked = !!state.enabled;
    updateSwitchLabel();
    fillForm(state.profile);
  });

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
