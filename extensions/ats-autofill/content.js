/**
 * Career OS 网申填表 Content Script
 * 单一求职意向；画像经 background 读取，不把 profile.json 暴露给页面。
 */
(function () {
  'use strict';

  if (window.__CAREER_OS_AUTOFILL_LOADED) return;
  window.__CAREER_OS_AUTOFILL_LOADED = true;

  const isTop = window === window.top;
  let profile = null;
  let fillCtx = null;
  let isPanelOpen = false;
  let pickMode = false;
  let lastFieldEl = null;
  let lastCoverage = null;

  function requestProfile() {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ action: 'GET_PROFILE' }, (res) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (!res || !res.ok) {
          reject(new Error((res && res.error) || '画像加载失败'));
          return;
        }
        resolve(res);
      });
    });
  }

  function requestFillContext() {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({ action: 'GET_FILL_PAYLOAD', url: location.href }, (res) => {
        if (chrome.runtime.lastError) {
          reject(new Error(chrome.runtime.lastError.message));
          return;
        }
        if (!res || (res.ok === false && !res.mode)) {
          reject(new Error((res && (res.error || res.reason)) || '填写载荷加载失败'));
          return;
        }
        resolve(res);
      });
    });
  }

  function applyFillContext(ctx) {
    fillCtx = ctx || null;
    if (ctx && ctx.profile) profile = ctx.profile;
    if (ctx && ctx.autofill && ctx.autofill.target_position && profile && profile.application) {
      profile.application.target_position = ctx.autofill.target_position;
    }
    if (self.CareerOsFieldMap && self.CareerOsFieldMap.setRules) {
      self.CareerOsFieldMap.setRules((ctx && ctx.field_rules) || []);
    }
  }

  function setNativeValue(element, value) {
    if (!element || value === undefined || value === null) return false;
    const str = String(value).trim();
    if (!str) return false;
    if (element.disabled || element.readOnly) return false;

    const tag = element.tagName.toLowerCase();
    if (tag === 'select') {
      const lower = str.toLowerCase();
      let matched = false;
      Array.from(element.options).forEach((opt) => {
        const t = (opt.text || '').trim();
        const v = (opt.value || '').trim();
        if (t === str || v === str || t.includes(str) || str.includes(t) || t.toLowerCase() === lower) {
          element.value = opt.value;
          matched = true;
        }
      });
      if (!matched) return false;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    const isTextarea = tag === 'textarea';
    const prototype = isTextarea ? window.HTMLTextAreaElement.prototype : window.HTMLInputElement.prototype;
    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value')?.set;
    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;

    let writeValue = str;
    if (element.type === 'date' && /^\d{4}-\d{2}$/.test(str)) {
      writeValue = str + '-01';
    }

    if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {
      prototypeValueSetter.call(element, writeValue);
    } else if (valueSetter) {
      valueSetter.call(element, writeValue);
    } else {
      element.value = writeValue;
    }

    element.dispatchEvent(new Event('input', { bubbles: true }));
    element.dispatchEvent(new Event('change', { bubbles: true }));
    element.dispatchEvent(new Event('blur', { bubbles: true }));
    return true;
  }

  function getFieldContext(el) {
    let context = '';
    if (el.placeholder) context += ' ' + el.placeholder;
    if (el.name) context += ' ' + el.name;
    if (el.id) context += ' ' + el.id;
    if (el.getAttribute('aria-label')) context += ' ' + el.getAttribute('aria-label');
    if (el.getAttribute('data-automation')) context += ' ' + el.getAttribute('data-automation');

    let parent = el.parentElement;
    let depth = 0;
    while (parent && depth < 6) {
      const labelEl = parent.querySelector(
        'label, .el-form-item__label, .ant-form-item-label, .bs-form-item-label, .title, .item-label, th'
      );
      if (labelEl && labelEl !== el) {
        context += ' ' + labelEl.textContent;
        break;
      }
      depth++;
      parent = parent.parentElement;
    }

    let prev = el.previousElementSibling;
    if (prev && (prev.tagName === 'LABEL' || prev.tagName === 'SPAN' || prev.tagName === 'DIV')) {
      context += ' ' + prev.textContent;
    }
    return context.replace(/\s+/g, ' ').trim();
  }

  const JD_SELECTORS = [
    '[class*="job-description"]',
    '[class*="jobDescription"]',
    '[class*="job-detail"]',
    '[class*="jobDetail"]',
    '[class*="position-detail"]',
    '[class*="positionDetail"]',
    '[class*="jd-content"]',
    '[class*="recruit-detail"]',
    'article'
  ];

  function collectFormFields() {
    const nodes = Array.from(
      document.querySelectorAll(
        'input:not([type="hidden"]):not([type="file"]), textarea, select'
      )
    );
    const fmap = self.CareerOsFieldMap;
    const fields = nodes.map((el, index) => {
      const ctx = getFieldContext(el);
      const isTextarea = el.tagName.toLowerCase() === 'textarea';
      const slot = fmap ? fmap.resolveSlot(ctx, { isTextarea: isTextarea }) : '';
      const required = !!(
        el.required ||
        el.getAttribute('aria-required') === 'true' ||
        /\*|必填/.test(ctx)
      );
      return {
        index: index,
        tag: el.tagName.toLowerCase(),
        type: el.type || el.tagName.toLowerCase(),
        name: el.name || '',
        id: el.id || '',
        label: ctx.slice(0, 200),
        required: required,
        placeholder: el.placeholder || '',
        slot: slot,
        frame: isTop ? 'top' : location.href
      };
    });
    return { nodes: nodes, fields: fields };
  }

  function extractTitle() {
    const el = document.querySelector(
      'h1, .job-title, .position-title, .job-name, .post-name, [class*="jobTitle"], [class*="positionTitle"]'
    );
    const t = el && el.textContent ? el.textContent.replace(/\s+/g, ' ').trim() : '';
    if (t && t.length < 120) return t;
    return (document.title || '').split(/[-_|｜]/)[0].trim();
  }

  function extractCompany() {
    const og = document.querySelector('meta[property="og:site_name"]');
    if (og && og.getAttribute('content')) return og.getAttribute('content').trim();
    const el = document.querySelector('.company-name, [class*="companyName"], [class*="company-name"]');
    if (el && el.textContent) return el.textContent.replace(/\s+/g, ' ').trim().slice(0, 80);
    return '';
  }

  function extractJdText() {
    const chunks = [];
    JD_SELECTORS.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => {
        const t = (el.innerText || '').trim();
        if (t.length > 80) chunks.push(t);
      });
    });
    document.querySelectorAll('h2, h3, .title, .section-title').forEach((h) => {
      if (!/职位描述|岗位职责|任职要求|职位要求|工作职责|岗位要求|职位详情/.test(h.textContent || '')) return;
      const parent = h.parentElement;
      const t = (parent && parent.innerText || '').trim();
      if (t.length > 80) chunks.push(t);
    });
    chunks.sort((a, b) => b.length - a.length);
    let best = chunks[0] || '';
    if (best.length < 80) {
      best = ((document.body && document.body.innerText) || '').trim();
    }
    return best.replace(/\n{3,}/g, '\n\n').slice(0, 20000);
  }

  function capturePageContext() {
    const collected = collectFormFields();
    return {
      version: '1.0',
      captured_at: new Date().toISOString(),
      url: location.href,
      host: location.hostname,
      company: extractCompany(),
      title: extractTitle(),
      jd_text: extractJdText(),
      hard_filters: {},
      keywords: [],
      form_schema: collected.fields,
      frame: isTop ? 'top' : location.href
    };
  }

  function fieldCurrentValue(el) {
    if (!el) return '';
    if (el.type === 'checkbox' || el.type === 'radio') return el.checked ? '1' : '';
    return String(el.value || '').trim();
  }

  function summarizeCoverage(events, collected) {
    const requiredEmpty = [];
    const widgetFail = [];
    const unmapped = [];
    (collected.fields || []).forEach((field, i) => {
      const el = collected.nodes[i];
      const required = !!field.required;
      const noise = self.CareerOsFieldMap && self.CareerOsFieldMap.isNoiseLabel(field.label);
      if (noise) return;
      const ev = events.filter((e) => e.label === field.label).pop();
      const filledNow = fieldCurrentValue(el);
      if (required && !field.slot && !filledNow) unmapped.push(field.label);
      if (required && !filledNow) requiredEmpty.push(field.label);
      if (ev && ev.reason === 'no_match' && required) widgetFail.push(field.label);
    });
    return {
      filled: events.filter((e) => e.ok).length,
      attempted: events.length,
      required_empty: requiredEmpty,
      widget_fail: widgetFail,
      unmapped: unmapped,
      ready: requiredEmpty.length === 0 && widgetFail.length === 0
    };
  }

  async function executeAutofill(opts) {
    opts = opts || {};
    const fmap = self.CareerOsFieldMap;
    if (!fmap) {
      showToast('字段映射未加载，请重载扩展');
      return { count: 0 };
    }
    try {
      if (opts.fill) applyFillContext(opts.fill);
      else applyFillContext(await requestFillContext());
      if (isTop) updateUI();
    } catch (err) {
      showToast(String(err && err.message ? err.message : err));
      return { count: 0 };
    }
    if (!fillCtx || !fillCtx.allow_fill) {
      showToast((fillCtx && fillCtx.reason) || '未放行，禁止填充');
      return { count: 0, blocked: true };
    }
    if (fillCtx.mode !== 'released' && fillCtx.mode !== 'volume' && fillCtx.mode !== 'overlay' && fillCtx.mode !== 'test') {
      showToast(fillCtx.reason || '未放行，禁止填充');
      return { count: 0, blocked: true };
    }
    if (!profile || !profile.universal || !profile.application) {
      showToast('画像未加载，请运行 python bin/sync_autofill_profile.py');
      return { count: 0 };
    }
    const blankOnly = !!opts.blankOnly;
    if (isTop) showToast(blankOnly ? '仅填空白字段…' : '正在一键填充（含下拉/日期）…');
    const log = self.CareerOsLog;
    const events = [];
    const collected = collectFormFields();
    const autofill = fillCtx.autofill;
    let count = 0;
    const projectNameEls = [];
    collected.fields.forEach((field, i) => {
      const el = collected.nodes[i];
      if (!el || el.disabled || el.readOnly) return;
      if (el.type === 'radio' || el.type === 'checkbox') return;
      if (blankOnly && fieldCurrentValue(el)) {
        events.push({ op: 'fill_native', label: field.label, reason: 'already', ok: true });
        return;
      }
      if (fmap.isNoiseLabel(field.label) && !field.slot) {
        events.push({ op: 'fill_native', label: field.label, reason: 'noise', ok: false });
        return;
      }
      if (field.slot === 'application.projects.name') {
        projectNameEls.push(el);
        return;
      }
      let value = fmap.matchAutofillValue(field, autofill);
      if (!value && field.slot) value = fmap.valueForSlot(field.slot, profile, 0);
      if (field.slot === 'application.target_position' && autofill && autofill.target_position) {
        value = autofill.target_position;
      }
      if (!field.slot && !value) {
        events.push({ op: 'fill_native', label: field.label, reason: 'unmapped', ok: false });
        return;
      }
      if (field.slot === 'universal.personal.id_card' && !fmap.isRealIdCard(value)) {
        events.push({ op: 'fill_native', label: field.label, slot: field.slot, reason: 'skip_id', ok: false });
        return;
      }
      if (!value) {
        events.push({ op: 'fill_native', label: field.label, slot: field.slot, reason: 'empty', ok: false });
        return;
      }
      const ok = setNativeValue(el, value);
      events.push({
        op: 'fill_native',
        label: field.label,
        slot: field.slot,
        reason: ok ? 'input' : 'no_match',
        preview: log ? log.preview(value, field.slot) : '',
        ok: ok
      });
      if (ok) count++;
    });
    const projects = (profile.application && profile.application.projects) || [];
    projects.forEach((proj, i) => {
      if (projectNameEls[i] && !(blankOnly && fieldCurrentValue(projectNameEls[i])) && setNativeValue(projectNameEls[i], proj.name)) {
        count++;
        events.push({ op: 'fill_native', slot: 'application.projects.name', reason: 'input', ok: true, preview: proj.name });
      }
    });
    count += fillRadios(profile.universal);
    if (self.CareerOsBeisenFill && self.CareerOsBeisenFill.fill) {
      try {
        const extra = await self.CareerOsBeisenFill.fill(profile);
        if (extra && typeof extra === 'object') {
          count += extra.count || 0;
          (extra.events || []).forEach((ev) => events.push(ev));
        } else {
          count += extra || 0;
        }
      } catch (err) {
        events.push({ op: 'beisen_fill', reason: 'error', ok: false, error: String(err && err.message ? err.message : err) });
      }
    }
    const coverage = summarizeCoverage(events, collected);
    lastCoverage = coverage;
    const summary = {
      op: 'autofill',
      url: location.href,
      host: location.hostname,
      mode: fillCtx.mode,
      run_id: fillCtx.run_id || null,
      profile: (profile.universal && profile.universal.personal && profile.universal.personal.name) || '',
      test_only: fillCtx.mode === 'test',
      filled: count,
      attempted: events.length,
      ok: events.filter((e) => e.ok).length,
      skipped: events.filter((e) => !e.ok).length,
      coverage: coverage,
      items: events
    };
    if (log) log.send(summary);
    if (isTop) {
      renderCoverage(coverage);
      const gap = (coverage.required_empty || []).length + (coverage.widget_fail || []).length;
      showToast('写入 ' + count + ' 项' + (gap ? '，必填缺口 ' + gap : '，必填已清'));
    }
    return { count: count, coverage: coverage };
  }

  function fillRadios(univ) {
    const gender = ((univ.personal && univ.personal.gender) || '').trim();
    const marriage = ((univ.personal && univ.personal.marriage) || '').trim();
    let filledCount = 0;
    document.querySelectorAll('input[type="radio"]').forEach((radio) => {
      const label = radio.parentElement ? radio.parentElement.textContent.trim() : '';
      const ctx = getFieldContext(radio);
      if (gender && (/(性别)/.test(ctx) || label === gender) && label.includes(gender) && !radio.checked) {
        radio.click();
        radio.dispatchEvent(new Event('change', { bubbles: true }));
        filledCount++;
      }
      if (marriage && /(婚姻)/.test(ctx) && label.includes(marriage) && !radio.checked) {
        radio.click();
        radio.dispatchEvent(new Event('change', { bubbles: true }));
        filledCount++;
      }
    });
    return filledCount;
  }

  function showToast(msg) {
    if (!isTop || !document.body) return;
    const existing = document.querySelector('.career-os-toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'career-os-toast';
    const icon = document.createElement('span');
    icon.textContent = '⚡';
    const text = document.createElement('span');
    text.textContent = msg;
    toast.appendChild(icon);
    toast.appendChild(text);
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transition = 'opacity 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 2800);
  }

  function copyToClipboard(text, label) {
    if (!text) {
      showToast('该项为空，未复制');
      return;
    }
    navigator.clipboard.writeText(text).then(() => {
      showToast('已复制: ' + label);
    }).catch(() => {
      showToast('复制失败');
    });
  }

  function injectFloatingUI() {
    if (!isTop || !document.body) return;
    if (document.getElementById('career-os-floating-root')) return;

    const root = document.createElement('div');
    root.id = 'career-os-floating-root';

    const panel = document.createElement('div');
    panel.className = 'career-os-panel';
    panel.id = 'career-os-panel';
    panel.style.display = 'none';

    const header = document.createElement('div');
    header.className = 'career-os-header';
    const title = document.createElement('div');
    title.className = 'career-os-title';
    title.textContent = 'Career OS 填表助手';
    const closeBtn = document.createElement('div');
    closeBtn.className = 'career-os-close';
    closeBtn.id = 'career-os-close';
    closeBtn.textContent = '✕';
    header.appendChild(title);
    header.appendChild(closeBtn);

    const body = document.createElement('div');
    body.className = 'career-os-body';

    const fillBtn = document.createElement('button');
    fillBtn.className = 'career-os-btn-primary';
    fillBtn.id = 'career-os-fill-btn';
    fillBtn.textContent = '一键填充当前页面表单';

    const settingsBtn = document.createElement('button');
    settingsBtn.className = 'career-os-btn-secondary';
    settingsBtn.id = 'career-os-settings-btn';
    settingsBtn.textContent = '打开设置（只装插件也走这里）';

    const blankBtn = document.createElement('button');
    blankBtn.className = 'career-os-btn-secondary';
    blankBtn.id = 'career-os-blank-btn';
    blankBtn.textContent = '仅填空白';

    const captureBtn = document.createElement('button');
    captureBtn.className = 'career-os-btn-secondary';
    captureBtn.id = 'career-os-capture-btn';
    captureBtn.textContent = '捕获当前岗位 JD + 表单';

    const markBtn = document.createElement('button');
    markBtn.className = 'career-os-btn-secondary';
    markBtn.id = 'career-os-mark-btn';
    markBtn.textContent = '标记网页已提交';
    markBtn.disabled = true;

    const info = document.createElement('div');
    info.className = 'career-os-info-card';
    info.id = 'career-os-info-card';

    const coverage = document.createElement('div');
    coverage.className = 'career-os-coverage';
    coverage.id = 'career-os-coverage';

    const hint = document.createElement('div');
    hint.className = 'career-os-section-title';
    hint.textContent = '点页面格子：旁边会出现填入/复制，不用滚回这里';

    body.appendChild(fillBtn);
    body.appendChild(settingsBtn);
    body.appendChild(blankBtn);
    body.appendChild(captureBtn);
    body.appendChild(markBtn);
    body.appendChild(info);
    body.appendChild(coverage);
    body.appendChild(hint);
    panel.appendChild(header);
    panel.appendChild(body);

    const fab = document.createElement('div');
    fab.className = 'career-os-fab';
    fab.id = 'career-os-fab';
    fab.title = '填表菜单（格子旁可直接填/复制）';
    const fabIcon = document.createElement('span');
    fabIcon.className = 'career-os-fab-icon';
    fabIcon.textContent = '⚡';
    fab.appendChild(fabIcon);

    root.appendChild(panel);
    root.appendChild(fab);
    document.body.appendChild(root);

    fab.addEventListener('click', () => {
      isPanelOpen = !isPanelOpen;
      panel.style.display = isPanelOpen ? 'flex' : 'none';
      if (isPanelOpen) updateUI();
    });
    closeBtn.addEventListener('click', () => {
      isPanelOpen = false;
      panel.style.display = 'none';
    });
    fillBtn.addEventListener('click', () => {
      executeAutofill({ blankOnly: false });
    });
    settingsBtn.addEventListener('click', () => {
      chrome.runtime.sendMessage({ action: 'OPEN_OPTIONS' });
    });
    blankBtn.addEventListener('click', () => {
      executeAutofill({ blankOnly: true });
    });
    markBtn.addEventListener('click', () => {
      if (!fillCtx || (fillCtx.mode !== 'released' && fillCtx.mode !== 'volume') || !fillCtx.run_id) {
        showToast(fillCtx && fillCtx.mode === 'overlay'
          ? '设置页画像可填表，但投递记录请走海投/专投 run'
          : '没有已放行/海投载荷，不能标记已提交');
        return;
      }
      if (!lastCoverage || !lastCoverage.ready) {
        showToast('必填未清零，不能标记网页已提交');
        return;
      }
      chrome.runtime.sendMessage(
        { action: 'MARK_APPLIED', run_id: fillCtx.run_id, coverage: lastCoverage },
        (res) => {
          if (!res || !res.ok) {
            showToast((res && res.error) || '回写失败');
            return;
          }
          showToast('已记网页提交（未自动点按钮）');
        }
      );
    });
    captureBtn.addEventListener('click', () => {
      chrome.runtime.sendMessage({ action: 'CAPTURE_ACTIVE_TAB' }, (res) => {
        if (!res || !res.ok) {
          showToast((res && res.error) || '捕获失败');
          return;
        }
        if (res.via === 'project' || res.via === 'folder') {
          const where = res.path ? ' → ' + res.path : '';
          const via = res.via === 'project' ? '项目目录' : '绑定目录';
          showToast('已保存到' + via + '「' + (res.title || '当前岗位') + '」' + where);
        } else {
          showToast('未写入项目目录：请先运行 python bin/job_context_receiver.py，或打开插件点「绑定项目目录」');
        }
        updateUI();
      });
    });
    updateUI();
  }

  function setInfoRow(card, label, value) {
    const row = document.createElement('div');
    row.className = 'career-os-info-row';
    const l = document.createElement('span');
    l.className = 'career-os-info-label';
    l.textContent = label;
    const v = document.createElement('span');
    v.className = 'career-os-info-val';
    v.textContent = value || '—';
    row.appendChild(l);
    row.appendChild(v);
    card.appendChild(row);
  }

  function updateUI() {
    const card = document.getElementById('career-os-info-card');
    if (!card) return;
    card.textContent = '';
    const mode = (fillCtx && fillCtx.mode) || 'unknown';
    const name = profile && profile.universal && profile.universal.personal
      ? profile.universal.personal.name : '';
    const edu = profile && profile.universal && profile.universal.education
      ? profile.universal.education.undergraduate || {} : {};
    const title = (fillCtx && fillCtx.autofill && fillCtx.autofill.target_position)
      || (fillCtx && fillCtx.autofill && fillCtx.autofill.title)
      || (profile && profile.application && profile.application.target_position)
      || '';
    const modeLabel = mode === 'released'
      ? ('专投 released #' + (fillCtx.run_id || ''))
      : (mode === 'volume'
        ? ('海投 #' + (fillCtx.run_id || '') + ' ' + ((fillCtx.autofill && fillCtx.autofill.track) || ''))
        : (mode === 'overlay'
          ? '设置页画像'
          : (mode === 'test' ? '测试画像' : (mode === 'setup' ? '待设置底稿' : '未放行'))));
    setInfoRow(card, '模式', modeLabel);
    setInfoRow(card, '候选人', name + (mode === 'test' ? '（测试）' : ''));
    setInfoRow(card, '院校', [edu.school, edu.degree].filter(Boolean).join(' · '));
    setInfoRow(card, '求职意向', title);
    const fillBtn = document.getElementById('career-os-fill-btn');
    const blankBtn = document.getElementById('career-os-blank-btn');
    const blocked = !fillCtx || !fillCtx.allow_fill;
    if (fillBtn) fillBtn.disabled = blocked;
    if (blankBtn) blankBtn.disabled = blocked;
    if (blocked && fillCtx && fillCtx.reason) setInfoRow(card, '原因', fillCtx.reason);
    chrome.storage.local.get(['lastJobContext'], (stored) => {
      const last = stored.lastJobContext;
      if (last) {
        setInfoRow(card, '已捕获岗位', last.title || last.host || last.url);
        setInfoRow(card, '本页表单格子', String((last.form_schema || []).length));
      }
    });
    if (lastCoverage) renderCoverage(lastCoverage);
  }

  function renderCoverage(coverage) {
    const box = document.getElementById('career-os-coverage');
    const markBtn = document.getElementById('career-os-mark-btn');
    if (!box) return;
    lastCoverage = coverage;
    box.textContent = '';
    if (!coverage) return;
    const rows = [
      ['已写入', String(coverage.filled || 0)],
      ['必填已填清', coverage.ready ? '是' : '否'],
      ['必填空', (coverage.required_empty || []).slice(0, 6).join('、') || '无'],
      ['控件失败', (coverage.widget_fail || []).slice(0, 6).join('、') || '无'],
      ['未映射必填', (coverage.unmapped || []).slice(0, 6).join('、') || '无']
    ];
    rows.forEach((pair) => {
      const row = document.createElement('div');
      row.className = 'career-os-info-row';
      const l = document.createElement('span');
      l.className = 'career-os-info-label';
      l.textContent = pair[0];
      const v = document.createElement('span');
      v.className = 'career-os-info-val' + (pair[0] !== '已写入' && pair[1] !== '无' && pair[1] !== '是' ? ' career-os-warn' : '');
      v.textContent = pair[1];
      row.appendChild(l);
      row.appendChild(v);
      box.appendChild(row);
    });
    if (markBtn) {
      const fillReady = fillCtx && (fillCtx.mode === 'released' || fillCtx.mode === 'volume' || fillCtx.mode === 'overlay');
      markBtn.disabled = !(fillReady && coverage.ready);
    }
  }

  function renderCopyList() {
    const container = document.getElementById('career-os-copy-container');
    if (!container || !profile) return;
    const univ = profile.universal;
    const app = profile.application;
    const proj1 = (app.projects && app.projects[0]) || {};
    const proj2 = (app.projects && app.projects[1]) || {};
    const items = [
      { label: '自我评价', val: app.self_evaluation },
      { label: '专业技能', val: app.skills_summary },
      { label: '项目1', val: proj1.full_text || proj1.description },
      { label: '项目2', val: proj2.full_text || proj2.description },
      { label: '学历', val: univ.education && univ.education.undergraduate
        ? [univ.education.undergraduate.school, univ.education.undergraduate.major].filter(Boolean).join(' ')
        : '' },
      { label: '外语', val: univ.languages }
    ];
    ((fillCtx && fillCtx.autofill && fillCtx.autofill.open_answers) || []).forEach((ans) => {
      if (ans && ans.value) items.push({ label: ans.label || ans.key || '开放题', val: ans.value });
    });
    const ready = items.filter((x) => x.val);

    container.textContent = '';
    ready.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'career-os-copy-item';
      const name = document.createElement('span');
      name.className = 'career-os-copy-name';
      name.textContent = item.label;
      const btn = document.createElement('button');
      btn.className = 'career-os-copy-btn';
      btn.textContent = pickMode ? '填入' : '复制';
      btn.addEventListener('click', () => {
        if (pickMode && lastFieldEl) {
          const ok = setNativeValue(lastFieldEl, item.val);
          showToast(ok ? ('已填入: ' + item.label) : '该控件写不进去，已复制到剪贴板');
          if (!ok) copyToClipboard(item.val, item.label);
          return;
        }
        copyToClipboard(item.val, item.label);
      });
      row.appendChild(name);
      row.appendChild(btn);
      container.appendChild(row);
    });
  }

  chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
    if (req && req.action === 'PING') {
      sendResponse({ ok: true });
      return;
    }
    if (req && req.action === 'COPY_TEXT') {
      const text = req.text || '';
      navigator.clipboard.writeText(text).then(() => {
        if (!req.silent) showToast('JobContext 已复制到剪贴板');
        sendResponse({ ok: true });
      }).catch(() => sendResponse({ ok: false }));
      return true;
    }
    if (req && req.action === 'CAPTURE') {
      sendResponse({ ok: true, context: capturePageContext() });
      return;
    }
    if (req && req.action === 'READ_FIELD_VALUES') {
      const collected = collectFormFields();
      const fields = collected.fields.map((field, i) => {
        const el = collected.nodes[i];
        let value = '';
        if (el) {
          if (el.type === 'checkbox' || el.type === 'radio') value = el.checked ? (el.value || '1') : '';
          else value = String(el.value || '').trim();
        }
        return {
          label: field.label,
          slot: field.slot || '',
          value: value,
          required: !!field.required
        };
      }).filter((f) => f.value);
      sendResponse({ ok: true, fields: fields });
      return;
    }
    if (req && req.action === 'AUTOFILL') {
      if (isTop) injectFloatingUI();
      executeAutofill({ fill: req.fill, blankOnly: !!req.blankOnly }).then((result) => {
        sendResponse({
          success: true,
          count: (result && result.count) || 0,
          coverage: result && result.coverage,
          blocked: !!(result && result.blocked)
        });
      }).catch((err) => {
        sendResponse({ success: false, count: 0, error: String(err && err.message ? err.message : err) });
      });
      return true;
    }
  });

  function resolveValueForEl(el) {
    const fmap = self.CareerOsFieldMap;
    if (!fmap || !el) return null;
    const ctx = getFieldContext(el);
    const isTextarea = el.tagName && el.tagName.toLowerCase() === 'textarea';
    const slot = fmap.resolveSlot(ctx, { isTextarea: isTextarea });
    let value = fmap.matchAutofillValue({ label: ctx, slot: slot }, fillCtx && fillCtx.autofill);
    if (!value && slot && profile) value = fmap.valueForSlot(slot, profile, 0);
    if (!value && fillCtx && fillCtx.autofill && fillCtx.autofill.target_position && slot === 'application.target_position') {
      value = fillCtx.autofill.target_position;
    }
    const shortLabel = (ctx || slot || '当前格子').replace(/\s+/g, ' ').trim().slice(0, 24);
    return { label: shortLabel, slot: slot, value: value || '' };
  }

  function hideFieldChip() {
    const chip = document.getElementById('career-os-field-chip');
    if (chip) chip.style.display = 'none';
  }

  function placeChip(chip, el) {
    const r = el.getBoundingClientRect();
    const w = Math.min(320, window.innerWidth - 16);
    let left = r.left;
    if (left + w > window.innerWidth - 8) left = window.innerWidth - w - 8;
    if (left < 8) left = 8;
    let top = r.bottom + 6;
    chip.style.display = 'flex';
    const h = chip.offsetHeight || 48;
    if (top + h > window.innerHeight - 8) top = Math.max(8, r.top - h - 6);
    chip.style.left = left + 'px';
    chip.style.top = top + 'px';
    chip.style.width = w + 'px';
  }

  function showFieldChip(el) {
    if (!el || el.closest && el.closest('#career-os-floating-root, #career-os-field-chip')) return;
    const hit = resolveValueForEl(el);
    if (!hit) return;
    lastFieldEl = el;
    let chip = document.getElementById('career-os-field-chip');
    if (!chip) {
      chip = document.createElement('div');
      chip.id = 'career-os-field-chip';
      document.documentElement.appendChild(chip);
    }
    chip.textContent = '';
    const meta = document.createElement('div');
    meta.className = 'career-os-chip-meta';
    const name = document.createElement('div');
    name.className = 'career-os-chip-label';
    name.textContent = hit.label || '当前格子';
    const preview = document.createElement('div');
    preview.className = 'career-os-chip-preview';
    preview.textContent = hit.value ? String(hit.value).slice(0, 80) : '（底稿里没有对应内容）';
    meta.appendChild(name);
    meta.appendChild(preview);
    const actions = document.createElement('div');
    actions.className = 'career-os-chip-actions';
    const fillBtn = document.createElement('button');
    fillBtn.type = 'button';
    fillBtn.textContent = '填入';
    fillBtn.disabled = !hit.value;
    const copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.textContent = '复制';
    copyBtn.disabled = !hit.value;
    fillBtn.addEventListener('mousedown', (e) => e.preventDefault());
    copyBtn.addEventListener('mousedown', (e) => e.preventDefault());
    fillBtn.addEventListener('click', () => {
      const ok = setNativeValue(el, hit.value);
      showToast(ok ? '已填入: ' + hit.label : '控件写不进，已复制');
      if (!ok) copyToClipboard(hit.value, hit.label);
    });
    copyBtn.addEventListener('click', () => copyToClipboard(hit.value, hit.label));
    actions.appendChild(fillBtn);
    actions.appendChild(copyBtn);
    chip.appendChild(meta);
    chip.appendChild(actions);
    placeChip(chip, el);
  }

  function bindPageShortcuts() {
    const api = self.CareerOsShortcuts;
    if (!api) return;
    let map = null;
    api.load().then((s) => { map = s; });
    chrome.storage.onChanged.addListener((changes) => {
      if (changes.careerOsShortcuts) api.load().then((s) => { map = s; });
    });
    document.addEventListener('keydown', (e) => {
      if (!map) return;
      if (api.match(e, map.fill)) {
        e.preventDefault();
        executeAutofill({ blankOnly: false });
      } else if (api.match(e, map.blank)) {
        e.preventDefault();
        executeAutofill({ blankOnly: true });
      } else if (api.match(e, map.capture)) {
        e.preventDefault();
        chrome.runtime.sendMessage({ action: 'CAPTURE_ACTIVE_TAB' });
      } else if (api.match(e, map.focused)) {
        e.preventDefault();
        const el = lastFieldEl || document.activeElement;
        const hit = resolveValueForEl(el);
        if (hit && hit.value) {
          const ok = setNativeValue(el, hit.value);
          showToast(ok ? '已填入当前格子' : '写不进，已复制');
          if (!ok) copyToClipboard(hit.value, hit.label);
        } else showToast('当前格子没有对应底稿');
      } else if (api.match(e, map.copy)) {
        e.preventDefault();
        const el = lastFieldEl || document.activeElement;
        const hit = resolveValueForEl(el);
        if (hit && hit.value) copyToClipboard(hit.value, hit.label);
        else showToast('当前格子没有对应底稿');
      }
    }, true);
  }

  document.addEventListener('focusin', (ev) => {
    const el = ev.target;
    if (!el || !el.tagName) return;
    const tag = el.tagName.toLowerCase();
    if (tag !== 'input' && tag !== 'textarea' && tag !== 'select') return;
    if (el.type === 'hidden' || el.type === 'file' || el.type === 'checkbox' || el.type === 'radio') return;
    showFieldChip(el);
  });
  document.addEventListener('scroll', () => {
    if (lastFieldEl && document.activeElement === lastFieldEl) {
      const chip = document.getElementById('career-os-field-chip');
      if (chip && chip.style.display !== 'none') placeChip(chip, lastFieldEl);
    } else hideFieldChip();
  }, true);

  bindPageShortcuts();

  requestFillContext().then((ctx) => {
    applyFillContext(ctx);
    if (isTop) injectFloatingUI();
  }).catch(() => {
    requestProfile().then((bundle) => {
      profile = bundle.data || bundle;
      if (self.CareerOsFieldMap && self.CareerOsFieldMap.setRules) {
        self.CareerOsFieldMap.setRules(bundle.field_rules || []);
      }
      if (isTop) injectFloatingUI();
    }).catch((err) => {
      if (isTop) {
        console.warn('[Career OS] 画像未加载:', err.message || err);
      }
    });
  });
})();
