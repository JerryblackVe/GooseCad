# Build/installation experiment inside the ephemeral runner only.
# Do not publish or upload a binary until the distribution license gate is resolved.
$ErrorActionPreference = 'Stop'
if (-not $env:RUNNER_TEMP) { throw 'This experiment is CI-only' }
$root = Join-Path $env:RUNNER_TEMP 'GooseCAD package test'
New-Item -ItemType Directory -Path $root | Out-Null
$dist = Join-Path $root 'dist'
$work = Join-Path $root 'work'
$report = Join-Path $root 'report'
New-Item -ItemType Directory -Path $report | Out-Null
function CheckExit($step) { if ($LASTEXITCODE -ne 0) { throw "$step failed: $LASTEXITCODE" } }
python -m goosecad.ui --self-test
CheckExit 'Source runtime test'
python -m PyInstaller --noconfirm --clean --onedir --console --noupx --name GooseCAD --distpath $dist --workpath $work --specpath $work --collect-all OCP packaging/launcher.py
CheckExit 'Freeze'
$bundle = Join-Path $dist 'GooseCAD'
python packaging/prepare_installer.py $bundle $report
CheckExit 'Bundle inventory'
$inventory = Get-Content (Join-Path $report 'bundle-inventory.json') -Raw | ConvertFrom-Json
$bytes = ($inventory | Measure-Object -Property bytes -Sum).Sum
Write-Host "Bundle baseline bytes: 762263751; candidate: $bytes; measured on separate runner, not bitwise reproducibility" 
Copy-Item (Join-Path $work 'GooseCAD\warn-GooseCAD.txt') (Join-Path $report 'freeze-warnings.txt')
$exe = Join-Path $bundle 'GooseCAD.exe'
& $exe --self-test
CheckExit 'Frozen runtime test'
$nsis = Join-Path ${env:ProgramFiles(x86)} 'NSIS\makensis.exe'
if (-not (Test-Path $nsis)) { throw 'NSIS runner compiler missing' }
& $nsis /VERSION
CheckExit 'NSIS version'
$installer = Join-Path $root 'GooseCAD-experimental-setup.exe'
$uninstall = Join-Path $report 'uninstall-files.nsh'
& $nsis /V3 "/DBUNDLE=$bundle" "/DUNINSTALL_LIST=$uninstall" "/DOUTPUT=$installer" packaging/goosecad.nsi
CheckExit 'Installer compilation'
$installPath = Join-Path $root 'installed application'
# /D must be last and NSIS expects an unquoted path including spaces.
$process = Start-Process -FilePath $installer -ArgumentList "/S /D=$installPath" -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Installer exit: $($process.ExitCode)" }
$installed = Join-Path $installPath 'GooseCAD.exe'
if (-not (Test-Path $installed)) { throw 'Installation missing executable' }
& $installed --self-test
CheckExit 'Installed runtime test'
# Uninstaller must not delete unknown user files even in installation folder.
$sentinel = Join-Path $installPath 'user-document.gcad'
Set-Content -LiteralPath $sentinel -Value 'preserve-user-file'
$uninstaller = Join-Path $installPath 'Uninstall.exe'
$process = Start-Process -FilePath $uninstaller -ArgumentList "/S _?=$installPath" -Wait -PassThru
if ($process.ExitCode -ne 0) { throw "Uninstaller exit: $($process.ExitCode)" }
if (Test-Path $installed) { throw 'Uninstaller left executable' }
if ((Get-Content -LiteralPath $sentinel -Raw).Trim() -ne 'preserve-user-file') { throw 'Uninstaller damaged sentinel' }
Write-Host 'Experimental install / runtime / uninstall verified; user file preserved.'
Get-FileHash -Algorithm SHA256 $installer | Format-List
# Only a textual inventory is retained. No installer, bundle or binary artifact upload.
Copy-Item (Join-Path $report 'dependency-inventory.json') packaging-dependency-inventory.json
Copy-Item (Join-Path $report 'bundle-inventory.json') packaging-bundle-inventory.json
Copy-Item (Join-Path $report 'freeze-warnings.txt') packaging-freeze-warnings.txt
