param([string]$RepositoryName = 'hue-task-mcp')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($RepositoryName -notmatch '^[a-zA-Z0-9_.-]+$') { throw 'Invalid repository name' }

# Ask the same Git credential helper used by ordinary git pull / git push.
# Credentials stay in memory and are never printed or written into this repo.
$credentialLines = "protocol=https`nhost=github.com`nusername=schris88`n`n" | git credential fill
if ($LASTEXITCODE -ne 0) { throw 'Git credential helper failed. Run this in your normal authenticated terminal.' }
$credential = @{}
foreach ($line in $credentialLines) {
    $parts = $line -split '=', 2
    if ($parts.Count -eq 2) { $credential[$parts[0]] = $parts[1] }
}
if (-not $credential.password) { throw 'No GitHub credential returned by Git.' }
$headers = @{ Authorization = "Bearer $($credential.password)"; 'User-Agent' = 'hue-task-mcp'; Accept = 'application/vnd.github+json' }
try {
    $profile = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $headers
    $repoUrl = "https://api.github.com/repos/$($profile.login)/$RepositoryName"
    $repo = $null
    try { $repo = Invoke-RestMethod -Uri $repoUrl -Headers $headers }
    catch { if ([int]$_.Exception.Response.StatusCode -ne 404) { throw } }
    if ($repo) {
        if (-not $repo.private) { throw 'Existing repository is public. Refusing to push.' }
    } else {
        $body = @{ name = $RepositoryName; private = $true; description = 'Subtle Hue MCP indicators: gentle blue color blends for done, red blends for questions.' } | ConvertTo-Json
        $repo = Invoke-RestMethod -Method Post -Uri 'https://api.github.com/user/repos' -Headers $headers -ContentType 'application/json' -Body $body
    }
    if (-not $repo.private) { throw 'Private repository verification failed.' }
    if (-not (Test-Path -LiteralPath '.git')) { git init -b main; if ($LASTEXITCODE -ne 0) { throw 'git init failed' } }
    $trackedSecrets = git ls-files -- '*.local.json' '.env'
    if ($trackedSecrets) { throw 'A local credentials file is tracked. Refusing to publish.' }
    git add -- .github .gitignore pyproject.toml README.md hue_task_mcp tests examples Publish-PrivateRepo.ps1
    if ($LASTEXITCODE -ne 0) { throw 'git add failed' }
    git diff --cached --quiet
    if ($LASTEXITCODE -eq 1) { git commit -m 'Add tested Hue MCP task indicators'; if ($LASTEXITCODE -ne 0) { throw 'git commit failed' } }
    $remotes = @(git remote)
    if ($remotes -contains 'origin') {
        $origin = git remote get-url origin
        if ($origin -ne $repo.clone_url) { throw "Existing origin differs from destination: $origin" }
    } else { git remote add origin $repo.clone_url }
    git push -u origin main
    if ($LASTEXITCODE -ne 0) { throw 'git push failed; no force push was attempted.' }
    $check = Invoke-RestMethod -Uri $repoUrl -Headers $headers
    if (-not $check.private) { throw 'Final privacy check failed' }
    Write-Host "Created and pushed PRIVATE repository: $($check.html_url)"
} finally {
    $credential.Clear()
    $headers.Clear()
    $credentialLines = $null
}
