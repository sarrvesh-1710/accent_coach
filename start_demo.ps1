param([int]$Port = 7861, [switch]$NoBrowser, [switch]$Demo)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (!(Test-Path -LiteralPath $python)) { throw 'Main environment missing. Follow docs/COMBINED_DEMO.md setup.' }
if (!$env:ACCENT_COACH_GENERATION_BACKEND) { $env:ACCENT_COACH_GENERATION_BACKEND = 'kokoro' }
if ($env:ACCENT_COACH_GENERATION_BACKEND -eq 'kokoro') {
    $voicePython = if ($env:ACCENT_COACH_KOKORO_PYTHON) { $env:ACCENT_COACH_KOKORO_PYTHON } else { Join-Path $PSScriptRoot 'voice_generation\.venv\Scripts\python.exe' }
    if (!(Test-Path -LiteralPath $voicePython)) { throw 'Kokoro environment missing. Follow voice_generation/KOKORO_RUNBOOK.md.' }
    if (!(Test-Path -LiteralPath (Join-Path $PSScriptRoot 'models\kokoro\manifest.json'))) { throw 'Kokoro weights missing. Run the documented one-time model setup.' }
}
$env:GRADIO_SERVER_PORT = "$Port"
$env:ACCENT_COACH_OPEN_BROWSER = if ($NoBrowser) { '0' } else { '1' }
if ($Demo -and !$PSBoundParameters.ContainsKey('Port')) { $Port = 7864 }
Write-Host "Accent Coach demo: http://127.0.0.1:$Port/"
if ($Demo) { Write-Host 'Sample history is stored separately in runs/profile_demo. Use Ctrl+C to stop.' } else { Write-Host 'Use Ctrl+C to stop. Accounts and recordings stay in private_data.' }
if ($Demo) {
    $demoArguments = @('tools/run_profile_demo.py', '--port', "$Port")
    if ($NoBrowser) { $demoArguments += '--no-browser' }
    & $python @demoArguments
} else {
    & $python site_server.py
}
exit $LASTEXITCODE
