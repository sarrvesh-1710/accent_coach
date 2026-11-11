# Optional Windows-only regeneration of synthetic listening examples.
# These assets are for playback only and are never passed to the scorer.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$projectRoot = Split-Path -Parent $PSScriptRoot
$exampleFolder = Join-Path $projectRoot 'web_assets/examples'
New-Item -ItemType Directory -Path $exampleFolder -Force | Out-Null
$prompts = Get-Content -LiteralPath (Join-Path $projectRoot 'prompts.json') -Raw -Encoding UTF8 | ConvertFrom-Json
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $speaker.SelectVoice('Microsoft Zira Desktop')
    $speaker.Rate = -1
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(16000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $manifest = @()
    foreach ($prompt in $prompts) {
        if ($prompt.id -notmatch '^[a-z0-9_]+$') { throw 'Unsafe prompt ID' }
        $destination = Join-Path $exampleFolder ($prompt.id + '.wav')
        $speaker.SetOutputToWaveFile($destination, $format)
        $speaker.Speak($prompt.text)
        $speaker.SetOutputToNull()
        $manifest += @{id=$prompt.id; text=$prompt.text; file=($prompt.id + '.wav'); voice=$speaker.Voice.Name; language='en-US'; synthetic=$true; used_for_scoring=$false}
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $exampleFolder 'manifest.json') -Encoding UTF8
} finally { $speaker.Dispose() }
Write-Output "Created $($manifest.Count) synthetic listening examples in $exampleFolder"
