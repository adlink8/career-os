#!/usr/bin/env node
/**
 * 用本地 HTML 模拟北森 / Moka 报名表，跑一键填充，不打开真网站。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const assert = require('assert');

const ROOT = path.resolve(__dirname, '../..');
let JSDOM;
try {
  JSDOM = require('jsdom').JSDOM;
} catch (err) {
  console.log('SKIP form-mocks: 未安装 jsdom（tests/js/node_modules）');
  process.exit(0);
}

function loadScript(dom, rel) {
  const code = fs.readFileSync(path.join(ROOT, rel), 'utf8');
  const script = dom.window.document.createElement('script');
  script.textContent = code;
  dom.window.document.body.appendChild(script);
}

function loadProfile() {
  return JSON.parse(
    fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/profile.virtual.json'), 'utf8')
  );
}

function loadRules() {
  return JSON.parse(
    fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map-rules.json'), 'utf8')
  );
}

async function fillPage(htmlRel, hostname, href, hash) {
  const html = fs.readFileSync(path.join(ROOT, htmlRel), 'utf8');
  const dom = new JSDOM(html, {
    url: href,
    runScripts: 'dangerously',
    pretendToBeVisual: true
  });
  const w = dom.window;
  w.HTMLInputElement = w.HTMLInputElement;
  w.HTMLTextAreaElement = w.HTMLTextAreaElement;
  loadScript(dom, 'extensions/ats-autofill/field-map.js');
  loadScript(dom, 'extensions/ats-autofill/fill-policy.js');
  loadScript(dom, 'extensions/ats-autofill/fill-runtime.js');
  loadScript(dom, 'extensions/ats-autofill/beisen-fill.js');
  const fmap = w.CareerOsFieldMap;
  fmap.setRules(loadRules());
  const profile = loadProfile();
  const site = w.CareerOsFillRuntime.detect(href, hostname, hash);
  const result = await w.CareerOsBeisenFill.fill(profile, { fillGroups: w.CareerOsFillPolicy.defaults() });
  return { window: w, document: w.document, result: result, site: site };
}

function check(label, cond) {
  assert.ok(cond, label);
}

(async function main() {
  const beisen = await fillPage(
    'tests/fixtures/forms/beisen-campus.html',
    'leadchina.zhiye.com',
    'https://leadchina.zhiye.com/campus/form',
    ''
  );
  check('识别北森', beisen.site.ats === 'beisen');
  check('北森报名页', beisen.result.count >= 8);
  check('姓名', beisen.document.getElementById('name').value === '测一填');
  check('手机', beisen.document.getElementById('phone').value === '13800138000');
  check('学校', beisen.document.getElementById('school').value.indexOf('常州大学') !== -1);
  check('学历下拉', beisen.document.getElementById('degree').value.indexOf('本科') !== -1);
  check('学习形式', beisen.document.getElementById('edu-type').value.indexOf('专升本') !== -1 || beisen.document.getElementById('edu-type').value.indexOf('全日制') !== -1);
  const eduStart = beisen.document.getElementById('edu-start').value;
  check('教育开始时间写入', /2025-09/.test(eduStart));
  const internStart = beisen.document.getElementById('intern-start').value;
  check('实习开始时间写入', /2025-07/.test(internStart));
  check('语言类型', beisen.document.getElementById('lang-type').value.indexOf('中文') !== -1 || beisen.document.getElementById('lang-type').value.indexOf('英语') !== -1);

  const moka = await fillPage(
    'tests/fixtures/forms/moka-apply.html',
    'app.mokahr.com',
    'https://app.mokahr.com/apply/focus/1#/job/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/apply',
    '#/job/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee/apply'
  );
  check('识别 Moka', moka.site.ats === 'moka');
  check('Moka 是报名页', moka.site && moka.window.CareerOsFillRuntime.isApplyPage(moka.site, moka.window.location.href, moka.window.location.hash));
  check('Moka 姓名', moka.document.getElementById('moka-name').value === '测一填');
  check('Moka 邮箱', moka.document.getElementById('moka-email').value.indexOf('example.com') !== -1);
  check('Moka 学历', moka.document.getElementById('moka-degree').value.indexOf('本科') !== -1);

  const detail = moka.window.CareerOsFillRuntime.isApplyPage(
    { ats: 'moka' },
    'https://app.mokahr.com/apply/focus/1#/job/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
    '#/job/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
  );
  check('Moka 详情页判定为非报名', detail === false);

  console.log('[OK] form-mocks.test.js count', beisen.result.count, moka.result.count);
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
