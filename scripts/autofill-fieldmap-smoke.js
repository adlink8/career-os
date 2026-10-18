#!/usr/bin/env node
/**
 * 用真实先导报名表 schema + 测试画像测迁入与按字段名取值。
 * 不打开北森页面：填表按标签对内容库，旧槽位只用于 normalizeImport。
 */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const sandbox = { self: {}, console };
vm.runInNewContext(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/overlay-store.js'), 'utf8'),
  sandbox
);
vm.runInNewContext(
  fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/field-map.js'), 'utf8'),
  sandbox
);
const overlay = sandbox.self.CareerOsOverlay;
const fmap = sandbox.self.CareerOsFieldMap;
if (!overlay || !fmap) {
  console.error('FAILED: overlay/field-map not loaded');
  process.exit(1);
}

const testProfile = path.join(ROOT, 'extensions/ats-autofill/profile.test.json');
const liveProfile = path.join(ROOT, 'extensions/ats-autofill/profile.json');
const profile = JSON.parse(
  fs.readFileSync(fs.existsSync(testProfile) ? testProfile : liveProfile, 'utf8')
);
const notebook = overlay.normalizeImport(profile);
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
const empty = [];
const skipped = [];
for (const field of fields) {
  const label = field.label || '';
  if (fmap.isNoiseLabel(label) || /搜索职位/.test(label)) {
    skipped.push(label || '(empty)');
    continue;
  }
  const value = fmap.valueByLabel(label, notebook, 0);
  const row = {
    label: label || '(empty)',
    value: value || '',
    wouldFill: Boolean(value && !(/身份证/.test(label) && !fmap.isRealIdCard(value)))
  };
  if (row.wouldFill) filled.push(row);
  else empty.push(row);
}

console.log('schema fields', fields.length);
console.log('would fill', filled.length);
console.log('label miss or empty', empty.length);
console.log('skipped noise', skipped.length);
console.log('--- filled ---');
filled.forEach((r) => console.log(r.label.slice(0, 40), '|', String(r.value).slice(0, 40)));
console.log('--- empty ---');
empty.forEach((r) => console.log(r.label.slice(0, 60)));

check('姓名能填', fmap.valueByLabel('姓名', notebook, 0) === '测一填');
check('专业能填', fmap.valueByLabel('专业', notebook, 0).includes('计算机'));
check('项目名称能填', fmap.valueByLabel('项目名称', notebook, 0).includes('网关'));
check('项目描述能填', fmap.valueByLabel('项目描述', notebook, 0).length > 20);
check('测试手机号能填', fmap.valueByLabel('手机号', notebook, 0) === '13800138000');
check('测试邮箱能填', fmap.valueByLabel('邮箱', notebook, 0).includes('example.com'));
check('假身份证不填', !fmap.isRealIdCard(fmap.valueByLabel('身份证号', notebook, 0)));
check('请选择是噪声标签', fmap.isNoiseLabel('请选择'));
check('lookupSlot 仍给迁入用', overlay.lookupSlot('universal.education.records.school').label === '学校名称');
check('学习形式迁入标签', overlay.lookupSlot('universal.education.records.education_type').label === '学习形式');
check('期望城市迁入标签', overlay.lookupSlot('application.expected_city').label === '期望城市');

const scSrc = fs.readFileSync(path.join(ROOT, 'extensions/ats-autofill/shortcuts.js'), 'utf8');
vm.runInNewContext(scSrc, sandbox);
const sc = sandbox.self.CareerOsShortcuts;
check('shortcuts 加载', !!sc);
check('默认填表快捷键含 Alt+Shift', sc.format(sc.DEFAULTS.fill).indexOf('Alt') >= 0 && sc.format(sc.DEFAULTS.fill).indexOf('F') >= 0);

check('不再导出 emptyProfile', typeof overlay.emptyProfile !== 'function');
check('不再导出 setByPath', typeof overlay.setByPath !== 'function');
const imported = overlay.normalizeImport({
  fields: [{ slot: 'universal.personal.name', value: '拖入姓名' }],
  target_position: '运维工程师'
});
check('拖入 fields JSON 能归一', overlay.valueByLabel(imported, '姓名', 0) === '拖入姓名');
check('AI 提示词含 notebook version', overlay.buildAiPrompt().indexOf('4.0-notebook') >= 0);

check('按岗载荷覆盖意向', fmap.matchAutofillValue(
  { label: '求职意向' },
  { fields: [{ label: '求职意向', value: 'Java开发工程师（AI应用部）' }] }
) === 'Java开发工程师（AI应用部）');
check('测试城市是单选值', fmap.valueByLabel('期望城市', notebook, 0) === '南京市');
check('专业排名能填', fmap.valueByLabel('专业排名', notebook, 0).indexOf('20%') !== -1);
check('实践名称能填', fmap.valueByLabel('实践名称', notebook, 0).indexOf('社会实践') !== -1);
check('职务名称能填', fmap.valueByLabel('职务名称', notebook, 0).indexOf('技术委员') !== -1);
check('获奖时间能填', fmap.valueByLabel('获奖时间', notebook, 0) === '2024-12');
check('语言类型能填', fmap.valueByLabel('语言类型', notebook, 0) !== undefined);
console.log('[OK] autofill-fieldmap-smoke');
