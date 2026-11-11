param([Parameter(Mandatory=$true)][string]$RequestPath)
$ErrorActionPreference = 'Stop'
$request = Get-Content -LiteralPath $RequestPath -Raw -Encoding UTF8 | ConvertFrom-Json
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $voices = @($synth.GetInstalledVoices() | Where-Object {
        $_.Enabled -and $_.VoiceInfo.Culture.Name -eq 'en-US'
    })
    if ($voices.Count -eq 0) { throw 'No American English desktop voice is installed.' }
    $voice = $voices[0].VoiceInfo.Name
    $synth.SelectVoice($voice)
    $synth.Rate = 0
    $synth.SetOutputToWaveFile([string]$request.output_path)
    $timer = [System.Diagnostics.Stopwatch]::StartNew()
    # Speak treats text as plain text, not SSML or executable PowerShell.
    $synth.Speak([string]$request.text)
    $timer.Stop()
    $synth.SetOutputToNull()
    @{voice = $voice; synthesis_ms = $timer.Elapsed.TotalMilliseconds} | ConvertTo-Json -Compress
} finally {
    $synth.Dispose()
}
