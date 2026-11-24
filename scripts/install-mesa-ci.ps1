# CI-only, process-local software renderer. No system-wide installation.
$ErrorActionPreference = 'Stop'
$root = Join-Path $env:RUNNER_TEMP 'goosecad-mesa-25.3.5'
if (Test-Path $root) { throw "Unexpected existing Mesa directory" }
New-Item -ItemType Directory -Path $root | Out-Null
$archive = Join-Path $root 'mesa.7z'
$url = 'https://github.com/pal1000/mesa-dist-win/releases/download/25.3.5/mesa3d-25.3.5-release-msvc.7z'
$expected = '066f64549ac122bfad4d68c2c4ec9b0018d025a1af7fa61654d3ccbc5e933388'
Invoke-WebRequest -Uri $url -OutFile $archive
$actual = (Get-FileHash -Path $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw "Mesa archive digest mismatch: $actual" }
& 7z x $archive "-o$root" -y
if ($LASTEXITCODE -ne 0) { throw "Mesa extraction failed" }
$gl = @(Get-ChildItem $root -Recurse -File -Filter opengl32.dll | Where-Object { $_.Directory.Name -eq 'x64' })
if ($gl.Count -ne 1) { throw "Expected exactly one x64 Mesa WGL runtime" }
$dllDir = $gl[0].Directory.FullName
if (-not (Test-Path (Join-Path $dllDir 'libgallium_wgl.dll'))) { throw "Missing Gallium WGL driver" }
"GOOSECAD_MESA_DLL_DIR=$dllDir" | Out-File -FilePath $env:GITHUB_ENV -Encoding utf8 -Append
Write-Host "Verified Mesa SHA256: $actual; x64 directory: $dllDir"
