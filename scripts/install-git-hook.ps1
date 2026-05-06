$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path "$PSScriptRoot\..").Path
$hookSource = Join-Path $repoRoot ".githooks\post-commit"
$hookTargetDir = Join-Path $repoRoot ".git\hooks"
$hookTarget = Join-Path $hookTargetDir "post-commit"

if (-not (Test-Path $hookSource)) {
    throw "Hook source not found: $hookSource"
}

if (-not (Test-Path $hookTargetDir)) {
    throw "Git hooks directory not found: $hookTargetDir"
}

Copy-Item -Path $hookSource -Destination $hookTarget -Force
Write-Host "Installed post-commit hook at: $hookTarget"
