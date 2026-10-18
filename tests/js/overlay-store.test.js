#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
const src = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/overlay-store.js'), 'utf8');

function loadStore(chrome) {
  const sandbox = { self: {}, console, chrome: chrome };
  vm.runInNewContext(src, sandbox);
  return sandbox.self.CareerOsOverlay;
}

function check(label, cond) {
  assert.ok(cond, label);
}

const store = loadStore(undefined);
assert.ok(store, 'CareerOsOverlay 未加载');

const empty = store.emptyNotebook();
check('默认空库无模块', Array.isArray(empty.modules) && empty.modules.length === 0);
check('默认版本是 notebook', empty.version === '4.0-notebook');

const old = {
  version: '3.0-overlay',
  universal: {
    personal: { name: '测一填' },
    education: {
      undergraduate: { school: '常州大学', major: '计科' },
      junior_college: { school: '某专科', major: '物联网' }
    }
  },
  application: {
    projects: [
      { name: '网关', role: '开发', full_text: '描述' },
      {},
      { name: '第二段' }
    ],
    internships: [{}]
  }
};
const nb = store.normalizeImport(old);
store.compactNotebook(nb);
check('不再导出 emptyProfile', typeof store.emptyProfile !== 'function');
check('不再导出 setByPath', typeof store.setByPath !== 'function');
check('不再导出 applySlot', typeof store.applySlot !== 'function');
check('normalizeImport 旧 JSON 仍有姓名', store.valueByLabel(nb, '姓名', 0) === '测一填');
check('normalizeImport 旧 JSON 仍有学校', store.valueByLabel(nb, '学校名称', 0) === '常州大学');
check('旧本科专科拆成两段学校', store.valueByLabel(nb, '学校名称', 0) === '常州大学' && store.valueByLabel(nb, '学校名称', 1) === '某专科');
check('压缩后只留有内容的项目', store.valueByLabel(nb, '项目名称', 0) === '网关' && store.valueByLabel(nb, '项目名称', 1) === '第二段');
check('空实习被丢掉', store.valueByLabel(nb, '单位名称', 0) === '');

const bag = {};
const chrome = {
  storage: {
    local: {
      get: function (defaults, cb) {
        const out = {};
        Object.keys(defaults).forEach(function (k) {
          out[k] = Object.prototype.hasOwnProperty.call(bag, k) ? bag[k] : defaults[k];
        });
        cb(out);
      },
      set: function (obj, cb) {
        Object.keys(obj).forEach(function (k) { bag[k] = obj[k]; });
        if (cb) cb();
      }
    }
  }
};
const store2 = loadStore(chrome);
bag.overlayEnabled = true;
bag.overlayProfile = old;
store2.loadState().then(function (state) {
  check('读到旧 overlayProfile 自动迁入', state.notebook && state.notebook.version === '4.0-notebook');
  check('迁入后能取姓名', store2.valueByLabel(state.notebook, '姓名', 0) === '测一填');
  return store2.saveState(true, state.notebook);
}).then(function () {
  check('saveState 写入 overlayNotebook', bag.overlayNotebook && bag.overlayNotebook.version === '4.0-notebook');
  check('saveState 不再把旧 profile 当权威', bag.overlayNotebook.modules.length > 0);
  console.log('[OK] overlay-store.test.js');
}).catch(function (err) {
  console.error(err);
  process.exit(1);
});
