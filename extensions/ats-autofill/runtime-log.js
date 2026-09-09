/**
 * 运行日志：控制台 + 发给 background 落盘。
 * 手机/邮箱/身份证只记脱敏预览。
 */
(function (root) {
  'use strict';

  function preview(val, slot) {
    var s = String(val == null ? '' : val);
    var key = String(slot || '');
    if (/phone|email|id_card|emergency/i.test(key)) {
      if (!s) return '';
      return s.slice(0, 3) + '***';
    }
    return s.length > 60 ? s.slice(0, 60) + '…' : s;
  }

  function send(event) {
    if (!event || typeof event !== 'object') return;
    event.ts = event.ts || new Date().toISOString();
    try {
      console.log('[Career OS]', event.op || 'log', event);
    } catch (_) { /* ignore */ }
    try {
      var inSw = typeof window === 'undefined';
      if (!inSw && chrome && chrome.runtime && chrome.runtime.sendMessage) {
        chrome.runtime.sendMessage({ action: 'APPEND_LOG', event: event });
      }
    } catch (_) { /* ignore */ }
  }

  root.CareerOsLog = { preview: preview, send: send };
})(typeof self !== 'undefined' ? self : this);
