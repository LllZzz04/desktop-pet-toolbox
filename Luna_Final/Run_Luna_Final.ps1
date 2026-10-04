param([switch]$Editor, [string]$GodotPath)
$ErrorActionPreference = 'Stop'
$taskEngine = $GodotPath
if (-not $taskEngine) { $taskEngine = Join-Path $PSScriptRoot 'tools\godot\Godot_v4.7.2-stable_win64.exe' }
if (-not (Test-Path -LiteralPath $taskEngine -PathType Leaf)) { throw 'Godot executable missing. Keep the complete extracted folder or provide -GodotPath.' }
if (-not $Editor) {
    $taskImport = Start-Process -FilePath $taskEngine -ArgumentList @('--headless','--audio-driver','Dummy','--editor','--import','--quit','--path',('"'+$PSScriptRoot+'"')) -WindowStyle Hidden -PassThru -Wait
    if ($taskImport.ExitCode -ne 0) { throw 'Resource import failed. Run with -Editor for details.' }
}
$taskArguments = @('--path',('"'+$PSScriptRoot+'"'))
if ($Editor) { $taskArguments += '--editor' }
Start-Process -FilePath $taskEngine -ArgumentList $taskArguments
