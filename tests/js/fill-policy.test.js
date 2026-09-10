#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
const src = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/fill-policy.js'), 'utf8');
const sandbox = { self: {}, console };
vm.runInNewContext(src, sandbox);
const policy = sandbox.self.CareerOsFillPolicy;
assert.ok(policy, 'CareerOsFillPolicy 未加载');

function check(label, cond) {
  assert.ok(cond, label);
}

check('默认 9 类全开', policy.GROUPS.length === 9 && policy.selectedIds(null).length === 9);
check('姓名归个人信息', policy.groupForSlot('universal.personal.name') === 'personal');
check('教育 records 归教育', policy.groupForSlot('universal.education.records.school') === 'education');
check('家庭成员归个人信息', policy.groupForSlot('application.family_members.name') === 'personal');
check('培训归实习类', policy.groupForSlot('application.training_records.name') === 'intern');
check('到岗时间归求职意向', policy.groupForSlot('universal.personal.available_time') === 'intent');
check('项目归项目', policy.groupForSlot('application.projects.full_text') === 'projects');
check('证书归获奖证书', policy.groupForSlot('application.certificate_records.name') === 'award');
check('开放题', policy.groupForSlot('open.why_us') === 'open');

const onlyPersonal = policy.normalize({ personal: true });
policy.GROUPS.forEach((g) => {
  if (g.id !== 'personal') onlyPersonal[g.id] = false;
});
check('只勾个人信息时姓名可填', policy.allowed('universal.personal.name', onlyPersonal) === true);
check('只勾个人信息时项目不填', policy.allowed('application.projects.name', onlyPersonal) === false);
check('未写进存储的类别默认勾选', policy.allowed('application.projects.name', policy.normalize({})) === true);

const none = {};
policy.GROUPS.forEach((g) => { none[g.id] = false; });
check('显式全不选则跳过姓名', policy.allowed('universal.personal.phone', none) === false);
check('未知槽位仍放行', policy.allowed('custom.unknown', none) === true);

console.log('[OK] fill-policy.test.js');
