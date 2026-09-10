/**
 * 设置页画像：开关打开用这份填北森/Moka；关闭则走本地 JSON / apply-run。
 */
(function (root) {
  'use strict';

  var KEY_ENABLED = 'overlayEnabled';
  var KEY_PROFILE = 'overlayProfile';

  function emptyRow() {
    return {
      name: '',
      role: '',
      keywords: '',
      start_date: '',
      end_date: '',
      duty: '',
      description: '',
      full_text: '',
      achievement: '',
      date: '',
      level: '',
      type: '',
      listen: '',
      speak: '',
      read: ''
    };
  }

  function emptyProfile() {
    return {
      version: '3.0-overlay',
      source: 'settings-overlay',
      universal: {
        personal: {
          name: '',
          gender: '',
          birth_date: '',
          age: '',
          phone: '',
          email: '',
          id_card: '',
          current_city: '',
          current_address: '',
          native_place: '',
          political_status: '',
          marriage: '',
          ethnicity: '',
          health: '',
          emergency_contact: '',
          emergency_phone: '',
          emergency_relation: '',
          available_time: '',
          internship_duration: '',
          days_per_week: ''
        },
        education: {
          records: [],
          undergraduate: {
            school: '',
            college: '',
            degree: '',
            major: '',
            graduation: '',
            start_date: '',
            end_date: '',
            education_type: '',
            gpa: '',
            rank: ''
          },
          junior_college: {
            school: '',
            degree: '',
            major: '',
            start_date: '',
            end_date: '',
            graduation: '',
            education_type: '',
            college: '',
            gpa: '',
            rank: ''
          }
        },
        hobbies: '',
        awards: '',
        certificates: '',
        languages: ''
      },
      application: {
        target_position: '',
        target_cities: '',
        expected_city: '',
        expected_salary: '',
        self_evaluation: '',
        skills_summary: '',
        skills_proficient: '',
        skills_familiar: '',
        internships: [],
        projects: [],
        campus_practices: [],
        campus_roles: [],
        award_records: [],
        certificate_records: [],
        languages: [],
        family_members: [],
        training_records: []
      }
    };
  }

  var LIST_PATHS = [
    'universal.education.records',
    'application.internships',
    'application.projects',
    'application.campus_practices',
    'application.campus_roles',
    'application.award_records',
    'application.certificate_records',
    'application.languages',
    'application.family_members',
    'application.training_records'
  ];

  function rowHasValue(row) {
    if (!row || typeof row !== 'object') return false;
    return Object.keys(row).some(function (k) {
      return String(row[k] == null ? '' : row[k]).trim() !== '';
    });
  }

  function compactList(arr) {
    return (Array.isArray(arr) ? arr : []).filter(rowHasValue);
  }

  function educationRows(profile) {
    var edu = getByPath(profile, 'universal.education') || {};
    if (Array.isArray(edu.records) && edu.records.some(rowHasValue)) {
      return compactList(edu.records);
    }
    var rows = [];
    if (rowHasValue(edu.undergraduate)) rows.push(edu.undergraduate);
    if (rowHasValue(edu.junior_college)) rows.push(edu.junior_college);
    return rows;
  }

  function emptyEduRow() {
    return {
      school: '',
      college: '',
      degree: '',
      major: '',
      graduation: '',
      start_date: '',
      end_date: '',
      education_type: '',
      gpa: '',
      rank: ''
    };
  }

  function syncEducationAliases(profile) {
    if (!profile || typeof profile !== 'object') return profile;
    if (!profile.universal || typeof profile.universal !== 'object') profile.universal = {};
    if (!profile.universal.education || typeof profile.universal.education !== 'object') {
      profile.universal.education = {};
    }
    var rows = educationRows(profile);
    profile.universal.education.records = rows;
    var blank = emptyEduRow();
    profile.universal.education.undergraduate = rows[0] ? Object.assign(emptyEduRow(), rows[0]) : blank;
    profile.universal.education.junior_college = rows[1]
      ? Object.assign(emptyEduRow(), rows[1])
      : emptyEduRow();
    return profile;
  }

  function compactProfile(profile) {
    if (!profile || typeof profile !== 'object') return profile;
    syncEducationAliases(profile);
    LIST_PATHS.forEach(function (path) {
      var arr = getByPath(profile, path);
      if (Array.isArray(arr)) setByPath(profile, path, compactList(arr));
    });
    syncEducationAliases(profile);
    return profile;
  }

  function ensureArray(obj, path, minLen) {
    var cur = obj;
    var parts = path.split('.');
    for (var i = 0; i < parts.length; i++) {
      var key = parts[i];
      if (i === parts.length - 1) {
        if (!Array.isArray(cur[key])) cur[key] = [];
        while (cur[key].length < minLen) cur[key].push(emptyRow());
        return cur[key];
      }
      if (!cur[key] || typeof cur[key] !== 'object') cur[key] = {};
      cur = cur[key];
    }
    return [];
  }

  function getByPath(obj, path) {
    return path.split('.').reduce(function (acc, key) {
      return acc == null ? undefined : acc[key];
    }, obj);
  }

  function setByPath(obj, path, value) {
    var parts = path.split('.');
    var cur = obj;
    for (var i = 0; i < parts.length - 1; i++) {
      var key = parts[i];
      var next = parts[i + 1];
      if (/^\d+$/.test(next)) {
        if (!Array.isArray(cur[key])) cur[key] = [];
        var idx = parseInt(next, 10);
        while (cur[key].length <= idx) cur[key].push(emptyRow());
        cur = cur[key];
      } else {
        if (!cur[key] || typeof cur[key] !== 'object' || Array.isArray(cur[key])) {
          if (!/^\d+$/.test(key)) cur[key] = cur[key] && typeof cur[key] === 'object' ? cur[key] : {};
        }
        if (/^\d+$/.test(key)) {
          cur = cur[parseInt(key, 10)];
        } else {
          if (!cur[key] || typeof cur[key] !== 'object') cur[key] = {};
          cur = cur[key];
        }
      }
    }
    var last = parts[parts.length - 1];
    if (/^\d+$/.test(last) && Array.isArray(cur)) {
      cur[parseInt(last, 10)] = value;
    } else {
      cur[last] = value;
    }
  }

  var LIST_PREFIX = {
    'universal.education.records': true,
    'application.projects': true,
    'application.internships': true,
    'application.campus_practices': true,
    'application.campus_roles': true,
    'application.award_records': true,
    'application.certificate_records': true,
    'application.languages': true,
    'application.family_members': true,
    'application.training_records': true
  };

  function applySlot(profile, slot, value, listIndex) {
    if (!slot || value == null || String(value).trim() === '') return;
    var idx = listIndex || 0;
    var listHit = slot.match(/^(universal\.education\.records|application\.(?:projects|internships|campus_practices|campus_roles|award_records|certificate_records|languages|family_members|training_records))\.(.+)$/);
    if (listHit) {
      var arr = ensureArray(profile, listHit[1], idx + 1);
      if (!arr[idx] || typeof arr[idx] !== 'object') arr[idx] = emptyRow();
      arr[idx][listHit[2]] = String(value).trim();
      return;
    }
    setByPath(profile, slot, String(value).trim());
  }

  function loadState() {
    return new Promise(function (resolve) {
      chrome.storage.local.get(
        { overlayEnabled: false, overlayProfile: null },
        function (stored) {
          resolve({
            enabled: !!stored.overlayEnabled,
            profile: stored.overlayProfile && typeof stored.overlayProfile === 'object'
              ? stored.overlayProfile
              : emptyProfile()
          });
        }
      );
    });
  }

  function saveState(enabled, profile) {
    return new Promise(function (resolve) {
      chrome.storage.local.set(
        {
          overlayEnabled: !!enabled,
          overlayProfile: compactProfile(profile || emptyProfile())
        },
        function () { resolve(true); }
      );
    });
  }

  function isProfile(obj) {
    return !!(obj && typeof obj === 'object' && obj.universal && obj.application);
  }

  function normalizeImport(raw) {
    if (typeof raw === 'string') {
      raw = JSON.parse(raw);
    }
    if (!raw || typeof raw !== 'object') {
      throw new Error('不是 JSON 对象');
    }
    if (isProfile(raw)) return raw;
    if (isProfile(raw.profile)) return raw.profile;
    if (isProfile(raw.overlayProfile)) return raw.overlayProfile;
    if (isProfile(raw.data)) return raw.data;
    var fields = raw.fields || (raw.autofill && raw.autofill.fields);
    if (Array.isArray(fields)) {
      var profile = emptyProfile();
      var counts = {};
      fields.forEach(function (item) {
        if (!item || !item.slot) return;
        var value = item.value;
        if (value == null || String(value).trim() === '') return;
        var n = counts[item.slot] || 0;
        applySlot(profile, item.slot, value, n);
        counts[item.slot] = n + 1;
      });
      if (raw.target_position) {
        setByPath(profile, 'application.target_position', raw.target_position);
      }
      return profile;
    }
    throw new Error('无法识别该 JSON。需要 universal+application，或 fields[].slot/value');
  }

  function buildAiPrompt() {
    var schema = JSON.stringify(emptyProfile(), null, 2);
    return [
      '你是网申填表 JSON 生成器。只输出一个 JSON 对象，不要用 Markdown 代码围栏，不要解释，不要注释。',
      '',
      '结构必须严格符合下面模板：字段名一字不改；缺的用空字符串 "" 或保留空对象/数组；不要新增字段。',
      '',
      schema,
      '',
      '规则：',
      '1. version 固定为 "3.0-overlay"；source 固定为 "settings-overlay"。',
      '2. application.target_position 必须是单一岗位官网全称，禁止「A与B」「A/B」复合意向。',
      '3. 日期只用 YYYY-MM 或 YYYY-MM-DD。',
      '4. internships / projects / education.records 每条至少有 name 或 school；项目描述写在 full_text，实习内容写在 duty。教育经历本科在前、专科在后，有几段写几段。',
      '5. 禁止编造量化业绩、假手机号、假邮箱、假身份证；用户没给的字段留空。',
      '6. 技能写真实会的，不要堆用户材料里没有的技术词。',
      '',
      '用户材料（简历或个人信息，原样保留事实）：',
      '',
      '（在这里粘贴简历或口述材料）'
    ].join('\n');
  }

  root.CareerOsOverlay = {
    KEY_ENABLED: KEY_ENABLED,
    KEY_PROFILE: KEY_PROFILE,
    LIST_PATHS: LIST_PATHS,
    emptyProfile: emptyProfile,
    emptyRow: emptyRow,
    getByPath: getByPath,
    setByPath: setByPath,
    applySlot: applySlot,
    ensureArray: ensureArray,
    rowHasValue: rowHasValue,
    compactList: compactList,
    compactProfile: compactProfile,
    educationRows: educationRows,
    syncEducationAliases: syncEducationAliases,
    loadState: loadState,
    saveState: saveState,
    normalizeImport: normalizeImport,
    buildAiPrompt: buildAiPrompt,
    LIST_PREFIX: LIST_PREFIX
  };
})(typeof self !== 'undefined' ? self : this);
