/**
 * 北森/Element 表单项填充：el-select、日期、级联、自定义单选。
 */
(function (root) {
  'use strict';

  function sleep(ms) {
    return new Promise(function (resolve) { setTimeout(resolve, ms); });
  }

  function textOf(el) {
    return ((el && el.textContent) || '').replace(/\s+/g, ' ').trim();
  }

  function asDate(val) {
    var s = String(val || '').trim();
    if (/^\d{4}-\d{2}$/.test(s)) return s + '-01';
    return s;
  }

  function itemLabel(item) {
    var lab = item.querySelector(
      '.el-form-item__label, .ant-form-item-label, .bs-form-item-label, label, [class*="ItemLabel"], [class*="item-label"]'
    );
    return textOf(lab);
  }

  function collectItems() {
    var nodes = document.querySelectorAll(
      '.el-form-item, .ant-form-item, .bs-form-item, [class*="form-item"], [class*="formItem"]'
    );
    var out = [];
    nodes.forEach(function (item) {
      if (item.closest('#career-os-floating-root')) return;
      var label = itemLabel(item);
      if (!label || label.length > 40) return;
      if (/搜索职位|添加|暂存|取消|预览并提交|立即投递/.test(label)) return;
      out.push({ item: item, label: label });
    });
    return out;
  }

  function pickValue(label, section, profile, fmap) {
    var slot = fmap.resolveSlot(label, {
      isTextarea: /描述|内容|评价|介绍/.test(label)
    });
    if (/开始时间|起始/.test(label)) {
      if (section === 'edu') slot = 'universal.education.undergraduate.start_date';
      else if (section === 'project') slot = 'application.projects.start_date';
      else if (section === 'intern') slot = 'application.internships.start_date';
      else if (section === 'practice') slot = 'application.campus_practices.start_date';
      else if (section === 'campus_role') slot = 'application.campus_roles.start_date';
    } else if (/结束时间|毕业时间/.test(label)) {
      if (section === 'edu') slot = 'universal.education.undergraduate.graduation';
      else if (section === 'project') slot = 'application.projects.end_date';
      else if (section === 'intern') slot = 'application.internships.end_date';
      else if (section === 'practice') slot = 'application.campus_practices.end_date';
      else if (section === 'campus_role') slot = 'application.campus_roles.end_date';
    } else if (/^城市$|所在城市/.test(label) && section === 'edu') {
      slot = 'universal.personal.current_city';
    }
    var value = fmap.valueForSlot(slot, profile, 0);
    if (/毕业时间|结束时间|开始时间|出生日期/.test(label)) value = asDate(value);
    return { slot: slot, value: value };
  }

  function detectSection(label, prev) {
    if (/教育经历|学校名称|所学专业|学习形式/.test(label)) return 'edu';
    if (/实习经历|单位名称/.test(label)) return 'intern';
    if (/项目经历|项目名称/.test(label)) return 'project';
    if (/在校实践|实践名称|实践描述/.test(label)) return 'practice';
    if (/职务名称|职务描述/.test(label)) return 'campus_role';
    if (/获奖/.test(label)) return 'award';
    if (/证书名称|获得时间/.test(label)) return 'cert';
    if (/语言类型|掌握程度|^听说$|^读写$/.test(label)) return 'lang';
    if (/个人信息|姓名|手机|邮箱/.test(label)) return 'personal';
    return prev;
  }

  function nativeInput(item) {
    return item.querySelector('textarea, input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="file"])');
  }

  function setInput(el, value) {
    if (!el || !value) return false;
    var proto = el.tagName.toLowerCase() === 'textarea'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    var desc = Object.getOwnPropertyDescriptor(proto, 'value');
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
    return true;
  }

  function visibleOptions() {
    var sels = [
      '.el-select-dropdown:not([style*="display: none"]) .el-select-dropdown__item',
      '.el-cascader-menu .el-cascader-node',
      '.el-picker-panel:not([style*="display: none"]) td.available',
      '[class*="dropdown"]:not([style*="display: none"]) li',
      '[class*="option"]'
    ];
    var found = [];
    sels.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        if (el.closest('#career-os-floating-root')) return;
        if (el.offsetParent === null && !el.classList.contains('el-cascader-node')) return;
        found.push(el);
      });
    });
    return found;
  }

  function optionCandidates(value) {
    var want = String(value).trim();
    var out = [];
    function add(p) {
      p = String(p || '').trim();
      if (p && out.indexOf(p) === -1) out.push(p);
    }
    add(want);
    want.split(/[、,，]/).forEach(add);
    out.slice().forEach(function (p) {
      if (p && p.charAt(p.length - 1) !== '市' && p.length <= 4) add(p + '市');
    });
    return out;
  }

  function clickMatchingOption(value) {
    var opts = visibleOptions();
    var wants = optionCandidates(value);
    var hit = null;
    wants.forEach(function (want) {
      if (hit) return;
      opts.forEach(function (el) {
        if (hit) return;
        var t = textOf(el);
        if (!t || t.length > 80) return;
        if (t === want || t.indexOf(want) !== -1 || want.indexOf(t) !== -1) hit = el;
      });
    });
    if (!hit) return false;
    hit.click();
    return true;
  }

  async function fillDropdown(item, value) {
    var wrap = item.querySelector('.el-select, .el-cascader, [class*="select"]') || item;
    var input = wrap.querySelector('input') || nativeInput(item);
    wrap.click();
    if (input) input.click();
    await sleep(180);
    if (input) setInput(input, value);
    await sleep(220);
    if (clickMatchingOption(value)) {
      await sleep(80);
      return true;
    }
    if (input) {
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      await sleep(80);
      return Boolean(input.value);
    }
    return false;
  }

  function fillRadioLike(item, value) {
    var want = String(value).trim();
    if (!want) return false;
    var hit = null;
    item.querySelectorAll('label, span, div, .el-radio, .el-radio-button').forEach(function (el) {
      if (hit) return;
      var t = textOf(el);
      if (t === want || t.indexOf(want) !== -1) hit = el;
    });
    if (!hit) return false;
    hit.click();
    return true;
  }

  async function fillItem(entry, section, profile, fmap) {
    var label = entry.label;
    var item = entry.item;
    var picked = pickValue(label, section, profile, fmap);
    var value = picked.value;
    var slot = picked.slot || '';
    if (!slot) return { ok: false, reason: 'unmapped', slot: '', value: '' };
    if (!value) return { ok: false, reason: 'empty', slot: slot, value: '' };
    if (slot.indexOf('id_card') !== -1 && !fmap.isRealIdCard(value)) {
      return { ok: false, reason: 'skip_id', slot: slot, value: '' };
    }

    var input = nativeInput(item);
    var hasSelect = item.querySelector('.el-select, .el-cascader, .el-date-editor');
    var ok = false;
    var how = 'input';
    if (/性别|婚姻/.test(label)) {
      ok = fillRadioLike(item, value) || fillRadioLike(item.parentElement, value);
      how = 'radio';
    }
    if (!ok && hasSelect) {
      ok = await fillDropdown(item, value);
      how = 'dropdown';
    }
    if (!ok && input) {
      ok = setInput(input, value);
      how = 'input';
    }
    if (!ok) {
      ok = await fillDropdown(item, value);
      how = 'dropdown';
    }
    return { ok: ok, reason: ok ? how : 'no_match', slot: slot, value: value };
  }

  async function fill(profile) {
    var fmap = root.CareerOsFieldMap;
    var events = [];
    if (!fmap || !profile) return { count: 0, events: events };
    var items = collectItems();
    var section = 'personal';
    var count = 0;
    for (var i = 0; i < items.length; i++) {
      var entry = items[i];
      section = detectSection(entry.label, section);
      try {
        var result = await fillItem(entry, section, profile, fmap);
        events.push({
          op: 'fill_item',
          label: entry.label,
          section: section,
          slot: result.slot,
          reason: result.reason,
          preview: root.CareerOsLog ? root.CareerOsLog.preview(result.value, result.slot) : '',
          ok: result.ok
        });
        if (result.ok) count++;
      } catch (err) {
        events.push({
          op: 'fill_item',
          label: entry.label,
          section: section,
          reason: 'error',
          ok: false,
          error: String(err && err.message ? err.message : err)
        });
      }
    }
    return { count: count, events: events };
  }

  root.CareerOsBeisenFill = { fill: fill, collectItems: collectItems };
})(typeof self !== 'undefined' ? self : this);
