#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
const src = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/fill-runtime.js'), 'utf8');
const sandbox = { self: {}, console };
vm.runInNewContext(src, sandbox);
const rt = sandbox.self.CareerOsFillRuntime;
assert.ok(rt, 'CareerOsFillRuntime 未加载');

function check(label, cond) {
  assert.ok(cond, label);
}

const mokaUrl =
  'https://app.mokahr.com/apply/focus/148405?sourceToken=abc#/job/f5bfbd62-fd05-476a-8807-f5bb6b114b53/apply';
const mokaDetail =
  'https://app.mokahr.com/apply/focus/148405?sourceToken=abc#/job/f5bfbd62-fd05-476a-8807-f5bb6b114b53';

const moka = rt.detect(mokaUrl, 'app.mokahr.com', '#/job/f5bfbd62-fd05-476a-8807-f5bb6b114b53/apply');
check('识别 Moka', moka.ats === 'moka');
check('Moka 报名页', rt.isApplyPage(moka, mokaUrl, '#/job/f5bfbd62-fd05-476a-8807-f5bb6b114b53/apply') === true);
check(
  'Moka 详情页不是报名表',
  rt.isApplyPage(moka, mokaDetail, '#/job/f5bfbd62-fd05-476a-8807-f5bb6b114b53') === false
);

const beisen = rt.detect('https://foo.zhiye.com/campus/form', 'foo.zhiye.com', '');
check('识别北森', beisen.ats === 'beisen');
check('识别大易', rt.detect('', 'corp.dayee.com', '').ats === 'dayee');
check('识别飞书', rt.detect('', 'jobs.feishu.cn', '').ats === 'feishu');
check('未知走 generic', rt.detect('', 'careers.example.com', '').ats === 'generic');

const plan = rt.expandPlan({
  universal: { education: { undergraduate: { school: '常州大学' }, junior_college: { school: '某专科' } } },
  application: {
    internships: [{ name: '测试科技' }],
    projects: [{ name: 'A' }, { name: 'B' }],
    campus_roles: [],
    award_records: [{ name: '奖' }, { name: '奖2' }, { name: '' }]
  }
});
check('一段实习不点添加', plan.intern === 0);
check('两段项目点 1 次添加', plan.projects === 1);
check('专科+本科教育点 1 次', plan.edu === 1);
const planRecords = rt.expandPlan({
  universal: {
    education: {
      records: [{ school: '本科校' }, { school: '专科校' }, { school: '高中' }]
    }
  },
  application: {}
});
check('三段教育点 2 次添加', planRecords.edu === 2);
check('空行不算段数', plan.awards === 1);
check('extraClicks(0)=0', rt.extraClicks(0) === 0);

function fakeEl(placeholder, prevText) {
  const prev = { textContent: prevText, previousElementSibling: null, querySelector: () => null };
  return {
    placeholder: placeholder,
    getAttribute: () => '',
    ownerDocument: { getElementById: () => null },
    previousElementSibling: prev,
    parentElement: { previousElementSibling: null, tagName: 'DIV', parentElement: null }
  };
}
check('旁边标题认出姓名', rt.nearbyLabel(fakeEl('请输入', '姓名')) === '姓名');
check('旁边标题认出学历', rt.nearbyLabel(fakeEl('请选择', '学历')) === '学历');
check('整页导航不当标题', rt.nearbyLabel(fakeEl('请输入', '首页了解先导社会招聘')) === '');

console.log('[OK] fill-runtime.test.js');
