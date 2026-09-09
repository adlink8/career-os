#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
const src = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/beisen-fill.js'), 'utf8');
const sandbox = {
  self: {},
  console,
  document: { querySelectorAll: () => [] },
  window: {},
  setTimeout: setTimeout
};
vm.runInNewContext(src, sandbox);
const api = sandbox.self.CareerOsBeisenFill;
assert.ok(api && api.optionCandidates, 'optionCandidates 未导出');

function check(label, cond) {
  assert.ok(cond, label);
}

const gender = api.optionCandidates('男');
check('男含男性', gender.indexOf('男性') !== -1);
const city = api.optionCandidates('南京');
check('南京补南京市', city.indexOf('南京市') !== -1);
const party = api.optionCandidates('共青团员');
check('共青团员含团员', party.indexOf('团员') !== -1);
check('fillDropdown 已导出', typeof api.fillDropdown === 'function');
check('日期 YYYY-MM 也出 YYYY-MM-01', api.dateVariants('2025-09').indexOf('2025-09-01') !== -1);
check('学历进入教育段', api.detectSection('学历', 'personal') === 'edu');
check('专业排名进入教育段', api.detectSection('专业排名', 'personal') === 'edu');
check('语言类型进入语言段', api.detectSection('语言类型', 'edu') === 'lang');
check('开始时间不改段', api.detectSection('开始时间', 'edu') === 'edu');
check('parseDate 2025-09 是 9 月', api.parseDate('2025-09').getMonth() === 8);
check('parseDate 2027-06-01 日', api.parseDate('2027-06-01').getDate() === 1);

console.log('[OK] fill-dropdown.test.js');
