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

const empty = store.emptyProfile();
check('默认实习为空数组', Array.isArray(empty.application.internships) && empty.application.internships.length === 0);
check('默认项目为空数组', empty.application.projects.length === 0);
check('默认证书为空数组', empty.application.certificate_records.length === 0);
check('默认在校职务为空', empty.application.campus_roles.length === 0);

empty.application.projects = [
  { name: '网关', role: '开发', keywords: '', start_date: '', end_date: '', full_text: '描述' },
  store.emptyRow(),
  { name: '第二段', role: '', keywords: '', start_date: '', end_date: '', full_text: '' }
];
empty.application.internships = [store.emptyRow()];
store.compactProfile(empty);
check('压缩后只留有内容的项目', empty.application.projects.length === 2);
check('空实习被丢掉', empty.application.internships.length === 0);
check('第二段有名称被保留', empty.application.projects[1].name === '第二段');

console.log('[OK] overlay-store.test.js');
