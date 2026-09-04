<#
.SYNOPSIS
  Career OS — Phase 1 repeatable audit (VER-01).
  Reports VERIFIED / PARTIAL / MISSING for skills, knowledge domains, data, templates, docs.

.DESCRIPTION
  Truth source = the filesystem. No documentation claim is trusted.
  Run before any future "completion" claim in README or docs.

.USAGE
  pwsh scripts/audit.ps1          # terminal table
  pwsh scripts/audit.ps1 -Quiet   # exit code only (0=clean, 1=drift found)
#>
[CmdletBinding()]
param(
  [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# ---------- helpers ----------
function Test-FileExists($rel) { Test-Path (Join-Path $root $rel) }
function Get-DirFileCount($rel) {
  $p = Join-Path $root $rel
  if (-not (Test-Path $p)) { return -1 }
  @(Get-ChildItem -Path $p -File -Recurse -ErrorAction SilentlyContinue).Count
}

$rows = [System.Collections.Generic.List[pscustomobject]]::new()
$counts = @{ VERIFIED = 0; PARTIAL = 0; MISSING = 0 }
function Add-Row($Layer, $Item, $Status, $Note) {
  $rows.Add([pscustomobject]@{ Layer = $Layer; Item = $Item; Status = $Status; Note = $Note })
  if ($counts.ContainsKey($Status)) { $counts[$Status]++ }
}

# ---------- skills ----------
$declaredSkills = @(
  @{ name = 'career-personal-data-update'; ref = 'references/update-rules.md' },
  @{ name = 'career-daily-driver';         ref = 'references/daily-driver-spec.md' },
  @{ name = 'career-self-assessment';     ref = 'references/direction-matrix.md' },
  @{ name = 'career-industry-research';   ref = 'references/research-method.md' },
  @{ name = 'career-learning-path';       ref = 'references/learning-strategy.md' },
  @{ name = 'career-general-recruit';     ref = 'references/recruit-workflow.md' },
  @{ name = 'career-company-check';       ref = 'references/company-check-checklist.md' },
  @{ name = 'career-app-tracker';         ref = 'references/tracker-spec.md' },
  @{ name = 'career-assessment-prep';     ref = 'references/assessment-systems.md' },
  @{ name = 'career-interview-master';    ref = 'references/interview-flow.md' },
  @{ name = 'career-onboarding-prep';     ref = 'references/onboarding-checklist.md' },
  @{ name = 'career-probation-survival';  ref = 'references/survival-playbook.md' },
  @{ name = 'career-english-interview-prep'; ref = 'references/english-interview-playbook.md' },
  @{ name = 'career-resume-audit';        ref = 'references/evidence-status.md' }
)
foreach ($s in $declaredSkills) {
  $skillMd = "skills/$($s.name)/SKILL.md"
  if (-not (Test-FileExists $skillMd)) {
    Add-Row 'Skill' $s.name 'MISSING' 'No folder / SKILL.md absent'
    continue
  }
  if ($s.ref -and -not (Test-FileExists "skills/$($s.name)/$($s.ref)")) {
    Add-Row 'Skill' $s.name 'PARTIAL' "SKILL.md present, declared reference $($s.ref) absent"
  } else {
    Add-Row 'Skill' $s.name 'VERIFIED' ''
  }
}

# ---------- knowledge ----------
$knowledgeDomains = @(
  'self-assessment','industry-reports','roadmaps','jd-templates','company-check',
  'resume-templates','assessment-banks','interview-banks','salary-data','onboarding','survival'
)
foreach ($d in $knowledgeDomains) {
  $rel = "knowledge/$d"
  $n = Get-DirFileCount $rel
  if ($n -eq -1) {
    Add-Row 'Knowledge' $d 'MISSING' 'Directory absent'
  } elseif ($n -eq 0) {
    Add-Row 'Knowledge' $d 'MISSING' 'Directory exists but empty'
  } elseif ($n -ge 1 -and -not (Test-FileExists "$rel/README.md")) {
    Add-Row 'Knowledge' $d 'PARTIAL' "$n file(s), no domain README (KNOW-01)"
  } else {
    Add-Row 'Knowledge' $d 'VERIFIED' "$n file(s) + README"
  }
}
if (Test-FileExists 'knowledge/README.md') { Add-Row 'Knowledge' 'README.md (root)' 'VERIFIED' '' }

# ---------- data ----------
if (Test-FileExists 'config/profile.yml')   { Add-Row 'Data' 'config/profile.yml'   'VERIFIED' '' } else { Add-Row 'Data' 'config/profile.yml' 'MISSING' '' }
if (Test-FileExists 'data/tracker.tsv')     { Add-Row 'Data' 'data/tracker.tsv'     'VERIFIED' '' } else { Add-Row 'Data' 'data/tracker.tsv' 'MISSING' '' }

# ---------- templates ----------
if (Test-FileExists 'templates/cv-template.md') { Add-Row 'Template' 'cv-template.md' 'VERIFIED' '' } else { Add-Row 'Template' 'cv-template.md' 'MISSING' '' }

# ---------- docs ----------
if (Test-FileExists 'docs/architecture.md') { Add-Row 'Doc' 'architecture.md' 'VERIFIED' '' } else { Add-Row 'Doc' 'architecture.md' 'MISSING' '' }
if (Test-FileExists 'docs/how-to-use.md')   { Add-Row 'Doc' 'how-to-use.md'   'VERIFIED' '' } else { Add-Row 'Doc' 'how-to-use.md' 'MISSING' '' }

# ---------- planning ----------
$planningFiles = 'config.json','PROJECT.md','REQUIREMENTS.md','ROADMAP.md','STATE.md','STATUS.md'
foreach ($f in $planningFiles) {
  if (Test-FileExists ".planning/$f") { Add-Row 'Planning' $f 'VERIFIED' '' } else { Add-Row 'Planning' $f 'MISSING' '' }
}

# ---------- output ----------
if (-not $Quiet) {
  Write-Host ''
  Write-Host 'Career OS audit — ' (Get-Date -Format 'yyyy-MM-dd HH:mm') -ForegroundColor Cyan
  Write-Host ''
  $colorOf = @{ VERIFIED = 'Green'; PARTIAL = 'Yellow'; MISSING = 'Red' }
  foreach ($r in $rows) {
    $c = $colorOf[$r.Status]
    Write-Host ("  [{0,-8}] {1,-32} {2,-40}" -f $r.Status, "$($r.Layer)/$($r.Item)", $r.Note) -ForegroundColor $c
  }
  Write-Host ''
  Write-Host ("  Summary: VERIFIED={0}  PARTIAL={1}  MISSING={2}" -f $counts['VERIFIED'], $counts['PARTIAL'], $counts['MISSING']) -ForegroundColor Cyan
  Write-Host ''
}

# ---------- exit gate ----------
# Any MISSING in Skill layer, or any doc claiming skills that don't exist, = drift.
$skillMissing = ($rows | Where-Object { $_.Layer -eq 'Skill' -and $_.Status -eq 'MISSING' }).Count
if ($skillMissing -gt 0) { exit 1 } else { exit 0 }
