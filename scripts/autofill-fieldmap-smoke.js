#!/usr/bin/env node
/**
 * 用真实先导报名表 schema + 本地 profile.json 测 field-map 填值。
 * 不打开北森页面：验证「格子 → 槽位 → 画像值」这条自动填写核心路径。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const mapSrc = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map.js'), 'utf8');
const sandbox = { self: {}, console };
vm.runInNewContext(mapSrc, sandbox);
const fmap = sandbox.self.CareerOsFieldMap;
if (!fmap) {
  console.error('FAILED: CareerOsFieldMap not loaded');
  process.exit(1);
}
const rules = JSON.parse(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map-rules.json'), 'utf8')
);
fmap.setRules(rules);

const testProfile = path.join(ROOT, 'extensions/ats-autofill/profile.test.json');
const liveProfile = path.join(ROOT, 'extensions/ats-autofill/profile.json');
const profile = JSON.parse(
  fs.readFileSync(fs.existsSync(testProfile) ? testProfile : liveProfile, 'utf8')
);
const capturePath = path.join(
  ROOT,
  'data/job_discovery/captures/job-context-leadchina.zhiye.com-ec6ce6c4-501d-476f-a63c-e23285b7b5ce.json'
);
const capture = JSON.parse(fs.readFileSync(capturePath, 'utf8'));
const fields = capture.form_schema || [];

function check(label, cond) {
  if (!cond) throw new Error(label);
  console.log('[PASS]', label);
}

const filled = [];
const mappedEmpty = [];
const unmapped = [];
for (const field of fields) {
  const isTextarea = field.tag === 'textarea' || field.type === 'textarea';
  const slot = fmap.resolveSlot(field.label || '', { isTextarea });
  const value = fmap.valueForSlot(slot, profile, 0);
  const row = {
    label: field.label || '(empty)',
    slot: slot || '',
    value: value || '',
    wouldFill: Boolean(slot && value && !(slot.endsWith('id_card') && !fmap.isRealIdCard(value)))
  };
  if (row.wouldFill) filled.push(row);
  else if (slot) mappedEmpty.push(row);
  else unmapped.push(row);
}

console.log('schema fields', fields.length);
console.log('would fill', filled.length);
console.log('mapped but profile empty', mappedEmpty.length);
console.log('unmapped', unmapped.length);
console.log('--- filled ---');
filled.forEach((r) => console.log(r.slot, '|', r.label.slice(0, 40), '|', String(r.value).slice(0, 40)));
console.log('--- mapped empty ---');
mappedEmpty.forEach((r) => console.log(r.slot, '|', r.label.slice(0, 40)));
console.log('--- unmapped ---');
unmapped.forEach((r) => console.log(r.label.slice(0, 60)));

const bySlot = Object.fromEntries(filled.map((r) => [r.slot, r]));
check('姓名能填', bySlot['universal.personal.name'] && bySlot['universal.personal.name'].value === '测一填');
check('专业能填', bySlot['universal.education.undergraduate.major'] && bySlot['universal.education.undergraduate.major'].value.includes('计算机'));
check('项目名称能填', bySlot['application.projects.name'] && bySlot['application.projects.name'].value.includes('网关'));
check('项目描述能填', bySlot['application.projects.full_text'] && bySlot['application.projects.full_text'].value.length > 20);
check('测试手机号能填', bySlot['universal.personal.phone'] && bySlot['universal.personal.phone'].value === '13800138000');
check('测试邮箱能填', bySlot['universal.personal.email'] && bySlot['universal.personal.email'].value.includes('example.com'));
check('假身份证不填', !filled.some((r) => r.slot === 'universal.personal.id_card'));
check('学校名称能映射', fmap.resolveSlot('学校名称', { isTextarea: false }) === 'universal.education.undergraduate.school');
check('学习形式能映射', fmap.resolveSlot('学习形式', { isTextarea: false }) === 'universal.education.undergraduate.education_type');
check('期望工作城市能映射', fmap.resolveSlot('期望工作城市', { isTextarea: false }) === 'application.expected_city');
check('专业排名能映射', fmap.resolveSlot('专业排名', { isTextarea: false }) === 'universal.education.undergraduate.rank');
check('实践名称能映射', fmap.resolveSlot('实践名称', { isTextarea: false }) === 'application.campus_practices.name');
check('职务名称能映射', fmap.resolveSlot('职务名称', { isTextarea: false }) === 'application.campus_roles.name');
check('获奖时间能映射', fmap.resolveSlot('获奖时间', { isTextarea: false }) === 'application.award_records.date');
check('语言类型能映射', fmap.resolveSlot('语言类型', { isTextarea: false }) === 'application.languages.type');
check('测试城市是单选值', fmap.valueForSlot('application.expected_city', profile, 0) === '南京市');
console.log('[OK] autofill-fieldmap-smoke');
