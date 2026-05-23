# Launch the FoundationDesignJm desktop app from PowerShell.
# Usage: right-click -> "Run with PowerShell"  OR  .\launch_desktop.ps1
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
python -m foundationdesignjm.desktop
