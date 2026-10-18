/**
 * 表单格子按字段名取值。旧槽位只给迁入 / lookupSlot 用。
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

  function valueByLabel(label, notebook, index) {
    var overlay = root.CareerOsOverlay;
    if (overlay && overlay.valueByLabel) return overlay.valueByLabel(notebook, label, index);
    var want = overlay && overlay.normalizeLabel
      ? overlay.normalizeLabel(label)
      : String(label || '').replace(/\s+/g, ' ').trim();
    if (!want || !notebook || !Array.isArray(notebook.modules)) return '';
    var hits = [];
    notebook.modules.forEach(function (mod) {
      (mod && Array.isArray(mod.items) ? mod.items : []).forEach(function (item) {
        (item && Array.isArray(item.fields) ? item.fields : []).forEach(function (field) {
          var lab = overlay && overlay.normalizeLabel
            ? overlay.normalizeLabel(field && field.label)
            : String(field && field.label || '').replace(/\s+/g, ' ').trim();
          if (lab === want) hits.push(field.value == null ? '' : String(field.value));
        });
      });
    });
    var raw = hits[index || 0];
    return raw == null ? '' : String(raw).trim();
  }

  function valueForSlot(slot, profile, projectIndex) {
    var overlay = root.CareerOsOverlay;
    if (!slot || !profile || !overlay) return '';
    var nb = profile;
    if (!overlay.isNotebook(profile) && overlay.normalizeImport) {
      try { nb = overlay.normalizeImport(profile); } catch (_) { nb = profile; }
    }
    var info = overlay.lookupSlot && overlay.lookupSlot(slot);
    var label = info && info.label ? info.label : slot;
    return valueByLabel(label, nb, projectIndex || 0);
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
    valueByLabel: valueByLabel,
    valueForSlot: valueForSlot,
    isRealIdCard: isRealIdCard,
    isNoiseLabel: isNoiseLabel,
    matchAutofillValue: matchAutofillValue,
    educationRecords: educationRecords
  };
})(typeof self !== 'undefined' ? self : this);
