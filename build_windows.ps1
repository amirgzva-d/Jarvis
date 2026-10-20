# Run in Windows PowerShell from the Jarvis project directory.
# Generates an independent Jarvis.exe. Optionally packages NSIS Setup.exe.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
py -3 -m pip install --upgrade pyinstaller 'edge-tts>=7.2.0,<8'
if ($LASTEXITCODE -ne 0) { throw 'Python dependencies installation failed.' }
py -3 -m PyInstaller --noconfirm --clean --onefile --windowed --name Jarvis --icon assets\jarvis.ico --add-data 'web;web' --add-data 'notes;notes' --collect-all edge_tts --hidden-import=edge_tts start_jarvis.py
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
Write-Host 'Portable executable: dist\Jarvis.exe'
$nsis = Get-Command makensis.exe -ErrorAction SilentlyContinue
if (-not $nsis) {
  $candidate = Join-Path ${env:ProgramFiles(x86)} 'NSIS\makensis.exe'
  if (Test-Path $candidate) { $nsis = @{ Source = $candidate } }
}
if ($nsis) { Push-Location (Join-Path $PSScriptRoot 'packaging'); try { & $nsis.Source 'Jarvis.nsi'; if ($LASTEXITCODE -ne 0) {throw 'NSIS installer generation failed.'} } finally { Pop-Location } }
else { Write-Host 'NSIS not installed: use portable dist\Jarvis.exe or install NSIS then rerun to build Setup.exe.' }
