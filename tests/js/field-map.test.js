#!/usr/bin/env node
/**
 * 字段映射 JS 单元测试：不读真实 captures，只用测试画像。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
const sandbox = { self: {}, console };
vm.runInNewContext(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/overlay-store.js'), 'utf8'),
  sandbox
);
vm.runInNewContext(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map.js'), 'utf8'),
  sandbox
);
const store = sandbox.self.CareerOsOverlay;
const fmap = sandbox.self.CareerOsFieldMap;
assert.ok(fmap, 'CareerOsFieldMap 未加载');
assert.ok(store, 'CareerOsOverlay 未加载');

const rules = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map-rules.json'), 'utf8')
);
fmap.setRules(rules);
const profile = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/profile.test.json'), 'utf8')
);
const notebook = store.normalizeImport(profile);

function check(label, cond) {
  assert.ok(cond, label);
}

check('填表用 valueByLabel 姓名', fmap.valueByLabel('姓名', notebook, 0) === '测一填');
check('填表用 valueByLabel 去请输入', fmap.valueByLabel('请输入姓名', notebook, 0) === '测一填');
check('填表用 valueByLabel 学校第二段', fmap.valueByLabel('学校名称', notebook, 1) === '江苏信息职业技术学院');
check('填表用 valueByLabel 手机号', fmap.valueByLabel('手机号', notebook, 0) === '13800138000');
check(
  'lookupSlot 只给迁入翻标签',
  store.lookupSlot('universal.personal.name') && store.lookupSlot('universal.personal.name').label === '姓名'
);
fmap.setRules([]);
check('填表不依赖 setRules', fmap.valueByLabel('姓名', notebook, 0) === '测一填');
fmap.setRules(rules);

const contentSrc = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/content.js'), 'utf8');
const beisenSrc = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/beisen-fill.js'), 'utf8');
check('content 填入不走 valueForSlot', contentSrc.indexOf('valueForSlot') === -1);
check('beisen pickValue 不走 valueForSlot', beisenSrc.indexOf('valueForSlot') === -1);
check('噪声标签', fmap.isNoiseLabel('请选择') === true);
check('假身份证不填', fmap.isRealIdCard('') === false);
check('18位才算身份证', fmap.isRealIdCard('11010119900101123' + 'X') === true);
check(
  '测试邮箱不含个人域',
  String(fmap.valueByLabel('邮箱', notebook, 0)).includes('example.com')
);

const autofill = {
  fields: [
    { label: '求职意向', slot: 'application.target_position', value: '运维工程师' },
    { label: '为什么选择本公司', slot: 'open.why_us', value: '因为 Linux 对口。' },
  ],
};
check(
  'matchAutofill 按标签',
  fmap.matchAutofillValue({ label: '求职意向' }, autofill) === '运维工程师'
);
check(
  'matchAutofill 开放题',
  fmap.matchAutofillValue({ label: '为什么选择本公司' }, autofill).includes('Linux')
);

console.log('[OK] field-map.test.js');
