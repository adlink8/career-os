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
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/fill-runtime.js'), 'utf8'),
  sandbox
);
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
  version: '4.0-notebook',
  modules: [
    {
      id: 'edu',
      title: '教育经历',
      items: [
        { fields: [{ label: '学校名称', value: '常州大学' }] },
        { fields: [{ label: '学校名称', value: '某专科' }] }
      ]
    },
    {
      id: 'intern',
      title: '实习经历',
      items: [{ fields: [{ label: '单位名称', value: '测试科技' }] }]
    },
    {
      id: 'proj',
      title: '项目经历',
      items: [
        { fields: [{ label: '项目名称', value: 'A' }] },
        { fields: [{ label: '项目名称', value: 'B' }] }
      ]
    },
    {
      id: 'award',
      title: '获奖',
      items: [
        { fields: [{ label: '获奖项', value: '奖' }] },
        { fields: [{ label: '获奖项', value: '奖2' }] },
        { fields: [{ label: '获奖项', value: '' }] }
      ]
    }
  ]
});
check('一段实习不点添加', plan['实习经历'] === 0);
check('两段项目点 1 次添加', plan['项目经历'] === 1);
check('专科+本科教育点 1 次', plan['教育经历'] === 1);
const planRecords = rt.expandPlan({
  version: '4.0-notebook',
  modules: [
    {
      id: 'edu',
      title: '教育经历',
      items: [
        { fields: [{ label: '学校名称', value: '本科校' }] },
        { fields: [{ label: '学校名称', value: '专科校' }] },
        { fields: [{ label: '学校名称', value: '高中' }] }
      ]
    }
  ]
});
check('三段教育点 2 次添加', planRecords['教育经历'] === 2);
check('空行不算段数', plan['获奖'] === 1);
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
check('附近标题按模块名归类', rt.classifyAdd(fakeEl('添加', '项目经历')) === '项目经历');
check('没有模块标题时项目退路', rt.classifyAdd(fakeEl('添加', '项目')) === '项目经历');
check('旁边标题认出姓名', rt.nearbyLabel(fakeEl('请输入', '姓名')) === '姓名');
check('旁边标题认出学历', rt.nearbyLabel(fakeEl('请选择', '学历')) === '学历');
check('整页导航不当标题', rt.nearbyLabel(fakeEl('请输入', '首页了解先导社会招聘')) === '');

const overlay = sandbox.self.CareerOsOverlay;
check(
  'pageKey 字面量含 hash',
  overlay.makePageKey('https://leadchina.zhiye.com/campus/form#sec') === 'leadchina.zhiye.com|/campus/form|#sec'
);
check(
  'pageKey 丢掉 query 留 hash',
  overlay.makePageKey('https://leadchina.zhiye.com/campus/form?x=1#sec') === 'leadchina.zhiye.com|/campus/form|#sec'
);
check('sleep 从 runtime 导出', typeof rt.sleep === 'function');
check('setNativeValue 从 runtime 导出', typeof rt.setNativeValue === 'function');

const beisenSrc = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/beisen-fill.js'), 'utf8');
check('beisen sleep 走 runtime', /CareerOsFillRuntime[\s\S]{0,80}sleep/.test(beisenSrc) && beisenSrc.indexOf('runtime.sleep') !== -1);
check('beisen setInput 走 runtime.setNativeValue', beisenSrc.indexOf('setNativeValue') !== -1);

console.log('[OK] fill-runtime.test.js');
