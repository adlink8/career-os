/**
 * 表单格子 → 画像槽位。捕获和填表共用，避免再按岗位轨道分支。
 */
(function (root) {
  'use strict';

  function pick(obj, path) {
    return path.split('.').reduce(function (acc, key) {
      return acc == null ? undefined : acc[key];
    }, obj);
  }

  var RULES = [];

  function setRules(list) {
    RULES = [];
    (list || []).forEach(function (r) {
      if (!r || !r.slot || !r.re) return;
      try {
        RULES.push({
          slot: r.slot,
          textarea: r.textarea,
          re: new RegExp(r.re, r.flags || '')
        });
      } catch (_) { /* skip bad rule */ }
    });
    return RULES.length;
  }

  function resolveSlot(ctx, meta) {
    var text = String(ctx || '')
      .replace(/请输入\d*位?/g, ' ')
      .replace(/请输入/g, ' ')
      .replace(/请选择/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
    if (/民族/.test(text) && /大学|学院/.test(text)) {
      return '';
    }
    var isTextarea = !!(meta && meta.isTextarea);
    for (var i = 0; i < RULES.length; i++) {
      var rule = RULES[i];
      if (rule.textarea === true && !isTextarea) continue;
      if (rule.textarea === false && isTextarea) continue;
      if (rule.re.test(text)) return rule.slot;
    }
    return '';
  }

  function projectValue(profile, key, index) {
    var list = pick(profile, 'application.projects') || [];
    var item = list[index] || list[0] || {};
    return item[key] || '';
  }

  function valueForSlot(slot, profile, projectIndex) {
    if (!slot || !profile) return '';
    var listHit = slot.match(/^(application\.(?:projects|internships|campus_practices|campus_roles|award_records|certificate_records|languages))\.(.+)$/);
    if (listHit) {
      var item = (pick(profile, listHit[1]) || [])[projectIndex || 0] || {};
      var raw = item[listHit[2]];
      if (raw == null || raw === '') {
        if (listHit[1] === 'application.award_records' && listHit[2] === 'name') {
          raw = pick(profile, 'universal.awards');
        }
        if (listHit[1] === 'application.certificate_records' && listHit[2] === 'name') {
          raw = pick(profile, 'universal.certificates');
        }
      }
      return raw == null ? '' : String(raw).trim();
    }
    if (slot === 'application.expected_city') {
      var city = pick(profile, 'application.expected_city');
      if (city) return String(city).trim();
      var cities = pick(profile, 'application.target_cities') || '';
      return String(cities).split(/[、,，]/)[0].trim();
    }
    var val = pick(profile, slot);
    if (val == null) return '';
    return String(val).trim();
  }

  function isRealIdCard(value) {
    return /^\d{17}[\dXx]$/.test(String(value || '').trim());
  }

  root.CareerOsFieldMap = {
    setRules: setRules,
    resolveSlot: resolveSlot,
    valueForSlot: valueForSlot,
    isRealIdCard: isRealIdCard
  };
})(typeof self !== 'undefined' ? self : this);
