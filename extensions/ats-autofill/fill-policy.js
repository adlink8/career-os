/**
 * 一键填充范围：按内容库模块标题勾选。格子旁「填入」不走这份策略。
 */
(function (root) {
  'use strict';

  var KEY = 'overlayFillGroups';

  var GROUPS = [];

  function groupsFrom(notebook) {
    var out = [];
    ((notebook && notebook.modules) || []).forEach(function (m) {
      if (!m) return;
      var title = String(m.title || '').trim();
      if (!title) return;
      out.push({ id: m.id || title, label: title });
    });
    return out;
  }

  function defaults(notebook) {
    var out = {};
    groupsFrom(notebook).forEach(function (g) { out[g.id] = true; });
    return out;
  }

  function normalize(map, notebook) {
    var out = defaults(notebook);
    if (!map || typeof map !== 'object') return out;
    Object.keys(out).forEach(function (id) {
      if (Object.prototype.hasOwnProperty.call(map, id)) out[id] = !!map[id];
    });
    return out;
  }

  function normalizeLabel(label) {
    var overlay = root.CareerOsOverlay;
    if (overlay && overlay.normalizeLabel) return overlay.normalizeLabel(label);
    return String(label || '').replace(/\s+/g, ' ').trim();
  }

  function moduleIdsForLabel(label, notebook) {
    var want = normalizeLabel(label);
    var ids = [];
    ((notebook && notebook.modules) || []).forEach(function (m) {
      var has = (m.items || []).some(function (item) {
        return (item.fields || []).some(function (f) {
          return normalizeLabel(f && f.label) === want;
        });
      });
      if (has) ids.push(m.id || m.title);
    });
    return ids;
  }

  function groupForSlot(slot) {
    var s = String(slot || '');
    if (!s) return '';
    if (s.indexOf('open.') === 0) return 'open';
    if (/available_time|internship_duration|days_per_week/.test(s)) return 'intent';
    if (s.indexOf('universal.personal.') === 0) return 'personal';
    if (s.indexOf('universal.education.') === 0) return 'education';
    if (
      s === 'application.target_position' ||
      s === 'application.target_cities' ||
      s.indexOf('application.expected_') === 0
    ) return 'intent';
    if (s.indexOf('application.family_members') === 0) return 'personal';
    if (s.indexOf('application.training_records') === 0) return 'intern';
    if (s.indexOf('application.internships') === 0) return 'intern';
    if (s.indexOf('application.projects') === 0) return 'projects';
    if (s.indexOf('application.campus_') === 0) return 'campus';
    if (
      s.indexOf('application.award_') === 0 ||
      s.indexOf('application.certificate_') === 0 ||
      s.indexOf('application.languages') === 0 ||
      s === 'universal.languages' ||
      s === 'universal.awards' ||
      s === 'universal.certificates'
    ) return 'award';
    if (
      s.indexOf('application.self_evaluation') === 0 ||
      s.indexOf('application.skills_') === 0 ||
      s === 'universal.hobbies'
    ) return 'eval';
    return '';
  }

  function allowed(label, groups, notebook, moduleTitle) {
    if (notebook && Array.isArray(notebook.modules) && notebook.modules.length) {
      var map = normalize(groups, notebook);
      if (moduleTitle) {
        var mod = null;
        notebook.modules.forEach(function (m) {
          if (m && m.title === moduleTitle) mod = m;
        });
        if (!mod) return true;
        return !!map[mod.id || mod.title];
      }
      var ids = moduleIdsForLabel(label, notebook);
      if (!ids.length) return true;
      return ids.some(function (id) { return !!map[id]; });
    }
    var g = groupForSlot(label);
    if (!g) return true;
    if (!groups || typeof groups !== 'object') return true;
    if (Object.prototype.hasOwnProperty.call(groups, g)) return !!groups[g];
    return true;
  }

  function selectedIds(groups, notebook) {
    var list = groupsFrom(notebook);
    if (!list.length) {
      return Object.keys(groups || {}).filter(function (k) { return groups[k]; });
    }
    var map = normalize(groups, notebook);
    return list.filter(function (g) { return map[g.id]; }).map(function (g) { return g.id; });
  }

  function load() {
    return new Promise(function (resolve) {
      if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
        resolve({});
        return;
      }
      chrome.storage.local.get({ overlayFillGroups: null }, function (stored) {
        resolve(stored.overlayFillGroups && typeof stored.overlayFillGroups === 'object'
          ? stored.overlayFillGroups
          : {});
      });
    });
  }

  function save(map) {
    var normalized = map && typeof map === 'object' ? map : {};
    return new Promise(function (resolve) {
      if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
        resolve(normalized);
        return;
      }
      chrome.storage.local.set({ overlayFillGroups: normalized }, function () {
        resolve(normalized);
      });
    });
  }

  root.CareerOsFillPolicy = {
    KEY: KEY,
    GROUPS: GROUPS,
    groupsFrom: groupsFrom,
    defaults: defaults,
    normalize: normalize,
    groupForSlot: groupForSlot,
    allowed: allowed,
    selectedIds: selectedIds,
    load: load,
    save: save
  };
})(typeof self !== 'undefined' ? self : this);
