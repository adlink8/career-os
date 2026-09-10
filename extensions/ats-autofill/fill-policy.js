/**
 * 一键填充范围：设置页多选。勾选的类别才写入；格子旁「填入」不走这份策略。
 */
(function (root) {
  'use strict';

  var KEY = 'overlayFillGroups';

  var GROUPS = [
    { id: 'personal', label: '个人信息' },
    { id: 'education', label: '教育经历' },
    { id: 'intent', label: '求职意向' },
    { id: 'intern', label: '实习经历' },
    { id: 'projects', label: '项目经历' },
    { id: 'campus', label: '职务 / 实践' },
    { id: 'award', label: '获奖 / 证书 / 外语' },
    { id: 'eval', label: '自我评价 / 技能' },
    { id: 'open', label: '开放题' }
  ];

  function defaults() {
    var out = {};
    GROUPS.forEach(function (g) { out[g.id] = true; });
    return out;
  }

  function normalize(map) {
    var out = defaults();
    if (!map || typeof map !== 'object') return out;
    GROUPS.forEach(function (g) {
      if (Object.prototype.hasOwnProperty.call(map, g.id)) out[g.id] = !!map[g.id];
    });
    return out;
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

  function allowed(slot, groups) {
    var g = groupForSlot(slot);
    if (!g) return true;
    return !!normalize(groups)[g];
  }

  function selectedIds(groups) {
    var map = normalize(groups);
    return GROUPS.filter(function (g) { return map[g.id]; }).map(function (g) { return g.id; });
  }

  function load() {
    return new Promise(function (resolve) {
      if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
        resolve(defaults());
        return;
      }
      chrome.storage.local.get({ overlayFillGroups: null }, function (stored) {
        resolve(normalize(stored.overlayFillGroups));
      });
    });
  }

  function save(map) {
    var normalized = normalize(map);
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
    defaults: defaults,
    normalize: normalize,
    groupForSlot: groupForSlot,
    allowed: allowed,
    selectedIds: selectedIds,
    load: load,
    save: save
  };
})(typeof self !== 'undefined' ? self : this);
