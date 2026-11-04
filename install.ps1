$ErrorActionPreference = 'Stop'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python 3.9+ must be installed and on PATH.' }
$tempDir = Join-Path ([IO.Path]::GetTempPath()) ('nexen-' + [guid]::NewGuid())
New-Item -ItemType Directory -Force $tempDir | Out-Null
try {
  $script = Join-Path $tempDir 'install.py'
  Invoke-WebRequest 'https://raw.githubusercontent.com/aswartzlander2-sys/nexen/main/install.py' -OutFile $script
  & python $script
  if ($LASTEXITCODE -ne 0) { throw 'Nexen installation failed.' }
  $bin = Join-Path $env:LOCALAPPDATA 'Nexen\bin'
  $path = [Environment]::GetEnvironmentVariable('Path','User')
  if (-not $path) { $path = '' }
  if (($path -split ';') -notcontains $bin) { [Environment]::SetEnvironmentVariable('Path', ($path.TrimEnd(';') + ';' + $bin).TrimStart(';'), 'User') }
  $env:Path += ';' + $bin
} finally { Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue }
