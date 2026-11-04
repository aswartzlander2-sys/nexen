$ErrorActionPreference = 'Stop'
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw 'Python 3.9+ must be installed and on PATH.' }
$base = Join-Path $env:LOCALAPPDATA 'Nexen\app'
$bin = Join-Path $env:LOCALAPPDATA 'Nexen\bin'
$tempDir = Join-Path ([IO.Path]::GetTempPath()) ('nexen-' + [guid]::NewGuid())
New-Item -ItemType Directory -Force $tempDir,$bin | Out-Null
try {
  $archive = Join-Path $tempDir 'nexen.zip'
  Invoke-WebRequest 'https://github.com/aswartzlander2-sys/nexen/archive/refs/heads/main.zip' -OutFile $archive
  Expand-Archive $archive -DestinationPath $tempDir
  if (Test-Path $base) { Remove-Item -Recurse -Force $base }
  Move-Item (Join-Path $tempDir 'nexen-main') $base
  $script = '@echo off' + "`r`n" + 'python "' + (Join-Path $base 'nexen.py') + '" %*' + "`r`n"
  [IO.File]::WriteAllText((Join-Path $bin 'nexen.cmd'), $script)
  $path = [Environment]::GetEnvironmentVariable('Path','User')
  if (($path -split ';') -notcontains $bin) { [Environment]::SetEnvironmentVariable('Path', ($path.TrimEnd(';') + ';' + $bin), 'User') }
  $env:Path += ';' + $bin
  Write-Host 'Installed. Open a new terminal and run: nexen start'
} finally { Remove-Item -Recurse -Force $tempDir -ErrorAction SilentlyContinue }
