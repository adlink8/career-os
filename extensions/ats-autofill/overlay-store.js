/**
 * 设置页画像：开关打开用这份填北森/Moka；关闭则走本地 JSON / apply-run。
 */
(function (root) {
  'use strict';

  var KEY_ENABLED = 'overlayEnabled';
  var KEY_PROFILE = 'overlayProfile';
  var KEY_NOTEBOOK = 'overlayNotebook';
  var KEY_SHAPES = 'overlayShapes';
  var NOTEBOOK_VERSION = '4.0-notebook';

  function emptyNotebook() {
    return {
      version: NOTEBOOK_VERSION,
      modules: []
    };
  }

  function isNotebook(obj) {
    return !!(obj && typeof obj === 'object' && Array.isArray(obj.modules) && !obj.universal && !obj.application);
  }

  function newModuleId(nb) {
    var n = 1;
    var used = {};
    (nb && nb.modules ? nb.modules : []).forEach(function (m) {
      if (m && m.id) used[m.id] = true;
    });
    while (used['m' + n]) n += 1;
    return 'm' + n;
  }

  function findModule(nb, id) {
    if (!nb || !Array.isArray(nb.modules)) return null;
    var i;
    for (i = 0; i < nb.modules.length; i++) {
      if (nb.modules[i] && nb.modules[i].id === id) return nb.modules[i];
    }
    return null;
  }

  function emptyItem() {
    return { fields: [] };
  }

  function upsertModule(nb, spec) {
    if (!nb || typeof nb !== 'object') return null;
    if (!Array.isArray(nb.modules)) nb.modules = [];
    spec = spec || {};
    var id = spec.id;
    var found = id ? findModule(nb, id) : null;
    if (found) {
      if (spec.title != null) found.title = String(spec.title);
      return found;
    }
    var mod = {
      id: id || newModuleId(nb),
      title: spec.title != null ? String(spec.title) : '',
      items: Array.isArray(spec.items) ? spec.items : []
    };
    nb.modules.push(mod);
    return mod;
  }

  function addItem(nb, moduleId, item) {
    var mod = findModule(nb, moduleId);
    if (!mod) return null;
    if (!Array.isArray(mod.items)) mod.items = [];
    var row = item && typeof item === 'object' ? item : emptyItem();
    if (!Array.isArray(row.fields)) row.fields = [];
    mod.items.push(row);
    return row;
  }

  function setField(nb, moduleId, itemIndex, label, value) {
    var mod = findModule(nb, moduleId);
    if (!mod) return null;
    if (!Array.isArray(mod.items)) mod.items = [];
    while (mod.items.length <= itemIndex) mod.items.push(emptyItem());
    var item = mod.items[itemIndex];
    if (!item || typeof item !== 'object') {
      item = emptyItem();
      mod.items[itemIndex] = item;
    }
    if (!Array.isArray(item.fields)) item.fields = [];
    var want = normalizeLabel(label);
    var i;
    for (i = 0; i < item.fields.length; i++) {
      if (normalizeLabel(item.fields[i].label) === want) {
        item.fields[i].label = String(label == null ? '' : label).trim() || item.fields[i].label;
        item.fields[i].value = value == null ? '' : String(value);
        return item.fields[i];
      }
    }
    var field = { label: String(label == null ? '' : label).trim(), value: value == null ? '' : String(value) };
    item.fields.push(field);
    return field;
  }

  function normalizeLabel(label) {
    var t = String(label == null ? '' : label).replace(/\s+/g, ' ').trim();
    t = t.replace(/^请输入\d*位?/, '').replace(/^请选择/, '').replace(/^请填写/, '').replace(/^请输入/, '');
    return t.replace(/\s+/g, ' ').trim();
  }

  var STRONG_LABELS = {
    '学校名称': true,
    '项目名称': true,
    '单位名称': true,
    '姓名': true
  };

  function moduleFieldLabels(mod) {
    var out = [];
    ((mod && mod.items) || []).forEach(function (item) {
      ((item && item.fields) || []).forEach(function (f) {
        var lab = normalizeLabel(f && f.label);
        if (lab && out.indexOf(lab) === -1) out.push(lab);
      });
    });
    return out;
  }

  function resolveModuleTitle(notebook, pageSection, fieldLabels) {
    var page = String(pageSection || '').trim() || '未分组';
    var labels = (fieldLabels || []).map(normalizeLabel).filter(Boolean);
    var modules = notebook && Array.isArray(notebook.modules) ? notebook.modules : [];
    if (!modules.length) return page;
    var i;
    for (i = 0; i < modules.length; i++) {
      if (modules[i] && modules[i].title === page) return modules[i].title;
    }
    for (i = 0; i < modules.length; i++) {
      var title = modules[i] && modules[i].title;
      if (!title) continue;
      if (page.indexOf(title) !== -1 || title.indexOf(page) !== -1) return title;
    }
    for (i = 0; i < modules.length; i++) {
      var mod = modules[i];
      if (!mod || !mod.title) continue;
      var have = moduleFieldLabels(mod);
      var hit = [];
      labels.forEach(function (lab) {
        if (have.indexOf(lab) !== -1 && hit.indexOf(lab) === -1) hit.push(lab);
      });
      var strong = hit.some(function (lab) { return STRONG_LABELS[lab]; });
      if ((hit.length >= 1 && strong) || hit.length >= 2) return mod.title;
    }
    return page;
  }

  function valueByLabel(nb, label, index) {
    var want = normalizeLabel(label);
    if (!want || !nb || !Array.isArray(nb.modules)) return '';
    var hits = [];
    nb.modules.forEach(function (mod) {
      (mod && Array.isArray(mod.items) ? mod.items : []).forEach(function (item) {
        (item && Array.isArray(item.fields) ? item.fields : []).forEach(function (field) {
          if (normalizeLabel(field && field.label) === want) hits.push(field.value == null ? '' : String(field.value));
        });
      });
    });
    var idx = index || 0;
    var raw = hits[idx];
    return raw == null ? '' : String(raw).trim();
  }

  function itemHasValue(item) {
    if (!item || !Array.isArray(item.fields)) return false;
    return item.fields.some(function (f) {
      return String(f && f.value == null ? '' : f.value).trim() !== '';
    });
  }

  function compactNotebook(nb) {
    if (!nb || !Array.isArray(nb.modules)) return nb;
    nb.modules.forEach(function (mod) {
      if (!mod || !Array.isArray(mod.items)) return;
      mod.items = mod.items.filter(itemHasValue);
    });
    return nb;
  }

  function makePageKey(url) {
    try {
      var u = new URL(String(url || ''));
      return u.hostname + '|' + (u.pathname || '/') + '|' + (u.hash || '');
    } catch (_) {
      var s = String(url || '');
      var hash = '';
      var hashAt = s.indexOf('#');
      if (hashAt !== -1) {
        hash = s.slice(hashAt);
        s = s.slice(0, hashAt);
      }
      s = s.replace(/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//, '');
      var slash = s.indexOf('/');
      var host = slash === -1 ? s : s.slice(0, slash);
      var pathname = slash === -1 ? '/' : s.slice(slash);
      var q = pathname.indexOf('?');
      if (q !== -1) pathname = pathname.slice(0, q);
      host = (host.split('@').pop() || host).replace(/:\d+$/, '');
      return host + '|' + pathname + '|' + hash;
    }
  }

  function shapeFromFields(fields, notebook) {
    var groups = [];
    var indexByPage = {};
    (fields || []).forEach(function (f) {
      if (!f) return;
      var label = normalizeLabel(f.label);
      if (!label) return;
      var page = String(f.section || '').trim() || '未分组';
      var idx = indexByPage[page];
      if (idx == null) {
        idx = groups.length;
        indexByPage[page] = idx;
        groups.push({ page: page, fields: [] });
      }
      if (groups[idx].fields.indexOf(label) === -1) groups[idx].fields.push(label);
    });
    var modules = [];
    var indexByTitle = {};
    groups.forEach(function (g) {
      var title = resolveModuleTitle(notebook, g.page, g.fields);
      var idx = indexByTitle[title];
      if (idx == null) {
        idx = modules.length;
        indexByTitle[title] = idx;
        modules.push({ title: title, fields: [] });
      }
      g.fields.forEach(function (lab) {
        if (modules[idx].fields.indexOf(lab) === -1) modules[idx].fields.push(lab);
      });
    });
    return { modules: modules };
  }

  function hydrate(notebook, shape) {
    if (!notebook || typeof notebook !== 'object') notebook = emptyNotebook();
    if (!shape || !Array.isArray(shape.modules)) return notebook;
    shape.modules.forEach(function (modShape) {
      if (!modShape) return;
      var labels = Array.isArray(modShape.fields) ? modShape.fields : [];
      var title = resolveModuleTitle(notebook, String(modShape.title || '').trim() || '未分组', labels);
      var mod = null;
      (notebook.modules || []).forEach(function (m) {
        if (m && m.title === title) mod = m;
      });
      if (!mod) mod = upsertModule(notebook, { title: title });
      if (!Array.isArray(mod.items) || !mod.items.length) addItem(notebook, mod.id);
      mod.items.forEach(function (item, itemIndex) {
        labels.forEach(function (lab) {
          var want = normalizeLabel(lab);
          if (!want) return;
          var exists = (item.fields || []).some(function (f) {
            return normalizeLabel(f && f.label) === want;
          });
          if (!exists) setField(notebook, mod.id, itemIndex, lab, '');
        });
      });
    });
    return notebook;
  }

  function ingestPageFields(notebook, fields) {
    if (!notebook) notebook = emptyNotebook();
    var shape = shapeFromFields(fields, notebook);
    hydrate(notebook, shape);
    var labelsByPage = {};
    (fields || []).forEach(function (f) {
      if (!f || !f.label) return;
      var page = String(f.section || '').trim() || '未分组';
      if (!labelsByPage[page]) labelsByPage[page] = [];
      var lab = normalizeLabel(f.label);
      if (lab && labelsByPage[page].indexOf(lab) === -1) labelsByPage[page].push(lab);
    });
    var counts = {};
    (fields || []).forEach(function (f) {
      if (!f || !f.label) return;
      var val = f.value;
      if (val == null || String(val).trim() === '') return;
      var page = String(f.section || '').trim() || '未分组';
      var title = resolveModuleTitle(notebook, page, labelsByPage[page] || [f.label]);
      var key = title + '|' + normalizeLabel(f.label);
      var idx = counts[key] || 0;
      counts[key] = idx + 1;
      var mod = moduleByTitle(notebook, title);
      setField(notebook, mod.id, idx, f.label, val);
    });
    return { notebook: notebook, shape: shape };
  }

  function mergeNotebook(base, incoming) {
    if (!base) base = emptyNotebook();
    if (!incoming || !Array.isArray(incoming.modules)) return base;
    incoming.modules.forEach(function (inc) {
      if (!inc) return;
      var found = null;
      (base.modules || []).forEach(function (m) {
        if (m && m.title === inc.title) found = m;
      });
      if (!found) {
        var copy = {
          id: newModuleId(base),
          title: inc.title || '导入',
          items: typeof structuredClone === 'function'
            ? structuredClone(inc.items || [])
            : JSON.parse(JSON.stringify(inc.items || []))
        };
        base.modules.push(copy);
        return;
      }
      (inc.items || []).forEach(function (item, idx) {
        (item && item.fields || []).forEach(function (f) {
          if (!f || f.value == null || String(f.value).trim() === '') return;
          setField(base, found.id, idx, f.label, f.value);
        });
      });
    });
    return base;
  }

  function applySavedShape(notebook, shapes, pageKey) {
    var shape = shapes && pageKey ? shapes[pageKey] : null;
    if (!shape || !Array.isArray(shape.modules)) {
      return { ok: false, reason: '这页还没有骨架，先点自适应' };
    }
    hydrate(notebook, shape);
    return { ok: true, notebook: notebook };
  }

  function loadShapes() {
    return new Promise(function (resolve) {
      if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
        resolve({});
        return;
      }
      chrome.storage.local.get({ overlayShapes: {} }, function (stored) {
        var all = stored.overlayShapes;
        resolve(all && typeof all === 'object' ? all : {});
      });
    });
  }

  function saveShape(pageKey, shape) {
    return loadShapes().then(function (all) {
      all = all || {};
      if (pageKey) {
        all[pageKey] = {
          pageKey: pageKey,
          modules: (shape && shape.modules) || []
        };
      }
      return new Promise(function (resolve) {
        if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
          resolve(all);
          return;
        }
        chrome.storage.local.set({ overlayShapes: all }, function () { resolve(all); });
      });
    });
  }

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

  function getByPath(obj, path) {
    return path.split('.').reduce(function (acc, key) {
      return acc == null ? undefined : acc[key];
    }, obj);
  }

  var SCALAR_SLOTS = {
    'universal.personal.name': { module: '个人信息', label: '姓名' },
    'universal.personal.gender': { module: '个人信息', label: '性别' },
    'universal.personal.phone': { module: '个人信息', label: '手机号' },
    'universal.personal.email': { module: '个人信息', label: '邮箱' },
    'universal.personal.birth_date': { module: '个人信息', label: '出生日期' },
    'universal.personal.age': { module: '个人信息', label: '年龄' },
    'universal.personal.ethnicity': { module: '个人信息', label: '民族' },
    'universal.personal.political_status': { module: '个人信息', label: '政治面貌' },
    'universal.personal.native_place': { module: '个人信息', label: '籍贯' },
    'universal.personal.current_city': { module: '个人信息', label: '现居住地' },
    'universal.personal.marriage': { module: '个人信息', label: '婚姻' },
    'universal.personal.health': { module: '个人信息', label: '健康状况' },
    'universal.personal.id_card': { module: '个人信息', label: '身份证号' },
    'universal.personal.current_address': { module: '个人信息', label: '详细地址' },
    'universal.personal.emergency_contact': { module: '个人信息', label: '紧急联系人' },
    'universal.personal.emergency_phone': { module: '个人信息', label: '紧急电话' },
    'universal.personal.emergency_relation': { module: '个人信息', label: '与本人关系' },
    'universal.personal.available_time': { module: '求职意向', label: '到岗时间' },
    'universal.personal.internship_duration': { module: '求职意向', label: '实习周期' },
    'universal.personal.days_per_week': { module: '求职意向', label: '每周出勤天数' },
    'application.target_position': { module: '求职意向', label: '求职意向' },
    'application.expected_city': { module: '求职意向', label: '期望城市' },
    'application.target_cities': { module: '求职意向', label: '目标城市' },
    'application.expected_salary': { module: '求职意向', label: '期望薪资' },
    'application.self_evaluation': { module: '自我评价 / 技能', label: '自我评价' },
    'application.skills_summary': { module: '自我评价 / 技能', label: '专业技能' },
    'application.skills_proficient': { module: '自我评价 / 技能', label: '熟练技能' },
    'application.skills_familiar': { module: '自我评价 / 技能', label: '熟悉技能' },
    'universal.hobbies': { module: '自我评价 / 技能', label: '兴趣爱好' },
    'universal.awards': { module: '获奖', label: '获奖情况' },
    'universal.certificates': { module: '证书', label: '所持证书' },
    'universal.languages': { module: '外语', label: '外语能力总述' }
  };

  var LIST_SLOTS = {
    'universal.education.records': {
      module: '教育经历',
      fields: {
        school: '学校名称',
        college: '学院',
        major: '专业',
        degree: '学历',
        education_type: '学习形式',
        start_date: '入学时间',
        graduation: '毕业时间',
        end_date: '毕业时间',
        gpa: 'GPA',
        rank: '专业排名'
      }
    },
    'application.internships': {
      module: '实习经历',
      fields: {
        name: '单位名称',
        role: '职位名称',
        start_date: '开始时间',
        end_date: '结束时间',
        duty: '实习内容'
      }
    },
    'application.projects': {
      module: '项目经历',
      fields: {
        name: '项目名称',
        role: '担任角色',
        keywords: '技术栈',
        start_date: '开始时间',
        end_date: '结束时间',
        full_text: '项目描述',
        duty: '项目职责',
        achievement: '项目业绩'
      }
    },
    'application.campus_roles': {
      module: '在校职务',
      fields: { name: '职务名称', description: '职务描述', start_date: '开始时间', end_date: '结束时间' }
    },
    'application.campus_practices': {
      module: '在校实践',
      fields: { name: '实践名称', description: '实践描述', start_date: '开始时间', end_date: '结束时间' }
    },
    'application.award_records': {
      module: '获奖',
      fields: { name: '获奖项', date: '获奖时间', level: '获奖级别', description: '获奖描述' }
    },
    'application.certificate_records': {
      module: '证书',
      fields: { name: '证书名称', date: '获得时间' }
    },
    'application.languages': {
      module: '外语',
      fields: { type: '语言类型', level: '掌握程度', listen: '听说', speak: '口语', read: '读写' }
    },
    'application.family_members': {
      module: '家庭成员',
      fields: { name: '姓名', relation: '称谓', work: '工作单位', phone: '电话' }
    },
    'application.training_records': {
      module: '培训经历',
      fields: {
        name: '培训名称',
        org: '培训机构',
        start_date: '开始时间',
        end_date: '结束时间',
        description: '培训内容'
      }
    }
  };

  function lookupSlot(slot) {
    var s = String(slot || '');
    if (SCALAR_SLOTS[s]) return { list: false, module: SCALAR_SLOTS[s].module, label: SCALAR_SLOTS[s].label };
    var eduHit = s.match(/^universal\.education\.(?:records|undergraduate|junior_college)\.(.+)$/);
    if (eduHit) {
      var eduLabel = LIST_SLOTS['universal.education.records'].fields[eduHit[1]];
      if (eduLabel) return { list: true, module: '教育经历', label: eduLabel };
    }
    var listHit = s.match(/^(application\.[a-z_]+)\.(.+)$/);
    if (listHit && LIST_SLOTS[listHit[1]]) {
      var listLabel = LIST_SLOTS[listHit[1]].fields[listHit[2]];
      if (listLabel) return { list: true, module: LIST_SLOTS[listHit[1]].module, label: listLabel };
    }
    return null;
  }

  function moduleByTitle(nb, title) {
    var found = null;
    (nb.modules || []).forEach(function (m) {
      if (m && m.title === title) found = m;
    });
    return found || upsertModule(nb, { title: title });
  }

  function ensureModuleItemField(nb, title, itemIndex, label, value) {
    var mod = moduleByTitle(nb, title);
    return setField(nb, mod.id, itemIndex, label, value);
  }

  function addListModule(nb, spec, rows) {
    var idx = 0;
    (Array.isArray(rows) ? rows : []).forEach(function (row) {
      if (!rowHasValue(row)) return;
      var keys = Object.keys(spec.fields);
      var wrote = false;
      keys.forEach(function (key) {
        var val = row[key];
        if (val == null || String(val).trim() === '') return;
        if (key === 'end_date' && spec.fields[key] === '毕业时间' && row.graduation) return;
        ensureModuleItemField(nb, spec.module, idx, spec.fields[key], val);
        wrote = true;
      });
      if (wrote) idx += 1;
    });
  }

  function profileToNotebook(profile) {
    var nb = emptyNotebook();
    Object.keys(SCALAR_SLOTS).forEach(function (slot) {
      var val = getByPath(profile, slot);
      if (val == null || String(val).trim() === '') return;
      var info = SCALAR_SLOTS[slot];
      ensureModuleItemField(nb, info.module, 0, info.label, val);
    });
    addListModule(nb, LIST_SLOTS['universal.education.records'], educationRows(profile));
    Object.keys(LIST_SLOTS).forEach(function (path) {
      if (path === 'universal.education.records') return;
      addListModule(nb, LIST_SLOTS[path], getByPath(profile, path));
    });
    return compactNotebook(nb);
  }

  function importFields(fields, extra) {
    var nb = emptyNotebook();
    var counts = {};
    (fields || []).forEach(function (item) {
      if (!item) return;
      var value = item.value;
      if (value == null || String(value).trim() === '') return;
      value = String(value).trim();
      var info = item.slot ? lookupSlot(item.slot) : null;
      if (item.label) {
        var title = (info && info.module) || '导入';
        var key = title + '|' + normalizeLabel(item.label);
        var idx = 0;
        if (info && info.list) {
          idx = counts[key] || 0;
          counts[key] = idx + 1;
        }
        ensureModuleItemField(nb, title, idx, String(item.label).trim(), value);
        return;
      }
      if (!item.slot) return;
      if (!info) {
        ensureModuleItemField(nb, '导入', 0, item.slot, value);
        return;
      }
      var ck = info.module + '|' + info.label;
      var n = 0;
      if (info.list) {
        n = counts[ck] || 0;
        counts[ck] = n + 1;
      }
      ensureModuleItemField(nb, info.module, n, info.label, value);
    });
    if (extra && extra.target_position) {
      ensureModuleItemField(nb, '求职意向', 0, '求职意向', extra.target_position);
    }
    return compactNotebook(nb);
  }

  function flattenToImportModule(raw) {
    var nb = emptyNotebook();
    var fields = [];
    function walk(obj) {
      if (!obj || typeof obj !== 'object') return;
      Object.keys(obj).forEach(function (k) {
        if (k === 'version' || k === 'source' || k === 'test_only' || k === 'autofill') return;
        var v = obj[k];
        if (v == null) return;
        if (typeof v === 'string' || typeof v === 'number' || typeof v === 'boolean') {
          var s = String(v).trim();
          if (s) fields.push({ label: k, value: s });
        } else if (Array.isArray(v)) {
          v.forEach(function (item) {
            if (item && typeof item === 'object') walk(item);
            else if (item != null && String(item).trim()) fields.push({ label: k, value: String(item).trim() });
          });
        } else {
          walk(v);
        }
      });
    }
    walk(raw);
    if (!fields.length) {
      throw new Error('无法识别该 JSON。请提供自由模块、fields[].label/value，或旧版画像。');
    }
    var mod = upsertModule(nb, { title: '导入' });
    addItem(nb, mod.id, { fields: fields });
    return nb;
  }

  function looksLikeOldProfile(obj) {
    return !!(obj && typeof obj === 'object' && (obj.universal || obj.application) && !Array.isArray(obj.modules));
  }

  function loadState() {
    return new Promise(function (resolve) {
      if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
        var blank = emptyNotebook();
        resolve({ enabled: false, notebook: blank, profile: blank });
        return;
      }
      chrome.storage.local.get(
        { overlayEnabled: false, overlayNotebook: null, overlayProfile: null },
        function (stored) {
          var enabled = !!stored.overlayEnabled;
          var notebook;
          var migrated = false;
          if (stored.overlayNotebook && isNotebook(stored.overlayNotebook)) {
            notebook = stored.overlayNotebook;
          } else if (stored.overlayProfile) {
            try {
              notebook = normalizeImport(stored.overlayProfile);
              migrated = true;
            } catch (_) {
              notebook = emptyNotebook();
            }
          } else {
            notebook = emptyNotebook();
          }
          notebook = compactNotebook(notebook);
          var done = function () {
            resolve({ enabled: enabled, notebook: notebook, profile: notebook });
          };
          if (migrated) {
            chrome.storage.local.set({ overlayNotebook: notebook }, done);
          } else {
            done();
          }
        }
      );
    });
  }

  function saveState(enabled, notebook) {
    return new Promise(function (resolve) {
      var nb = notebook;
      try {
        if (nb && !isNotebook(nb)) nb = normalizeImport(nb);
      } catch (_) {
        nb = emptyNotebook();
      }
      nb = compactNotebook(nb || emptyNotebook());
      if (typeof chrome === 'undefined' || !chrome.storage || !chrome.storage.local) {
        resolve(true);
        return;
      }
      chrome.storage.local.set(
        { overlayEnabled: !!enabled, overlayNotebook: nb },
        function () { resolve(true); }
      );
    });
  }

  function isProfile(obj) {
    return looksLikeOldProfile(obj);
  }

  function normalizeImport(raw) {
    if (typeof raw === 'string') {
      raw = JSON.parse(raw);
    }
    if (!raw || typeof raw !== 'object') {
      throw new Error('不是 JSON 对象');
    }
    if (isNotebook(raw)) return raw;
    if (raw.notebook && isNotebook(raw.notebook)) return raw.notebook;
    if (looksLikeOldProfile(raw)) return profileToNotebook(raw);
    if (looksLikeOldProfile(raw.profile)) return profileToNotebook(raw.profile);
    if (looksLikeOldProfile(raw.overlayProfile)) return profileToNotebook(raw.overlayProfile);
    if (looksLikeOldProfile(raw.data)) return profileToNotebook(raw.data);
    var fields = raw.fields || (raw.autofill && raw.autofill.fields);
    if (Array.isArray(fields)) return importFields(fields, raw);
    return flattenToImportModule(raw);
  }

  function buildAiPrompt() {
    var schema = JSON.stringify({
      version: NOTEBOOK_VERSION,
      modules: [
        {
          id: 'm1',
          title: '个人信息',
          items: [{ fields: [{ label: '姓名', value: '' }, { label: '手机号', value: '' }] }]
        }
      ]
    }, null, 2);
    return [
      '你是网申填表 JSON 生成器。只输出一个 JSON 对象，不要用 Markdown 代码围栏，不要解释，不要注释。',
      '',
      '结构是自由模块内容库，不要再输出 universal / application 固定底稿：',
      '',
      schema,
      '',
      '规则：',
      '1. version 固定为 "4.0-notebook"。',
      '2. 模块名、字段名用中文，可按用户材料增减。',
      '3. 日期只用 YYYY-MM 或 YYYY-MM-DD。',
      '4. 重复经历用同一模块下多个 items。',
      '5. 禁止编造量化业绩、假手机号、假邮箱、假身份证；用户没给的字段留空。',
      '',
      '用户材料（简历或个人信息，原样保留事实）：',
      '',
      '（在这里粘贴简历或口述材料）'
    ].join('\n');
  }

  root.CareerOsOverlay = {
    KEY_ENABLED: KEY_ENABLED,
    KEY_PROFILE: KEY_PROFILE,
    KEY_NOTEBOOK: KEY_NOTEBOOK,
    KEY_SHAPES: KEY_SHAPES,
    emptyNotebook: emptyNotebook,
    isNotebook: isNotebook,
    upsertModule: upsertModule,
    addItem: addItem,
    setField: setField,
    valueByLabel: valueByLabel,
    compactNotebook: compactNotebook,
    normalizeLabel: normalizeLabel,
    resolveModuleTitle: resolveModuleTitle,
    makePageKey: makePageKey,
    shapeFromFields: shapeFromFields,
    hydrate: hydrate,
    ingestPageFields: ingestPageFields,
    mergeNotebook: mergeNotebook,
    applySavedShape: applySavedShape,
    loadShapes: loadShapes,
    saveShape: saveShape,
    lookupSlot: lookupSlot,
    SCALAR_SLOTS: SCALAR_SLOTS,
    LIST_SLOTS: LIST_SLOTS,
    rowHasValue: rowHasValue,
    compactList: compactList,
    educationRows: educationRows,
    loadState: loadState,
    saveState: saveState,
    normalizeImport: normalizeImport,
    buildAiPrompt: buildAiPrompt
  };
})(typeof self !== 'undefined' ? self : this);
