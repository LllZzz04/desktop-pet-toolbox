param([string]$GodotPath, [string]$PythonPath, [switch]$RenderPreviews)
$ErrorActionPreference = 'Stop'
$taskEngine = $GodotPath
if (-not $taskEngine) { $taskEngine = Join-Path $PSScriptRoot 'tools\godot\Godot_v4.7.2-stable_win64_console.exe' }
if (-not (Test-Path -LiteralPath $taskEngine -PathType Leaf)) { throw 'Godot executable missing.' }
Push-Location -LiteralPath $PSScriptRoot
try {
    & $taskEngine --headless --audio-driver Dummy --editor --import --path $PSScriptRoot --quit
    if ($LASTEXITCODE -ne 0) { throw 'Resource import failed.' }
    foreach ($taskTest in @('leg_guard_crouch_checks','success_v2_checks','click_cover_checks','working_panel_order_checks','blink_compatibility')) {
        & $taskEngine --headless --audio-driver Dummy --path $PSScriptRoot --script ('res://tests/'+$taskTest+'.gd')
        if ($LASTEXITCODE -ne 0) { throw ('Test failed: '+$taskTest) }
    }
    foreach ($taskStage in @('A','B','C','D','E','F')) {
        & $taskEngine --headless --audio-driver Dummy --path $PSScriptRoot --script res://tests/phase_checks.gd -- $taskStage
        if ($LASTEXITCODE -ne 0) { throw ('State regression failed: '+$taskStage) }
    }
    if ($RenderPreviews) {
        foreach ($taskCapture in @('render_approved_poses','render_final_showcase')) {
            $taskRender = Start-Process -FilePath $taskEngine -ArgumentList @('--path',('"'+$PSScriptRoot+'"'),'--audio-driver','Dummy','--script',('res://tests/'+$taskCapture+'.gd')) -WindowStyle Hidden -PassThru -Wait
            if ($taskRender.ExitCode -ne 0) { throw ('GPU capture failed: '+$taskCapture) }
        }
        if (-not $PythonPath) { throw 'Export needs -PythonPath with Pillow and NumPy.' }
        & $PythonPath tools/export_final_previews.py
        if ($LASTEXITCODE -ne 0) { throw 'Preview export failed. For MP4, also provide a reachable ffmpeg.' }
    }
    if ($PythonPath) {
        & $PythonPath tools/validate_final.py
        if ($LASTEXITCODE -ne 0) { throw 'Final integrity validation failed.' }
    }
} finally { Pop-Location }
