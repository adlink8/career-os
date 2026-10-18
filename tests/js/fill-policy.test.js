#!/usr/bin/env node
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
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/fill-policy.js'), 'utf8'),
  sandbox
);
const policy = sandbox.self.CareerOsFillPolicy;
assert.ok(policy, 'CareerOsFillPolicy 未加载');

function check(label, cond) {
  assert.ok(cond, label);
}

const notebook = {
  version: '4.0-notebook',
  modules: [
    { id: 'm1', title: '个人信息', items: [{ fields: [{ label: '姓名', value: '测一填' }, { label: '手机号', value: '13800138000' }] }] },
    { id: 'm2', title: '项目经历', items: [{ fields: [{ label: '项目名称', value: '网关' }] }] }
  ]
};

const groups = policy.groupsFrom(notebook);
check('分组来自模块标题', groups.length === 2 && groups[0].label === '个人信息' && groups[1].label === '项目经历');
check('默认按模块全开', policy.selectedIds(null, notebook).length === 2);

const onlyPersonal = policy.normalize({ m1: true, m2: false }, notebook);
check('只勾个人信息时姓名可填', policy.allowed('姓名', onlyPersonal, notebook) === true);
check('只勾个人信息时项目不填', policy.allowed('项目名称', onlyPersonal, notebook) === false);
check('未写进存储的模块默认勾选', policy.allowed('项目名称', policy.normalize({}, notebook), notebook) === true);

const none = policy.normalize({ m1: false, m2: false }, notebook);
check('显式全不选则跳过姓名', policy.allowed('手机号', none, notebook) === false);
check('未知标签仍放行', policy.allowed('自定义栏', none, notebook) === true);

console.log('[OK] fill-policy.test.js');
