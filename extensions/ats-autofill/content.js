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
  let isPanelOpen = false;

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
        resolve(res.data);
      });
    });
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
    while (parent && depth < 4) {
      const labelEl = parent.querySelector(
        'label, .el-form-item__label, .ant-form-item-label, .bs-form-item-label, .title, .item-label, th'
      );
      if (labelEl) {
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

  function executeAutofill() {
    if (!profile || !profile.universal || !profile.application) {
      showToast('画像未加载，请先运行 sync_autofill_profile.py 后重载扩展');
      return 0;
    }
    const fmap = self.CareerOsFieldMap;
    if (!fmap) {
      showToast('字段映射未加载，请重载扩展');
      return 0;
    }
    const collected = collectFormFields();
    let count = 0;
    const projectNameEls = [];
    collected.fields.forEach((field, i) => {
      const el = collected.nodes[i];
      if (!el || el.disabled || el.readOnly) return;
      if (el.type === 'radio' || el.type === 'checkbox') return;
      if (field.slot === 'application.projects.name') {
        projectNameEls.push(el);
        return;
      }
      if (!field.slot) return;
      const value = fmap.valueForSlot(field.slot, profile, 0);
      if (field.slot === 'universal.personal.id_card' && !fmap.isRealIdCard(value)) return;
      if (setNativeValue(el, value)) count++;
    });
    const projects = profile.application.projects || [];
    projects.forEach((proj, i) => {
      if (projectNameEls[i] && setNativeValue(projectNameEls[i], proj.name)) count++;
    });
    count += fillRadios(profile.universal);
    if (isTop) {
      showToast('已按本页 ' + collected.fields.length + ' 个格子填入 ' + count + ' 项');
    }
    return count;
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

    const captureBtn = document.createElement('button');
    captureBtn.className = 'career-os-btn-secondary';
    captureBtn.id = 'career-os-capture-btn';
    captureBtn.textContent = '捕获当前岗位 JD + 表单';

    const info = document.createElement('div');
    info.className = 'career-os-info-card';
    info.id = 'career-os-info-card';

    const copyTitle = document.createElement('div');
    copyTitle.className = 'career-os-section-title';
    copyTitle.textContent = '快捷复制';
    const copyList = document.createElement('div');
    copyList.className = 'career-os-copy-list';
    copyList.id = 'career-os-copy-container';

    body.appendChild(fillBtn);
    body.appendChild(captureBtn);
    body.appendChild(info);
    body.appendChild(copyTitle);
    body.appendChild(copyList);
    panel.appendChild(header);
    panel.appendChild(body);

    const fab = document.createElement('div');
    fab.className = 'career-os-fab';
    fab.id = 'career-os-fab';
    fab.title = 'Career OS 自动填表';
    const fabIcon = document.createElement('span');
    fabIcon.className = 'career-os-fab-icon';
    fabIcon.textContent = '⚡';
    const fabText = document.createElement('span');
    fabText.textContent = 'Career OS 填表';
    fab.appendChild(fabIcon);
    fab.appendChild(fabText);

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
      executeAutofill();
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
    if (!card || !profile) return;
    card.textContent = '';
    const univ = profile.universal || {};
    const app = profile.application || {};
    const p = univ.personal || {};
    const edu = (univ.education && univ.education.undergraduate) || {};
    setInfoRow(card, '候选人', p.name);
    setInfoRow(card, '院校', [edu.school, edu.degree].filter(Boolean).join(' · '));
    setInfoRow(card, '求职意向', app.target_position);
    const proj0 = app.projects && app.projects[0];
    setInfoRow(card, '首个项目', proj0 ? proj0.name : '');
    chrome.storage.local.get(['lastJobContext'], (stored) => {
      const last = stored.lastJobContext;
      if (last) {
        setInfoRow(card, '已捕获岗位', last.title || last.host || last.url);
        setInfoRow(card, '本页表单格子', String((last.form_schema || []).length));
      }
    });
    renderCopyList();
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
      { label: '学历', val: [univ.education.undergraduate.school, univ.education.undergraduate.major].filter(Boolean).join(' ') },
      { label: '外语', val: univ.languages }
    ].filter((x) => x.val);

    container.textContent = '';
    items.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'career-os-copy-item';
      const name = document.createElement('span');
      name.className = 'career-os-copy-name';
      name.textContent = item.label;
      const btn = document.createElement('button');
      btn.className = 'career-os-copy-btn';
      btn.textContent = '复制';
      btn.addEventListener('click', () => copyToClipboard(item.val, item.label));
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
    if (req && req.action === 'AUTOFILL') {
      if (isTop) injectFloatingUI();
      const run = () => {
        const count = executeAutofill();
        sendResponse({ success: true, count: count });
      };
      if (!profile) {
        requestProfile().then((data) => {
          profile = data;
          if (isTop) updateUI();
          run();
        }).catch((err) => {
          showToast(String(err.message || err));
          sendResponse({ success: false, count: 0, error: String(err.message || err) });
        });
        return true;
      }
      run();
    }
  });

  requestProfile().then((data) => {
    profile = data;
    if (isTop) injectFloatingUI();
  }).catch((err) => {
    if (isTop) {
      console.warn('[Career OS] 画像未加载:', err.message || err);
    }
  });
})();
