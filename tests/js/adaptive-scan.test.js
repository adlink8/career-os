#!/usr/bin/env node
/**
 * 自适应收窄：折叠分组 + 只扫表单项。缺 jsdom 时 SKIP。
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
let JSDOM;
try {
  JSDOM = require('jsdom').JSDOM;
} catch (err) {
  console.log('[OK] SKIP adaptive-scan: 未安装 jsdom（tests/js/node_modules）');
  process.exit(0);
}

function check(label, cond) {
  assert.ok(cond, label);
}

function loadScript(dom, rel) {
  const code = fs.readFileSync(path.join(ROOT, rel), 'utf8');
  const script = dom.window.document.createElement('script');
  script.textContent = code;
  dom.window.document.body.appendChild(script);
}

function loadCollapse() {
  const html = fs.readFileSync(path.join(ROOT, 'tests/fixtures/forms/beisen-collapse.html'), 'utf8');
  const dom = new JSDOM(html, {
    url: 'https://maxscend.zhiye.com/form',
    runScripts: 'dangerously',
    pretendToBeVisual: true
  });
  loadScript(dom, 'extensions/ats-autofill/overlay-store.js');
  loadScript(dom, 'extensions/ats-autofill/fill-runtime.js');
  return dom;
}

const dom = loadCollapse();
const w = dom.window;
const rt = w.CareerOsFillRuntime;
assert.ok(rt, 'CareerOsFillRuntime 未加载');

check(
  '折叠头教育经历',
  rt.nearbySection(w.document.getElementById('school')) === '教育经历'
);

const h2Wrap = w.document.createElement('div');
h2Wrap.innerHTML = '<h2>项目经历</h2><div class="el-form-item"><label class="el-form-item__label">旁路项目</label><input id="h2-proj"></div>';
w.document.body.appendChild(h2Wrap);
check(
  '仍支持旁边 h2',
  rt.nearbySection(w.document.getElementById('h2-proj')) === '项目经历'
);

check(
  '顶栏搜索没有折叠头',
  rt.nearbySection(w.document.getElementById('job-search')) === ''
);

const scanDom = loadCollapse();
const scanRt = scanDom.window.CareerOsFillRuntime;
const fields = scanRt.collectAdaptiveFields(scanDom.window.document);
const labels = fields.map(function (f) { return f.label; });
check('收姓名', labels.indexOf('姓名') !== -1);
check('收学校名称', labels.indexOf('学校名称') !== -1);
check('收项目名称', labels.indexOf('项目名称') !== -1);
check('不收搜索职位关键词', labels.indexOf('搜索职位关键词') === -1);
check('没有空 label', fields.every(function (f) { return f.label; }));
check('不收添加教育经历', labels.indexOf('添加教育经历') === -1);
const byLabel = {};
fields.forEach(function (f) { byLabel[f.label] = f; });
check('姓名进个人信息', byLabel['姓名'] && byLabel['姓名'].section === '个人信息');
check('学校名称进教育经历', byLabel['学校名称'] && byLabel['学校名称'].section === '教育经历');

const e2e = loadCollapse();
const store = e2e.window.CareerOsOverlay;
const e2eRt = e2e.window.CareerOsFillRuntime;
const nb = store.emptyNotebook();
store.upsertModule(nb, { id: 'p', title: '个人信息' });
store.addItem(nb, 'p');
store.setField(nb, 'p', 0, '姓名', '测一填');
store.upsertModule(nb, { id: 'e', title: '教育经历' });
store.addItem(nb, 'e');
store.setField(nb, 'e', 0, '学校名称', '');
store.upsertModule(nb, { id: 'proj', title: '项目经历' });
store.addItem(nb, 'proj');
store.setField(nb, 'proj', 0, '项目名称', '');
const scanned = e2eRt.collectAdaptiveFields(e2e.window.document);
const ingested = store.ingestPageFields(nb, scanned);
const titles = ingested.notebook.modules.map(function (m) { return m.title; });
const allFieldLabels = [];
ingested.notebook.modules.forEach(function (m) {
  (m.items || []).forEach(function (item) {
    (item.fields || []).forEach(function (f) { allFieldLabels.push(f.label); });
  });
});
check('端到端姓名不覆盖', store.valueByLabel(ingested.notebook, '姓名', 0) === '测一填');
check(
  '端到端出现学校名称',
  ingested.notebook.modules.some(function (m) {
    return m.title === '教育经历' && (m.items[0].fields || []).some(function (f) {
      return f.label === '学校名称';
    });
  })
);
check('没有搜索职位关键词当模块名', titles.indexOf('搜索职位关键词') === -1);
check('没有搜索职位关键词当字段', allFieldLabels.indexOf('搜索职位关键词') === -1);
check('教育经历只出现一次', titles.filter(function (t) { return t === '教育经历'; }).length === 1);

loadScript(e2e, 'extensions/ats-autofill/beisen-fill.js');
const fillItems = e2e.window.CareerOsBeisenFill.collectItems();
const fillByLabel = {};
fillItems.forEach(function (entry) { fillByLabel[entry.label] = entry; });
check('填表 collectItems 学校进教育经历', fillByLabel['学校名称'] && fillByLabel['学校名称'].section === '教育经历');
check('填表 collectItems 不收搜索', !fillByLabel['搜索职位关键词']);

console.log('[OK] adaptive-scan.test.js');
