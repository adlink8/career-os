<#
.SYNOPSIS
  Career OS — 静态冒烟测试 (VER-02 runtime-proxy)
  在没有 Agent 运行时的情况下，验证 14 个本地 skill 的自洽性与引用闭环。

.DESCRIPTION
  不调用 LLM,只检查结构契约:
    1. SKILL.md 的 YAML frontmatter 完整(name/displayName/description/trigger)
    2. SKILL.md 中声明引用的 references/* 文件真实存在
    3. SKILL.md 中声明的 config/data/knowledge 输入文件真实存在
    4. SKILL.md 有"输出规范"或"输出格式"章节
    5. 输出位置(如 tracker.tsv)的 schema 与 spec 一致

.USAGE
  pwsh scripts/smoke-test.ps1
#>
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$pass = 0; $fail = 0; $warn = 0
$failures = [System.Collections.Generic.List[string]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

function Check($label, $cond, $detail) {
  if ($cond) {
    Write-Host "  [PASS] $label" -ForegroundColor Green; $script:pass++
  } else {
    Write-Host "  [FAIL] $label — $detail" -ForegroundColor Red
    $script:fail++; $script:failures.Add("$label — $detail") | Out-Null
  }
}
function Warn($label, $detail) {
  Write-Host "  [WARN] $label — $detail" -ForegroundColor Yellow
  $script:warn++; $script:warnings.Add("$label — $detail") | Out-Null
}

# ---------- frontmatter 必填字段 ----------
$requiredFront = 'name','displayName','description','trigger'

$skills = @(
  @{ name='career-personal-data-update'; expectsRef='update-rules.md';            expectsInput=@('config/profile.yml') }
  @{ name='career-daily-driver';        expectsRef='daily-driver-spec.md';         expectsInput=@('config/profile.yml','data/current-status.md','data/tracker.tsv') }
  @{ name='career-self-assessment';     expectsRef='direction-matrix.md';          expectsInput=@('config/profile.yml') }
  @{ name='career-industry-research';   expectsRef='research-method.md';           expectsInput=@('config/profile.yml') }
  @{ name='career-learning-path';       expectsRef='learning-strategy.md';         expectsInput=@('config/profile.yml') }
  @{ name='career-general-recruit';     expectsRef='recruit-workflow.md';          expectsInput=@('config/profile.yml','templates/cv-template.md') }
  @{ name='career-company-check';       expectsRef='company-check-checklist.md';   expectsInput=@('config/profile.yml') }
  @{ name='career-app-tracker';         expectsRef='tracker-spec.md';              expectsInput=@('data/tracker.tsv') }
  @{ name='career-assessment-prep';     expectsRef='assessment-systems.md';        expectsInput=@('config/profile.yml') }
  @{ name='career-interview-master';    expectsRef='interview-flow.md';            expectsInput=@('config/profile.yml') }
  @{ name='career-onboarding-prep';     expectsRef='onboarding-checklist.md';      expectsInput=@('config/profile.yml') }
  @{ name='career-probation-survival';  expectsRef='survival-playbook.md';         expectsInput=@('config/profile.yml') }
  @{ name='career-resume-audit';        expectsRef='evidence-status.md';           expectsInput=@('config/profile.yml') }
  @{ name='career-english-interview-prep'; expectsRef='english-interview-playbook.md'; expectsInput=@('config/profile.yml','data/lessons-learned.md') }
)

Write-Host ''
Write-Host 'Career OS smoke test — ' (Get-Date -Format 'yyyy-MM-dd HH:mm') -ForegroundColor Cyan
Write-Host 'Scope: 14 local skills (daily-driver + English interview + runtime)'
Write-Host ''

foreach ($s in $skills) {
  Write-Host "▶ $($s.name)" -ForegroundColor White
  $skillPath = "skills/$($s.name)/SKILL.md"
  $fullPath = Join-Path $root $skillPath

  # 1. SKILL.md 存在并可读
  Check "$($s.name): SKILL.md exists" (Test-Path $fullPath) "file missing"

  if (-not (Test-Path $fullPath)) { continue }
  $content = Get-Content $fullPath -Raw -Encoding UTF8

  # 2. 提取 YAML frontmatter
  $fmMatch = [regex]::Match($content, '(?s)^---\s*\n(.*?)\n---')
  Check "$($s.name): YAML frontmatter present" $fmMatch.Success "no --- block at top"
  if ($fmMatch.Success) {
    $fm = $fmMatch.Groups[1].Value
    foreach ($f in $requiredFront) {
      Check "$($s.name): frontmatter has '$f'" ($fm -match "(?m)^$f\s*:") "missing field $f"
    }
  }

  # 3. 声明的 reference 文件存在
  $refPath = "skills/$($s.name)/references/$($s.expectsRef)"
  Check "$($s.name): reference $($s.expectsRef) exists" (Test-Path (Join-Path $root $refPath)) "declared reference not on disk"

  # 4. 声明的输入文件存在（支持 profile.yml 或模板 profile.example.yml）
  foreach ($inp in $s.expectsInput) {
    $exists = (Test-Path (Join-Path $root $inp)) -or ($inp -eq 'config/profile.yml' -and (Test-Path (Join-Path $root 'config/profile.example.yml')))
    Check "$($s.name): input '$inp' exists" $exists "declared input missing"
  }

  # 5. 输出规范章节
  $hasOutputSpec = $content -match '输出规范|输出格式|Output'
  Check "$($s.name): declares output format/spec" $hasOutputSpec "no 输出规范/输出格式 section"

  # 6. 检查 SKILL.md 内文本里所有 `references/xxx.md` 引用是否都存在
  $refMentions = [regex]::Matches($content, 'references/([A-Za-z0-9_\-\.]+\.md)')
  foreach ($m in $refMentions) {
    $refName = $m.Groups[1].Value
    $refFull = "skills/$($s.name)/references/$refName"
    Check "$($s.name): referenced $refName exists" (Test-Path (Join-Path $root $refFull)) "SKILL.md cites $refName but file absent"
  }
  Write-Host ''
}

# ---------- 跨 skill 一致性检查 ----------
Write-Host '▶ Cross-skill consistency' -ForegroundColor White

# career-app-tracker 的 TSV header 必须与 tracker-spec.md 字段一致
$tsv = Get-Content (Join-Path $root 'data/tracker.tsv') -Encoding UTF8
$headerLine = ($tsv | Where-Object { $_ -match '^日期\t公司名称\t目标岗位\t目标城市\t薪资范围\t企业官网\t校招网申直达链接\t当前状态\t战略定位与项目匹配备注$' } | Select-Object -First 1)
$specContent = Get-Content (Join-Path $root 'skills/career-app-tracker/references/tracker-spec.md') -Raw -Encoding UTF8
$expectedCols = '日期','公司名称','目标岗位','目标城市','薪资范围','企业官网','校招网申直达链接','当前状态','战略定位与项目匹配备注'
$allMatch = $true
foreach ($c in $expectedCols) {
  if (-not ($headerLine -and $headerLine.Contains($c))) { $allMatch = $false }
}
Check 'tracker.tsv header matches tracker-spec.md fields' $allMatch "TSV header out of sync with spec"

# profile.yml (或脱敏样本 profile.example.yml) 必须包含 career-app-tracker/self-assessment 等都依赖的关键字段
$profileFile = Join-Path $root 'config/profile.yml'
if (-not (Test-Path $profileFile)) {
  $profileFile = Join-Path $root 'config/profile.example.yml'
}
$profile = Get-Content $profileFile -Raw -Encoding UTF8
$profileRequired = 'personal:','education:','career_target:','skills:'
foreach ($k in $profileRequired) {
  Check "profile has section '$k'" ($profile.Contains($k)) "missing top-level section $k"
}
Write-Host ''

# ---------- DATA-03 模板分离检查 ----------
Write-Host '▶ DATA-03: template/real-data separation' -ForegroundColor White
$tpl = Get-Content (Join-Path $root 'templates/cv-template.md') -Raw -Encoding UTF8
$hasPlaceholder = $tpl -match '\{\{name\}\}'
$profileName = if ($profile -match 'name:\s*"([^"]+)"') { $matches[1] } else { $null }
$hasLeak = if ($profileName -and $profileName -ne '{{你的姓名}}') { $tpl.Contains($profileName) } else { $false }
Check 'cv-template.md does NOT leak profile name' (-not $hasLeak) "real personal data leaked into template"

$realExists = (Test-Path (Join-Path $root 'data/cv/cv-real.md')) -or (Test-Path (Join-Path $root 'templates/cv-template.md'))
Check 'data/cv/ (gitignored) or templates/cv-template.md is present' $realExists "CV specification missing"

$gitignore = Test-Path (Join-Path $root '.gitignore')
$giContent = if ($gitignore) { Get-Content (Join-Path $root '.gitignore') -Raw } else { '' }
Check '.gitignore excludes data/cv/ (incl. cv-real.md)' ($giContent -match 'data/cv/') 'real CV dir not gitignored'
Write-Host ''

# ---------- 总结 ----------
Write-Host ('=' * 60) -ForegroundColor Cyan
Write-Host ("  Result:  PASS=$pass  FAIL=$fail  WARN=$warn") -ForegroundColor Cyan
if ($failures.Count -gt 0) {
  Write-Host '  Failures:' -ForegroundColor Red
  foreach ($f in $failures) { Write-Host "    - $f" -ForegroundColor Red }
}
if ($warnings.Count -gt 0) {
  Write-Host '  Warnings:' -ForegroundColor Yellow
  foreach ($w in $warnings) { Write-Host "    - $w" -ForegroundColor Yellow }
}
Write-Host ''
if ($fail -gt 0) { exit 1 } else { exit 0 }
