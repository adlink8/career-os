#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
const src = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/overlay-store.js'), 'utf8');
const sandbox = { self: {}, console, chrome: undefined };
vm.runInNewContext(src, sandbox);
const store = sandbox.self.CareerOsOverlay;
assert.ok(store, 'CareerOsOverlay 未加载');

function check(label, cond) {
  assert.ok(cond, label);
}

const empty = store.emptyNotebook();
check('空库版本 4.0-notebook', empty.version === '4.0-notebook');
check('空库 modules 是空数组', Array.isArray(empty.modules) && empty.modules.length === 0);

const nb = store.emptyNotebook();
store.upsertModule(nb, { id: 'm1', title: '个人信息' });
store.addItem(nb, 'm1');
store.setField(nb, 'm1', 0, '姓名', '测一填');
store.setField(nb, 'm1', 0, '手机号', '13800138000');
check("valueByLabel 姓名", store.valueByLabel(nb, '姓名', 0) === '测一填');
check("valueByLabel 手机号", store.valueByLabel(nb, '手机号', 0) === '13800138000');

store.upsertModule(nb, { id: 'm2', title: '项目经历' });
store.addItem(nb, 'm2');
store.setField(nb, 'm2', 0, '项目名称', '网关');
store.addItem(nb, 'm2');
store.setField(nb, 'm2', 1, '项目名称', '第二段');
check('同标签第 0 段', store.valueByLabel(nb, '项目名称', 0) === '网关');
check('同标签第 1 段', store.valueByLabel(nb, '项目名称', 1) === '第二段');

check('标签去空白', store.valueByLabel(nb, ' 姓名 ', 0) === '测一填');
check('请输入前缀对上标签', store.valueByLabel(nb, '请输入姓名', 0) === '测一填');
check('请选择前缀对上标签', store.valueByLabel(nb, '请选择姓名', 0) === '测一填');

store.addItem(nb, 'm2');
store.setField(nb, 'm2', 2, '项目名称', '');
store.setField(nb, 'm2', 2, '项目描述', '   ');
store.upsertModule(nb, { id: 'm3', title: '备用空模块' });
store.compactNotebook(nb);
check('压缩丢掉全空 item', nb.modules[1].items.length === 2);
check('空模块可留作备用', nb.modules.some(function (m) { return m.id === 'm3' && m.title === '备用空模块'; }));
check('压缩后项目仍两段', store.valueByLabel(nb, '项目名称', 1) === '第二段');

const oldProfile = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/profile.test.json'), 'utf8')
);
const imported = store.normalizeImport(oldProfile);
check('旧画像变成 notebook', imported.version === '4.0-notebook');
check('迁入不暴露 slot 当模块名', imported.modules.every(function (m) {
  return !/universal\.|application\./.test(m.title || '');
}));
check('迁入姓名', store.valueByLabel(imported, '姓名', 0) === '测一填');
check('迁入手机号', store.valueByLabel(imported, '手机号', 0) === '13800138000');
check('迁入学校第一段', store.valueByLabel(imported, '学校名称', 0) === '常州大学');
check('迁入学校第二段', store.valueByLabel(imported, '学校名称', 1) === '江苏信息职业技术学院');
check('迁入项目第一段', store.valueByLabel(imported, '项目名称', 0) === '测试项目·网关联调平台');
check('迁入实习内容', store.valueByLabel(imported, '实习内容', 0).indexOf('巡检') !== -1);

const labeled = store.normalizeImport({
  fields: [
    { label: '姓名', value: '甲' },
    { label: '项目名称', value: '网关' }
  ]
});
check('fields.label 灌入姓名', store.valueByLabel(labeled, '姓名', 0) === '甲');
check('fields.label 灌入项目', store.valueByLabel(labeled, '项目名称', 0) === '网关');

const slotted = store.normalizeImport({
  fields: [
    { slot: 'universal.personal.name', value: '乙' },
    { slot: 'application.projects.name', value: '旧槽项目' }
  ]
});
check('无 label 才用旧 slot 姓名', store.valueByLabel(slotted, '姓名', 0) === '乙');
check('无 label 才用旧 slot 项目', store.valueByLabel(slotted, '项目名称', 0) === '旧槽项目');

const mixed = store.normalizeImport({
  fields: [{ label: '自定义栏', slot: 'universal.personal.name', value: '丙' }]
});
check('有 label 不走 slot 名', store.valueByLabel(mixed, '自定义栏', 0) === '丙');
check('有 label 不写成姓名槽', store.valueByLabel(mixed, '姓名', 0) === '');

const already = store.normalizeImport({
  version: '4.0-notebook',
  modules: [{ id: 'm1', title: '个人信息', items: [{ fields: [{ label: '姓名', value: '丁' }] }] }]
});
check('已经是 notebook 原样用', store.valueByLabel(already, '姓名', 0) === '丁');

const free = store.normalizeImport({ 自我介绍: '能干活', extra: { note: '备注一句' } });
check('自由 JSON 落到导入模块', free.modules.some(function (m) { return m.title === '导入'; }));
check('自由 JSON 按名字灌入', store.valueByLabel(free, '自我介绍', 0) === '能干活');

const pageKey = store.makePageKey('https://leadchina.zhiye.com/campus/form#sec');
check(
  'pageKey 稳定',
  pageKey === 'leadchina.zhiye.com|/campus/form|#sec'
);
check(
  'pageKey 无 hash 也收尾竖线',
  store.makePageKey('https://leadchina.zhiye.com/campus/form') === 'leadchina.zhiye.com|/campus/form|'
);

const shape = store.shapeFromFields([
  { section: '个人信息', label: '姓名' },
  { section: '个人信息', label: '手机号' },
  { section: '个人信息', label: '姓名' },
  { section: '', label: '备注' },
  { section: '项目经历', label: '项目名称' },
  { section: '项目经历', label: '项目描述' }
]);
check('同 section 字段去重保序', JSON.stringify(shape.modules[0].fields) === JSON.stringify(['姓名', '手机号']));
check('空 section 归未分组', shape.modules.some(function (m) { return m.title === '未分组' && m.fields[0] === '备注'; }));
check('项目骨架字段', JSON.stringify(shape.modules.filter(function (m) { return m.title === '项目经历'; })[0].fields) === JSON.stringify(['项目名称', '项目描述']));

const pool = store.emptyNotebook();
store.upsertModule(pool, { id: 'm1', title: '个人信息' });
store.addItem(pool, 'm1');
store.setField(pool, 'm1', 0, '姓名', '测一填');
store.upsertModule(pool, { id: 'spare', title: '备用空模块' });
store.hydrate(pool, shape);
check('水合保留已有 value', store.valueByLabel(pool, '姓名', 0) === '测一填');
check('水合补空字段', store.valueByLabel(pool, '手机号', 0) === '');
const personal = pool.modules.filter(function (m) { return m.title === '个人信息'; })[0];
check('水合个人信息有手机号空字段', personal.items[0].fields.some(function (f) { return f.label === '手机号' && f.value === ''; }));
check('骨架没点名的模块原样留着', pool.modules.some(function (m) { return m.id === 'spare' && m.title === '备用空模块'; }));
check('骨架有而内容库没有的模块会建空的', pool.modules.some(function (m) { return m.title === '项目经历'; }));

const miss = store.applySavedShape(pool, {}, 'no.such.host|/x|');
check('没有该页骨架时 ok=false', miss.ok === false && !!miss.reason);
check('没有骨架不改 notebook', pool.modules.some(function (m) { return m.id === 'spare'; }));

const shapes = {};
const saved = {
  pageKey: pageKey,
  modules: [{ title: '个人信息', fields: ['姓名', '邮箱'] }]
};
const applied = store.applySavedShape(pool, { [pageKey]: saved }, pageKey);
check('手动套用上次骨架成功', applied.ok === true);
check('套用后补邮箱空字段', pool.modules.filter(function (m) { return m.title === '个人信息'; })[0].items[0].fields.some(function (f) { return f.label === '邮箱'; }));

check('没有当前页变化监听 API', typeof store.onPageChange !== 'function' && typeof store.autoApplyShape !== 'function');

const ingested = store.ingestPageFields(pool, [
  { section: '个人信息', label: '姓名', value: '' },
  { section: '个人信息', label: '民族', value: '汉族' }
]);
check('自适应空值不覆盖已有正文', store.valueByLabel(ingested.notebook, '姓名', 0) === '测一填');
check('自适应把页面已填值灌进内容库', store.valueByLabel(ingested.notebook, '民族', 0) === '汉族');

const eduNb = store.emptyNotebook();
store.upsertModule(eduNb, { id: 'p', title: '个人信息' });
store.addItem(eduNb, 'p');
store.setField(eduNb, 'p', 0, '姓名', '测一填');
store.upsertModule(eduNb, { id: 'e', title: '教育经历' });
store.addItem(eduNb, 'e');
store.setField(eduNb, 'e', 0, '学校名称', '常州大学');
store.setField(eduNb, 'e', 0, '专业', '物联网');
check(
  '字段对上时教育信息并进教育经历',
  store.resolveModuleTitle(eduNb, '教育信息', ['学校名称', '专业名称']) === '教育经历'
);
check(
  '标题全等用教育经历',
  store.resolveModuleTitle(eduNb, '教育经历', ['学校名称']) === '教育经历'
);
check(
  '空底稿用页面分组名',
  store.resolveModuleTitle(store.emptyNotebook(), '论文', ['论文题目']) === '论文'
);
check(
  '未分组对不上不要塞进个人信息',
  store.resolveModuleTitle(eduNb, '未分组', ['验证码']) === '未分组'
);

const mergeNb = store.emptyNotebook();
store.upsertModule(mergeNb, { id: 'p', title: '个人信息' });
store.addItem(mergeNb, 'p');
store.setField(mergeNb, 'p', 0, '姓名', '测一填');
store.upsertModule(mergeNb, { id: 'e', title: '教育经历' });
store.addItem(mergeNb, 'e');
store.setField(mergeNb, 'e', 0, '学校名称', '');
store.setField(mergeNb, 'e', 0, '专业', '物联网');
const merged = store.ingestPageFields(mergeNb, [
  { section: '教育信息', label: '学校名称', value: '' },
  { section: '教育信息', label: '专业名称', value: '' },
  { section: '项目经历', label: '项目名称', value: '' },
  { section: '项目经历', label: '项目描述', value: '网关联调' }
]);
const mergeTitles = merged.notebook.modules.map(function (m) { return m.title; });
check('模块仍以个人信息、教育经历开头', mergeTitles[0] === '个人信息' && mergeTitles[1] === '教育经历');
check(
  '教育经历补上学校名称空字段',
  merged.notebook.modules[1].items[0].fields.some(function (f) {
    return f.label === '学校名称' && f.value === '';
  })
);
check('没有新模块教育信息', mergeTitles.indexOf('教育信息') === -1);
check('项目经历按页面名新建', mergeTitles.indexOf('项目经历') !== -1);
check('教育经历只出现一次', mergeTitles.filter(function (t) { return t === '教育经历'; }).length === 1);
check('页面已填项目描述灌入', store.valueByLabel(merged.notebook, '项目描述', 0) === '网关联调');

console.log('[OK] notebook-store.test.js');
