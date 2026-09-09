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

  function dateVariants(val) {
    var s = String(val || '').trim();
    var out = [];
    function add(p) {
      p = String(p || '').trim();
      if (p && out.indexOf(p) === -1) out.push(p);
    }
    add(s);
    if (/^\d{4}-\d{2}$/.test(s)) {
      add(s + '-01');
      add(s.replace('-', '年') + '月');
    }
    if (/^\d{4}-\d{2}-\d{2}$/.test(s)) add(s.slice(0, 7));
    return out;
  }

  function itemLabel(item) {
    if (!item) return '';
    var runtime = root.CareerOsFillRuntime;
    if (runtime && runtime.nearbyLabel) {
      var near = runtime.nearbyLabel(item.querySelector('input, textarea, select') || item);
      if (near) return near;
    }
    var lab = item.querySelector('.el-form-item__label, .ant-form-item-label, .bs-form-item-label, label');
    var t = textOf(lab);
    if (t && t.length <= 20 && !/首页|投递记录|上传简历/.test(t)) return t;
    return '';
  }

  function collectItems() {
    var seen = [];
    var out = [];
    function push(item, label) {
      if (!item || seen.indexOf(item) !== -1) return;
      if (item.closest && item.closest('#career-os-floating-root')) return;
      label = String(label || '').replace(/\s+/g, ' ').trim();
      if (!label || label.length > 40) return;
      if (/搜索职位|添加|暂存|取消|预览并提交|立即投递|至今/.test(label)) return;
      seen.push(item);
      out.push({ item: item, label: label });
    }
    document.querySelectorAll('.el-form-item, .ant-form-item, .bs-form-item').forEach(function (item) {
      push(item, itemLabel(item));
    });
    document.querySelectorAll(
      '.el-date-editor, .el-select, .el-input, .el-textarea, .ant-select, .ant-picker, .el-cascader'
    ).forEach(function (widget) {
      var item = widget.closest('.el-form-item, .ant-form-item, .bs-form-item') || widget.parentElement;
      if (!item || seen.indexOf(item) !== -1) return;
      push(item, itemLabel(item) || itemLabel(widget.parentElement));
    });
    return out;
  }

  function pickValue(label, section, profile, fmap, index) {
    var slot = fmap.resolveSlot(label, {
      isTextarea: /描述|内容|评价|介绍/.test(label)
    });
    if (/开始时间|起始|就读时间|起止时间|活动时间/.test(label)) {
      if (section === 'edu') slot = 'universal.education.undergraduate.start_date';
      else if (section === 'project') slot = 'application.projects.start_date';
      else if (section === 'intern') slot = 'application.internships.start_date';
      else if (section === 'practice') slot = 'application.campus_practices.start_date';
      else if (section === 'campus_role') slot = 'application.campus_roles.start_date';
      else if (section === 'award') slot = 'application.award_records.date';
    } else if (/结束时间|毕业时间/.test(label)) {
      if (section === 'edu') slot = 'universal.education.undergraduate.graduation';
      else if (section === 'project') slot = 'application.projects.end_date';
      else if (section === 'intern') slot = 'application.internships.end_date';
      else if (section === 'practice') slot = 'application.campus_practices.end_date';
      else if (section === 'campus_role') slot = 'application.campus_roles.end_date';
    } else if (/^城市$|所在城市/.test(label) && section === 'edu') {
      slot = 'universal.personal.current_city';
    }
    var value = fmap.valueForSlot(slot, profile, index || 0);
    return { slot: slot, value: value };
  }

  function detectSection(label, prev) {
    if (/教育经历|教育背景|学校名称|所学专业|学习形式|^学历$|专业排名|学院名称|成绩/.test(label)) return 'edu';
    if (/实习经历|单位名称/.test(label)) return 'intern';
    if (/项目经历|项目经验|项目名称/.test(label)) return 'project';
    if (/在校实践|实践名称|实践描述|活动时间/.test(label)) return 'practice';
    if (/职务名称|职务描述|在校职务/.test(label)) return 'campus_role';
    if (/获奖/.test(label)) return 'award';
    if (/证书名称|获得时间/.test(label)) return 'cert';
    if (/语言类型|掌握程度|^听说$|^读写$/.test(label)) return 'lang';
    if (/个人信息|姓名|手机|邮箱/.test(label)) return 'personal';
    return prev;
  }

  function isDateField(label, item) {
    if (/时间|日期|年月/.test(label || '')) return true;
    return !!(item && item.querySelector && item.querySelector('.el-date-editor, .ant-picker, .el-picker'));
  }

  function nativeInput(item) {
    return item.querySelector('textarea, input:not([type="hidden"]):not([type="radio"]):not([type="checkbox"]):not([type="file"])');
  }

  function setInput(el, value) {
    if (!el || !value) return false;
    if (el.readOnly) {
      try { el.readOnly = false; } catch (_) { /* ignore */ }
    }
    var proto = el.tagName.toLowerCase() === 'textarea'
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    var desc = Object.getOwnPropertyDescriptor(proto, 'value');
    if (el._valueTracker && typeof el._valueTracker.setValue === 'function') {
      el._valueTracker.setValue('');
    }
    if (desc && desc.set) desc.set.call(el, value);
    else el.value = value;
    el.dispatchEvent(new Event('input', { bubbles: true }));
    try {
      el.dispatchEvent(new InputEvent('input', { bubbles: true, data: value, inputType: 'insertText' }));
    } catch (_) { /* ignore */ }
    el.dispatchEvent(new Event('change', { bubbles: true }));
    el.dispatchEvent(new Event('blur', { bubbles: true }));
    return true;
  }

  function visibleOptions() {
    var sels = [
      '.el-select-dropdown:not([style*="display: none"]) .el-select-dropdown__item',
      '.el-cascader-menu .el-cascader-node',
      '.el-picker-panel:not([style*="display: none"]) td.available',
      '.ant-select-dropdown .ant-select-item',
      '.ant-select-item-option',
      '.ant-select-item-option-content',
      '.rc-select-dropdown .rc-select-item',
      'div[role="option"]',
      'li[role="option"]',
      '[class*="SelectOption"]',
      '[class*="select-option"]',
      '[class*="dropdown"]:not([style*="display: none"]) li',
      '[class*="option"]'
    ];
    var found = [];
    sels.forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        if (el.closest('#career-os-floating-root')) return;
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
      if (p && p.charAt(p.length - 1) === '市') add(p.slice(0, -1));
    });
    if (want === '男') { add('男性'); add('先生'); }
    if (want === '女') { add('女性'); add('女士'); }
    if (/共青团/.test(want)) { add('共青团员'); add('团员'); }
    if (want === '本科') { add('大学本科'); add('本科'); }
    if (want === '统招专升本') { add('专升本'); add('全日制'); add('普通全日制'); }
    if (/前\s*20%/.test(want)) { add('前20%'); add('前 20%'); add('其他'); }
    if (want === '英语' || /CET/.test(want)) { add('英语'); add('English'); }
    if (want === '中文') { add('汉语'); add('中文'); }
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
    if (!item || !value) return false;
    var wrap = item.querySelector('.el-select, .el-cascader, .ant-select, .rc-select') || item;
    var input = wrap.querySelector('input') || nativeInput(item);
    var shown0 = input ? String(input.value || '').trim() : '';
    if (shown0 && shown0 !== '请选择' && optionCandidates(value).some(function (w) {
      return shown0 === w || shown0.indexOf(w) !== -1;
    })) return true;
    if (input) setInput(input, value);
    shown0 = input ? String(input.value || '').trim() : '';
    if (shown0 && shown0 !== '请选择' && optionCandidates(value).some(function (w) {
      return shown0 === w || shown0.indexOf(w) !== -1;
    })) return true;
    wrap.click();
    if (input) input.click();
    await sleep(50);
    if (clickMatchingOption(value)) return true;
    if (input) setInput(input, value);
    await sleep(50);
    if (clickMatchingOption(value)) return true;
    shown0 = input ? String(input.value || '').trim() : '';
    return !!(shown0 && shown0 !== '请选择');
  }

  function parseDate(val) {
    var m = String(val || '').trim().match(/^(\d{4})-(\d{1,2})(?:-(\d{1,2}))?/);
    if (!m) return null;
    return new Date(Number(m[1]), Number(m[2]) - 1, m[3] ? Number(m[3]) : 1);
  }

  function datePayloads(val) {
    var out = [];
    var date = parseDate(val);
    if (date && !isNaN(date.getTime())) out.push(date);
    dateVariants(val).forEach(function (s) { out.push(s); });
    return out;
  }

  function walkVue(el) {
    var n = el;
    var i;
    for (i = 0; i < 14 && n; i++) {
      if (n.__vue__) return n.__vue__;
      if (n.__vueParentComponent) return n.__vueParentComponent;
      n = n.parentElement;
    }
    return null;
  }

  function emitVueDate(vm, payloads) {
    if (!vm) return;
    var i;
    for (i = 0; i < payloads.length; i++) {
      var v = payloads[i];
      try { if (typeof vm.$emit === 'function') vm.$emit('input', v); } catch (_) { /* ignore */ }
      try { if (typeof vm.$emit === 'function') vm.$emit('update:modelValue', v); } catch (_) { /* ignore */ }
      try { if (typeof vm.$emit === 'function') vm.$emit('change', v); } catch (_) { /* ignore */ }
      try { if (typeof vm.handleChange === 'function') vm.handleChange(v); } catch (_) { /* ignore */ }
      try { if (typeof vm.emitChange === 'function') vm.emitChange(v); } catch (_) { /* ignore */ }
      try {
        if (vm.vnode && vm.vnode.props) {
          if (typeof vm.vnode.props.onUpdate === 'function') vm.vnode.props.onUpdate(v);
          if (typeof vm.vnode.props['onUpdate:modelValue'] === 'function') vm.vnode.props['onUpdate:modelValue'](v);
          if (typeof vm.vnode.props.onChange === 'function') vm.vnode.props.onChange(v);
        }
      } catch (_) { /* ignore */ }
    }
  }

  function emitReactDate(el, payloads) {
    if (!el) return;
    var key;
    for (key in el) {
      if (!Object.prototype.hasOwnProperty.call(el, key)) continue;
      if (key.indexOf('__reactProps$') !== 0 && key.indexOf('__reactEventHandlers$') !== 0) continue;
      var props = el[key];
      if (!props) continue;
      payloads.forEach(function (v) {
        var str = v instanceof Date
          ? (v.getFullYear() + '-' + ('0' + (v.getMonth() + 1)).slice(-2) + '-' + ('0' + v.getDate()).slice(-2))
          : String(v);
        var ev = { target: { value: str }, currentTarget: el };
        try {
          if (typeof props.onChange === 'function') props.onChange(v instanceof Date ? v : parseDate(str), str);
        } catch (_) { /* ignore */ }
        try { if (typeof props.onBlur === 'function') props.onBlur(ev); } catch (_) { /* ignore */ }
      });
    }
  }

  function shownDate(input) {
    var shown = input ? String(input.value || '').trim() : '';
    return !!(shown && shown !== '请选择' && shown !== '请输入');
  }

  async function fillDatePicker(item, value) {
    var variants = dateVariants(value);
    var payloads = datePayloads(value);
    if (!variants.length) return false;
    var wrap = item.querySelector('.el-date-editor, .ant-picker, .el-picker') || item;
    var inputs = wrap.querySelectorAll ? wrap.querySelectorAll('input') : [];
    var input = (inputs && inputs[0]) || nativeInput(item);
    var vm = walkVue(wrap) || walkVue(input);
    emitVueDate(vm, payloads);
    if (vm && vm.$parent) emitVueDate(vm.$parent, payloads);
    if (vm && vm.$parent && vm.$parent.$parent) emitVueDate(vm.$parent.$parent, payloads);
    emitReactDate(input, payloads);
    emitReactDate(wrap, payloads);
    var i;
    for (i = 0; i < variants.length; i++) {
      if (input) setInput(input, variants[i]);
      if (inputs && inputs.length > 1) setInput(inputs[1], variants[i]);
    }
    if (shownDate(input)) return true;
    if (input) {
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true }));
      input.dispatchEvent(new Event('blur', { bubbles: true }));
    }
    return shownDate(input);
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

  async function fillItem(entry, section, profile, fmap, groups, counters) {
    var label = entry.label;
    var item = entry.item;
    var slotHint = fmap.resolveSlot(label, { isTextarea: /描述|内容|评价|介绍/.test(label) });
    var idx = 0;
    var hit = String(slotHint || '').match(/^(application\.(?:projects|internships|campus_practices|campus_roles|award_records|certificate_records|languages))/);
    if (hit) {
      idx = counters[slotHint] || 0;
      counters[slotHint] = idx + 1;
    }
    var picked = pickValue(label, section, profile, fmap, idx);
    var value = picked.value;
    var slot = picked.slot || '';
    if (!slot) return { ok: false, reason: 'unmapped', slot: '', value: '' };
    var policy = root.CareerOsFillPolicy;
    if (policy && groups && !policy.allowed(slot, groups)) {
      return { ok: false, reason: 'policy_skip', slot: slot, value: '' };
    }
    if (!value) return { ok: false, reason: 'empty', slot: slot, value: '' };
    if (slot.indexOf('id_card') !== -1 && !fmap.isRealIdCard(value)) {
      return { ok: false, reason: 'skip_id', slot: slot, value: '' };
    }

    var input = nativeInput(item);
    var shown = input ? String(input.value || '').trim() : '';
    if (shown && shown !== '请选择' && shown !== '请输入') {
      return { ok: true, reason: 'already', slot: slot, value: value };
    }
    var hasSelect = item.querySelector('.el-select, .el-cascader, .ant-select, .rc-select');
    var ok = false;
    var how = 'input';
    if (/性别|婚姻/.test(label)) {
      ok = fillRadioLike(item, value) || fillRadioLike(item.parentElement, value);
      how = 'radio';
    }
    if (!ok && input && !input.readOnly) {
      ok = setInput(input, value);
      how = 'input';
    }
    if (!ok && isDateField(label, item)) {
      ok = await fillDatePicker(item, value);
      how = 'date';
    }
    if (!ok && hasSelect) {
      ok = await fillDropdown(item, value);
      how = 'dropdown';
    }
    if (!ok && input) {
      ok = setInput(input, value);
      how = 'input';
    }
    return { ok: ok, reason: ok ? how : 'no_match', slot: slot, value: value };
  }

  async function fill(profile, opts) {
    var fmap = root.CareerOsFieldMap;
    var events = [];
    if (!fmap || !profile) return { count: 0, events: events };
    var groups = opts && opts.fillGroups;
    var counters = {};
    var items = collectItems();
    var section = 'personal';
    var count = 0;
    for (var i = 0; i < items.length; i++) {
      var entry = items[i];
      section = detectSection(entry.label, section);
      try {
        var result = await fillItem(entry, section, profile, fmap, groups, counters);
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

  root.CareerOsBeisenFill = {
    fill: fill,
    collectItems: collectItems,
    fillDropdown: fillDropdown,
    fillDatePicker: fillDatePicker,
    parseDate: parseDate,
    optionCandidates: optionCandidates,
    dateVariants: dateVariants,
    detectSection: detectSection
  };
})(typeof self !== 'undefined' ? self : this);
