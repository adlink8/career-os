/**
 * 可改快捷键。存在 chrome.storage.local.careerOsShortcuts。
 */
(function (root) {
  'use strict';

  var DEFAULTS = {
    fill: { alt: true, shift: true, ctrl: false, key: 'f', label: '一键填充' },
    blank: { alt: true, shift: true, ctrl: false, key: 'b', label: '仅填空白' },
    focused: { alt: true, shift: true, ctrl: false, key: 'Enter', label: '填入当前格子' },
    copy: { alt: true, shift: true, ctrl: false, key: 'c', label: '复制当前格子' },
    capture: { alt: true, shift: true, ctrl: false, key: 'j', label: '捕获 JD+表单' }
  };

  function cloneDefaults() {
    var out = {};
    Object.keys(DEFAULTS).forEach(function (k) {
      out[k] = Object.assign({}, DEFAULTS[k]);
    });
    return out;
  }

  function format(s) {
    if (!s) return '';
    var parts = [];
    if (s.ctrl) parts.push('Ctrl');
    if (s.alt) parts.push('Alt');
    if (s.shift) parts.push('Shift');
    var key = String(s.key || '');
    if (key === ' ') key = 'Space';
    parts.push(key.length === 1 ? key.toUpperCase() : key);
    return parts.join('+');
  }

  function fromEvent(e) {
    var key = e.key;
    if (!key) return null;
    if (key === 'Control' || key === 'Alt' || key === 'Shift' || key === 'Meta') return null;
    return {
      alt: !!e.altKey,
      shift: !!e.shiftKey,
      ctrl: !!e.ctrlKey,
      key: key.length === 1 ? key.toLowerCase() : key
    };
  }

  function match(e, s) {
    if (!s || !s.key) return false;
    var key = e.key;
    var want = String(s.key);
    if (want.length === 1) {
      if (String(key).toLowerCase() !== want.toLowerCase()) return false;
    } else if (key !== want) {
      return false;
    }
    return !!e.altKey === !!s.alt && !!e.shiftKey === !!s.shift && !!e.ctrlKey === !!s.ctrl;
  }

  function load() {
    return new Promise(function (resolve) {
      chrome.storage.local.get({ careerOsShortcuts: null }, function (stored) {
        var merged = cloneDefaults();
        var raw = stored.careerOsShortcuts || {};
        Object.keys(merged).forEach(function (k) {
          if (raw[k] && raw[k].key) merged[k] = Object.assign({}, merged[k], raw[k]);
        });
        resolve(merged);
      });
    });
  }

  function save(map) {
    return new Promise(function (resolve) {
      chrome.storage.local.set({ careerOsShortcuts: map }, function () { resolve(true); });
    });
  }

  root.CareerOsShortcuts = {
    DEFAULTS: DEFAULTS,
    cloneDefaults: cloneDefaults,
    format: format,
    fromEvent: fromEvent,
    match: match,
    load: load,
    save: save
  };
})(typeof self !== 'undefined' ? self : this);
