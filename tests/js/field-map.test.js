#!/usr/bin/env node
/**
 * 字段映射 JS 单元测试：不读真实 captures，只用测试画像。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
const mapSrc = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map.js'), 'utf8');
const sandbox = { self: {}, console };
vm.runInNewContext(mapSrc, sandbox);
const fmap = sandbox.self.CareerOsFieldMap;
assert.ok(fmap, 'CareerOsFieldMap 未加载');

const rules = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map-rules.json'), 'utf8')
);
fmap.setRules(rules);
const profile = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/profile.test.json'), 'utf8')
);

function check(label, cond) {
  assert.ok(cond, label);
}

check('姓名槽位', fmap.resolveSlot('姓名') === 'universal.personal.name');
check('学校名称', fmap.resolveSlot('学校名称') === 'universal.education.records.school');
check('学习形式', fmap.resolveSlot('学习形式') === 'universal.education.records.education_type');
check(
  '教育第二段读专科',
  fmap.valueForSlot('universal.education.records.school', profile, 1) === '江苏信息职业技术学院'
);
check(
  '旧 undergraduate 槽位仍读第一段',
  fmap.valueForSlot('universal.education.undergraduate.school', profile, 0) === '常州大学'
);
check('期望工作城市', fmap.resolveSlot('期望工作城市') === 'application.expected_city');
check('噪声标签', fmap.isNoiseLabel('请选择') === true);
check('假身份证不填', fmap.isRealIdCard('') === false);
check('18位才算身份证', fmap.isRealIdCard('11010119900101123' + 'X') === true);
check(
  '测试姓名',
  fmap.valueForSlot('universal.personal.name', profile, 0) === '测一填'
);
check(
  '测试手机',
  fmap.valueForSlot('universal.personal.phone', profile, 0) === '13800138000'
);
check(
  '测试邮箱不含个人域',
  String(fmap.valueForSlot('universal.personal.email', profile, 0)).includes('example.com')
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
