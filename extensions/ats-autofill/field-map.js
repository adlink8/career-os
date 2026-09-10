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

  function rowHasValue(row) {
    if (!row || typeof row !== 'object') return false;
    return Object.keys(row).some(function (k) {
      return String(row[k] == null ? '' : row[k]).trim() !== '';
    });
  }

  function educationRecords(profile) {
    var edu = pick(profile, 'universal.education') || {};
    if (Array.isArray(edu.records) && edu.records.some(rowHasValue)) {
      return edu.records.filter(rowHasValue);
    }
    var out = [];
    if (rowHasValue(edu.undergraduate)) out.push(edu.undergraduate);
    if (rowHasValue(edu.junior_college)) out.push(edu.junior_college);
    return out;
  }

  function valueForSlot(slot, profile, projectIndex) {
    if (!slot || !profile) return '';
    var eduHit = String(slot).match(/^universal\.education\.(?:records|undergraduate|junior_college)\.(.+)$/);
    if (eduHit) {
      var recs = educationRecords(profile);
      var eduItem = recs[projectIndex || 0] || {};
      var eduKey = eduHit[1];
      var eduRaw = eduItem[eduKey];
      if ((eduRaw == null || eduRaw === '') && eduKey === 'graduation') eduRaw = eduItem.end_date;
      if ((eduRaw == null || eduRaw === '') && eduKey === 'end_date') eduRaw = eduItem.graduation;
      return eduRaw == null ? '' : String(eduRaw).trim();
    }
    var listHit = slot.match(/^(application\.(?:projects|internships|campus_practices|campus_roles|award_records|certificate_records|languages|family_members|training_records))\.(.+)$/);
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

  function isNoiseLabel(label) {
    var raw = String(label || '').replace(/\s+/g, ' ').trim();
    return /^(请选择|请输入|请填写|\+86|\+86 \+86|moka-version|验证码|captcha)$/i.test(raw);
  }

  function matchAutofillValue(field, autofill) {
    if (!field || !autofill) return '';
    var rows = autofill.fields || [];
    var label = String(field.label || '').replace(/\s+/g, ' ').trim();
    var i;
    for (i = 0; i < rows.length; i++) {
      if (String(rows[i].label || '').replace(/\s+/g, ' ').trim() === label && rows[i].value) {
        return String(rows[i].value);
      }
    }
    if (field.slot) {
      for (i = 0; i < rows.length; i++) {
        if (rows[i].slot === field.slot && rows[i].value) return String(rows[i].value);
      }
    }
    var answers = autofill.open_answers || [];
    for (i = 0; i < answers.length; i++) {
      var a = answers[i];
      if (a && a.value && a.label && String(a.label).replace(/\s+/g, ' ').trim() === label) {
        return String(a.value);
      }
    }
    return '';
  }

  root.CareerOsFieldMap = {
    setRules: setRules,
    resolveSlot: resolveSlot,
    valueForSlot: valueForSlot,
    isRealIdCard: isRealIdCard,
    isNoiseLabel: isNoiseLabel,
    matchAutofillValue: matchAutofillValue,
    educationRecords: educationRecords
  };
})(typeof self !== 'undefined' ? self : this);
