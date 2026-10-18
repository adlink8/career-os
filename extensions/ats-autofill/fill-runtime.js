/**
 * 校招网申站点识别 + 等表单 + 点「添加」。
 * 不自动点提交。大厂自建站走 generic，需用户「在当前页启用」。
 */
(function (root) {
  'use strict';

  function detect(href, hostname, hash) {
    var host = String(hostname || '').toLowerCase();
    var url = String(href || '');
    var h = String(hash || '');
    if (!h && url.indexOf('#') !== -1) h = url.slice(url.indexOf('#'));
    if (/zhiye\.com|italent\.cn|beisen\.com/.test(host)) {
      return { ats: 'beisen', label: '北森' };
    }
    if (/mokahr\.com|moka\.com/.test(host)) {
      return { ats: 'moka', label: 'Moka' };
    }
    if (/dayee\.com/.test(host)) return { ats: 'dayee', label: '大易' };
    if (/gllue\.com/.test(host)) return { ats: 'gllue', label: '孤鹿' };
    if (/hotjob\.cn/.test(host)) return { ats: 'hotjob', label: '热招' };
    if (/feishu\.cn|larkoffice\.com/.test(host)) return { ats: 'feishu', label: '飞书招聘' };
    if (/nowcoder\.com/.test(host)) return { ats: 'nowcoder', label: '牛客' };
    if (/zhipin\.com|zhaopin\.com|51job\.com|liepin\.com|lagou\.com|shixiseng\.com/.test(host)) {
      return { ats: 'portal', label: '招聘门户' };
    }
    return { ats: 'generic', label: '通用' };
  }

  function isApplyPage(site, href, hash) {
    var url = String(href || '');
    var h = String(hash || '');
    if (!h && url.indexOf('#') !== -1) h = url.slice(url.indexOf('#'));
    var ats = (site && site.ats) || detect(href, '', h).ats;
    if (ats === 'moka') {
      return /\/job\/[^/]+\/apply/i.test(h) || /\/apply\/[^/]+\/form/i.test(url);
    }
    if (ats === 'beisen') {
      return /\/form|\/apply|campus\/detail/i.test(url + h);
    }
    return true;
  }

  function notApplyMessage(site) {
    if (site && site.ats === 'moka') {
      return '这是 Moka 职位详情。请点「申请」进入报名表（地址带 /apply）再一键填充';
    }
    return '当前页还不是报名表，请进入填写页再试';
  }

  function rowCount(arr) {
    if (!Array.isArray(arr)) return 0;
    var n = 0;
    arr.forEach(function (row) {
      if (!row || typeof row !== 'object') return;
      var ok = Object.keys(row).some(function (k) {
        return String(row[k] == null ? '' : row[k]).trim() !== '';
      });
      if (ok) n += 1;
    });
    return n;
  }

  function extraClicks(need) {
    return Math.max(0, (need || 0) - 1);
  }

  function itemHasValue(item) {
    if (!item || typeof item !== 'object') return false;
    if (Array.isArray(item.fields)) {
      return item.fields.some(function (f) {
        return String(f && f.value == null ? '' : f.value).trim() !== '';
      });
    }
    return Object.keys(item).some(function (k) {
      return String(item[k] == null ? '' : item[k]).trim() !== '';
    });
  }

  function asNotebook(profile) {
    var overlay = root.CareerOsOverlay;
    if (!overlay || !profile) return profile;
    if (overlay.isNotebook(profile)) return profile;
    try { return overlay.normalizeImport(profile); } catch (_) { return profile; }
  }

  function expandPlan(notebook, shape) {
    var nb = asNotebook(notebook);
    var counts = {};
    function addCount(title, n) {
      title = String(title || '').trim();
      if (!title) return;
      counts[title] = Math.max(counts[title] || 0, n || 0);
    }
    if (nb && Array.isArray(nb.modules)) {
      nb.modules.forEach(function (m) {
        var n = 0;
        (m.items || []).forEach(function (item) {
          if (itemHasValue(item)) n += 1;
        });
        addCount(m.title, n);
      });
    } else if (notebook && notebook.application) {
      var app = notebook.application || {};
      var edu = (notebook.universal && notebook.universal.education) || {};
      var eduNeed = rowCount(edu.records);
      if (!eduNeed) {
        if (edu.undergraduate && (edu.undergraduate.school || edu.undergraduate.major)) eduNeed += 1;
        if (edu.junior_college && (edu.junior_college.school || edu.junior_college.major)) eduNeed += 1;
      }
      addCount('教育经历', eduNeed);
      addCount('实习经历', rowCount(app.internships));
      addCount('项目经历', rowCount(app.projects));
      addCount('在校职务', rowCount(app.campus_roles));
      addCount('在校实践', rowCount(app.campus_practices));
      addCount('获奖', rowCount(app.award_records));
      addCount('证书', rowCount(app.certificate_records));
      addCount('家庭成员', rowCount(app.family_members));
      addCount('培训经历', rowCount(app.training_records));
    }
    if (shape && Array.isArray(shape.modules)) {
      shape.modules.forEach(function (m) {
        var want = Number(m && m.count);
        if (want > 0) addCount(m.title, want);
      });
    }
    var plan = {};
    Object.keys(counts).forEach(function (title) {
      plan[title] = extraClicks(counts[title]);
    });
    return plan;
  }

  function classifyAdd(el, notebook) {
    var titles = [];
    var nb = asNotebook(notebook);
    if (nb && Array.isArray(nb.modules)) {
      nb.modules.forEach(function (m) {
        if (m && m.title) titles.push(String(m.title).trim());
      });
    }
    function matchTitle(t) {
      var i;
      for (i = 0; i < titles.length; i++) {
        if (!titles[i]) continue;
        if (t === titles[i] || t.indexOf(titles[i]) !== -1 || titles[i].indexOf(t) !== -1) return titles[i];
      }
      return '';
    }
    var node = el;
    var i;
    for (i = 0; i < 10 && node; i++) {
      var prev = node.previousElementSibling;
      while (prev) {
        var t = String(prev.textContent || '').replace(/\s+/g, ' ').trim();
        if (t && t.length < 24) {
          var hit = matchTitle(t);
          if (hit) return hit;
          if (/项目/.test(t)) return matchTitle('项目经历') || '项目经历';
          if (/实习|工作经历/.test(t)) return matchTitle('实习经历') || '实习经历';
          if (/教育/.test(t)) return matchTitle('教育经历') || '教育经历';
          if (/家庭/.test(t)) return matchTitle('家庭成员') || '家庭成员';
          if (/培训/.test(t)) return matchTitle('培训经历') || '培训经历';
          if (/校园|在校职务|职务/.test(t)) return matchTitle('在校职务') || '在校职务';
          if (/实践/.test(t)) return matchTitle('在校实践') || '在校实践';
          if (/证书/.test(t)) return matchTitle('证书') || '证书';
          if (/获奖/.test(t)) return matchTitle('获奖') || '获奖';
        }
        prev = prev.previousElementSibling;
      }
      node = node.parentElement;
    }
    return '';
  }

  function findAddButtons(doc) {
    if (!doc || !doc.querySelectorAll) return [];
    var out = [];
    doc.querySelectorAll('button, a, [role="button"], span, div').forEach(function (el) {
      if (el.closest && el.closest('#career-os-floating-root')) return;
      var raw = String(el.textContent || '').trim();
      var t = raw.replace(/\s+/g, '');
      if (t !== '添加' && t !== '+添加' && t !== '添加一段') return;
      if (raw.length > 12) return;
      out.push(el);
    });
    return out;
  }

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function setNativeValue(element, value) {
    if (!element || value === undefined || value === null) return false;
    var str = String(value).trim();
    if (!str) return false;
    if (element.disabled) return false;
    var win = typeof window !== 'undefined' ? window : root;
    var tag = String(element.tagName || '').toLowerCase();
    if (tag === 'select') {
      var lower = str.toLowerCase();
      var matched = false;
      var opts = element.options || [];
      var i;
      for (i = 0; i < opts.length; i++) {
        var opt = opts[i];
        var t = String((opt && opt.text) || '').trim();
        var v = String((opt && opt.value) || '').trim();
        if (t === str || v === str || t.indexOf(str) !== -1 || str.indexOf(t) !== -1 || t.toLowerCase() === lower) {
          element.value = opt.value;
          matched = true;
        }
      }
      if (!matched) return false;
      element.dispatchEvent(new Event('input', { bubbles: true }));
      element.dispatchEvent(new Event('change', { bubbles: true }));
      return true;
    }

    if (element.readOnly) {
      try { element.readOnly = false; } catch (_) { /* ignore */ }
    }

    var isTextarea = tag === 'textarea';
    var prototype = isTextarea
      ? (win.HTMLTextAreaElement && win.HTMLTextAreaElement.prototype)
      : (win.HTMLInputElement && win.HTMLInputElement.prototype);
    var ownDesc = Object.getOwnPropertyDescriptor(element, 'value');
    var protoDesc = prototype ? Object.getOwnPropertyDescriptor(prototype, 'value') : null;
    var writeValue = str;
    if (element.type === 'date' && /^\d{4}-\d{2}$/.test(str)) writeValue = str + '-01';
    if (element._valueTracker && typeof element._valueTracker.setValue === 'function') {
      element._valueTracker.setValue('');
    }
    if (protoDesc && protoDesc.set && ownDesc && ownDesc.set !== protoDesc.set) protoDesc.set.call(element, writeValue);
    else if (ownDesc && ownDesc.set) ownDesc.set.call(element, writeValue);
    else if (protoDesc && protoDesc.set) protoDesc.set.call(element, writeValue);
    else element.value = writeValue;

    element.dispatchEvent(new Event('input', { bubbles: true }));
    try {
      element.dispatchEvent(new InputEvent('input', {
        bubbles: true,
        cancelable: true,
        data: writeValue,
        inputType: 'insertText'
      }));
    } catch (_) { /* older browsers */ }
    element.dispatchEvent(new Event('change', { bubbles: true }));
    try { element.dispatchEvent(new Event('blur', { bubbles: true })); } catch (_) { /* ignore */ }
    return true;
  }

  function cleanTitle(el) {
    var t = String((el && el.textContent) || '').replace(/\s+/g, ' ').trim();
    if (!t || t.length >= 24) return '';
    if (/添加|暂存/.test(t)) return '';
    return t;
  }

  function classNameOf(el) {
    return String((el && el.className) || '');
  }

  function isSectionHeading(el) {
    if (!el) return false;
    if (el.tagName && /^H[1-4]$/.test(el.tagName)) return true;
    var cls = classNameOf(el);
    if (el.classList && el.classList.contains('module-title')) return true;
    if (el.classList && el.classList.contains('el-collapse-item__header')) return true;
    if (cls.indexOf('collapse-item__header') !== -1) return true;
    return false;
  }

  function isCollapseItem(el) {
    var cls = classNameOf(el);
    if (!cls) return false;
    if (cls.indexOf('collapse-item__') !== -1) return false;
    return cls.indexOf('collapse-item') !== -1;
  }

  function headingIn(el) {
    if (!el) return '';
    if (isSectionHeading(el)) return cleanTitle(el);
    if (!isCollapseItem(el) || !el.querySelector) return '';
    var header = el.querySelector('.el-collapse-item__header, [class*="collapse-item__header"], .module-title');
    return header ? cleanTitle(header) : '';
  }

  function nearbySection(el) {
    var n = el;
    var depth = 0;
    while (n && depth < 14) {
      var prev = n.previousElementSibling;
      while (prev) {
        var t = headingIn(prev);
        if (t) return t;
        prev = prev.previousElementSibling;
      }
      if (n !== el) {
        var own = headingIn(n);
        if (own) return own;
      }
      n = n.parentElement;
      depth += 1;
    }
    return '';
  }

  function itemLabel(item) {
    if (!item) return '';
    var near = nearbyLabel(item.querySelector && item.querySelector('input, textarea, select') || item);
    if (near) return near;
    var lab = item.querySelector
      ? item.querySelector('.el-form-item__label, .ant-form-item-label, .bs-form-item-label, label')
      : null;
    var t = String((lab && lab.textContent) || '').replace(/\s+/g, ' ').trim();
    if (t && t.length <= 20 && !/首页|投递记录|上传简历/.test(t)) return t;
    return '';
  }

  function collectFormItems(doc) {
    doc = doc || (typeof document !== 'undefined' ? document : null);
    if (!doc || !doc.querySelectorAll) return [];
    var seen = [];
    var out = [];
    function push(item, label) {
      if (!item || seen.indexOf(item) !== -1) return;
      if (item.closest && item.closest('#career-os-floating-root')) return;
      label = String(label || '').replace(/\s+/g, ' ').trim();
      if (!label || label.length > 40) return;
      if (/搜索职位|添加|暂存|取消|预览并提交|立即投递|至今/.test(label)) return;
      seen.push(item);
      out.push({ item: item, label: label, section: nearbySection(item) });
    }
    doc.querySelectorAll('.el-form-item, .ant-form-item, .bs-form-item').forEach(function (item) {
      push(item, itemLabel(item));
    });
    doc.querySelectorAll(
      '.el-date-editor, .el-select, .el-input, .el-textarea, .ant-select, .ant-picker, .el-cascader'
    ).forEach(function (widget) {
      var item = (widget.closest && widget.closest('.el-form-item, .ant-form-item, .bs-form-item'))
        || widget.parentElement;
      if (!item || seen.indexOf(item) !== -1) return;
      push(item, itemLabel(item) || itemLabel(widget.parentElement));
    });
    return out;
  }

  function fieldValue(item) {
    var input = item && item.querySelector
      ? item.querySelector('textarea, input:not([type="hidden"]):not([type="file"])')
      : null;
    if (!input) return '';
    if (input.type === 'checkbox' || input.type === 'radio') return input.checked ? (input.value || '1') : '';
    return String(input.value || '').trim();
  }

  function collectAdaptiveFields(doc) {
    return collectFormItems(doc).map(function (entry) {
      return {
        section: entry.section || '',
        label: entry.label,
        value: fieldValue(entry.item)
      };
    });
  }

  function nearbyLabel(el) {
    if (!el) return '';
    function clean(t) {
      t = String(t || '').replace(/\s+/g, ' ').trim();
      t = t.replace(/^请输入\d*位?/, '').replace(/请输入|请选择|请填写/g, '').trim();
      if (!t || t.length > 20) return '';
      if (/首页|了解先导|投递记录|上传简历|预览并提交|搜索职位|立即投递|我的简历/.test(t)) return '';
      return t;
    }
    var doc = el.ownerDocument;
    var labelled = el.getAttribute && el.getAttribute('aria-labelledby');
    if (labelled && doc && doc.getElementById) {
      var by = clean((doc.getElementById(labelled) || {}).textContent);
      if (by) return by;
    }
    var aria = clean(el.getAttribute && el.getAttribute('aria-label'));
    if (aria) return aria;
    var node = el;
    var depth = 0;
    while (node && depth < 8) {
      var prev = node.previousElementSibling;
      while (prev) {
        var c = clean(prev.textContent);
        if (c) return c;
        var inner = prev.querySelector && prev.querySelector('.el-form-item__label, .ant-form-item-label, .bs-form-item-label, label');
        if (inner) {
          c = clean(inner.textContent);
          if (c) return c;
        }
        prev = prev.previousElementSibling;
      }
      var td = node.tagName === 'TD' ? node : null;
      if (!td && node.parentElement && node.parentElement.tagName === 'TD') td = node.parentElement;
      if (td && td.parentElement) {
        var th = td.parentElement.querySelector('th');
        var ht = th && clean(th.textContent);
        if (ht) return ht;
      }
      node = node.parentElement;
      depth += 1;
    }
    return '';
  }

  function formReady(doc) {
    if (!doc || !doc.querySelectorAll) return false;
    var hit = 0;
    doc.querySelectorAll('input:not([type="hidden"]):not([type="file"]), textarea').forEach(function (el) {
      if (el.id === 'moka-version') return;
      var blob = [el.placeholder, el.getAttribute('aria-label'), el.parentElement && el.parentElement.textContent]
        .join(' ')
        .slice(0, 80);
      if (/姓名|手机|邮箱|学校/.test(blob)) hit += 1;
    });
    return hit >= 1;
  }

  function waitForForm(doc, timeoutMs) {
    timeoutMs = timeoutMs || 1200;
    return new Promise(function (resolve) {
      if (formReady(doc)) {
        resolve(true);
        return;
      }
      var started = Date.now();
      var timer = setInterval(function () {
        if (formReady(doc) || Date.now() - started > timeoutMs) {
          clearInterval(timer);
          resolve(formReady(doc));
        }
      }, 200);
    });
  }

  async function expandRepeatable(doc, profile) {
    if (!doc) return 0;
    var plan = expandPlan(profile);
    var remain = {};
    Object.keys(plan || {}).forEach(function (k) { remain[k] = plan[k]; });
    var clicks = 0;
    var guard = 0;
    while (guard < 8) {
      guard += 1;
      var buttons = findAddButtons(doc);
      var did = false;
      var i;
      for (i = 0; i < buttons.length; i++) {
        var kind = classifyAdd(buttons[i], profile);
        if (!kind || !remain[kind]) continue;
        try { buttons[i].click(); } catch (_) { continue; }
        remain[kind] -= 1;
        clicks += 1;
        did = true;
        await sleep(60);
        break;
      }
      if (!did) break;
    }
    return clicks;
  }

  async function revealForm(doc, win) {
    if (!doc) return;
    win = win || doc.defaultView;
    var root = doc.scrollingElement || doc.documentElement;
    var body = doc.body;
    var max = Math.max(
      (root && root.scrollHeight) || 0,
      (body && body.scrollHeight) || 0
    );
    var view = (win && win.innerHeight) || 800;
    var stops = [0, 0.2, 0.4, 0.6, 0.8, 1];
    var i;
    for (i = 0; i < stops.length; i++) {
      var y = Math.max(0, Math.floor((max - view) * stops[i]));
      if (win && win.scrollTo) win.scrollTo(0, y);
      else if (root) root.scrollTop = y;
      await sleep(160);
    }
    if (doc.querySelectorAll) {
      doc.querySelectorAll('[class*="scroll"], [class*="content"], .ant-drawer-body, .el-dialog__body').forEach(function (p) {
        try {
          if (p.scrollHeight > p.clientHeight + 40) p.scrollTop = p.scrollHeight;
        } catch (_) { /* ignore */ }
      });
    }
    await sleep(180);
    if (win && win.scrollTo) win.scrollTo(0, 0);
  }

  root.CareerOsFillRuntime = {
    detect: detect,
    isApplyPage: isApplyPage,
    notApplyMessage: notApplyMessage,
    rowCount: rowCount,
    extraClicks: extraClicks,
    expandPlan: expandPlan,
    classifyAdd: classifyAdd,
    findAddButtons: findAddButtons,
    formReady: formReady,
    waitForForm: waitForForm,
    expandRepeatable: expandRepeatable,
    revealForm: revealForm,
    nearbyLabel: nearbyLabel,
    nearbySection: nearbySection,
    collectFormItems: collectFormItems,
    collectAdaptiveFields: collectAdaptiveFields,
    sleep: sleep,
    setNativeValue: setNativeValue
  };
})(typeof self !== 'undefined' ? self : this);
