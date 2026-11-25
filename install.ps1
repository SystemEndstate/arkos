# Instalador da ARKOS em uma linha:
#   irm https://raw.githubusercontent.com/<org>/arkos/main/install.ps1 | iex
# Baixa (git clone, ou zip se não houver git) para ~/.arkos/app, pede a chave, configura a base e as atualizações,
# põe `arkos` no PATH do usuário e sincroniza as skills. Chave VIP baixa também o pacote VIP do servidor da base.
# Variáveis opcionais: ARKOS_ORG, ARKOS_BASE_URL, ARKOS_CHAVE (sem perguntar), ARKOS_APP (pasta de instalação).
$ErrorActionPreference = 'Stop'
$Org = if ($env:ARKOS_ORG) { $env:ARKOS_ORG } else { 'SystemEndstate' }
if ($Org -match '[<>]') { throw "Defina a organização do GitHub: `$env:ARKOS_ORG = 'nome-da-org' e rode de novo." }
$Repo = "https://github.com/$Org/arkos"
$Raw = "https://raw.githubusercontent.com/$Org/arkos/main"
$Zip = "https://codeload.github.com/$Org/arkos/zip/refs/heads/main"
$Base = if ($env:ARKOS_BASE_URL) { $env:ARKOS_BASE_URL } else { '' }

foreach ($req in 'node', 'claude') {
  if (-not (Get-Command $req -ErrorAction SilentlyContinue)) { throw "Falta '$req' no PATH. Instale antes de continuar." }
}
if ([int]((node -v).TrimStart('v').Split('.')[0]) -lt 18) { throw "Node 18+ necessário (achei $(node -v))." }

$casa = Join-Path $HOME '.arkos'
$app = if ($env:ARKOS_APP) { $env:ARKOS_APP } else { Join-Path $casa 'app' }
New-Item -ItemType Directory -Force $casa | Out-Null

# 1. código: clone/pull com git; sem git, zip do main
if (Test-Path (Join-Path $app '.git')) {
  git -C $app pull --ff-only --quiet
} elseif (Get-Command git -ErrorAction SilentlyContinue) {
  if (Test-Path $app) { Remove-Item -Recurse -Force $app }
  git clone --depth 1 --quiet $Repo $app
} else {
  $tmp = Join-Path ([IO.Path]::GetTempPath()) ("arkos-" + [guid]::NewGuid().ToString('n'))
  New-Item -ItemType Directory -Force $tmp | Out-Null
  Invoke-WebRequest $Zip -OutFile (Join-Path $tmp 'arkos.zip') -UseBasicParsing
  Expand-Archive (Join-Path $tmp 'arkos.zip') -DestinationPath $tmp -Force
  $src = Get-ChildItem $tmp -Directory | Select-Object -First 1
  if (Test-Path $app) { Remove-Item -Recurse -Force $app }
  Move-Item $src.FullName $app
  Remove-Item -Recurse -Force $tmp
}
Push-Location $app
try { npm install --omit=dev --no-fund --no-audit --silent | Out-Null } finally { Pop-Location }

# 2. chave (licença ARK1): guardada só em ~/.arkos/licenca.txt
$lic = Join-Path $casa 'licenca.txt'
$chave = $env:ARKOS_CHAVE
if (-not $chave -and -not (Test-Path $lic)) { $chave = Read-Host 'Cole a sua chave ARKOS (ARK1...)' }
if ($chave) {
  $chave = $chave.Trim()
  if ($chave -notmatch '^ARK1\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$') { throw 'Chave em formato inválido (esperado ARK1.xxx.yyy).' }
  Set-Content $lic $chave -Encoding ascii -NoNewline
}
if (-not $Base) { $Base = Read-Host 'Endereço da base ARKOS (Enter = sem base por enquanto)' }

# 3. config: base, origem das atualizações (GitHub), auto-atualização ligada
$cfg = Join-Path $casa 'config.json'
$j = if (Test-Path $cfg) { Get-Content $cfg -Raw | ConvertFrom-Json } else { [pscustomobject]@{ prestador = $env:USERNAME } }
$j | Add-Member -NotePropertyName base -NotePropertyValue ([pscustomobject]@{ url = $Base; mcpConfig = $null }) -Force
$j | Add-Member -NotePropertyName atualizacao -NotePropertyValue ([pscustomobject]@{ fonte = "$Raw/versao.json"; zip = $Zip; auto = $true }) -Force
$j | ConvertTo-Json -Depth 10 | Set-Content $cfg -Encoding utf8

# 4. PATH do usuário
$bin = Join-Path $app 'bin'
$userPath = [Environment]::GetEnvironmentVariable('Path', 'User')
$parts = @($userPath -split ';' | Where-Object { $_ })
if ($parts -notcontains $bin) { [Environment]::SetEnvironmentVariable('Path', (($parts + $bin) -join ';'), 'User') }
$env:Path = "$env:Path;$bin"

# 5. casa + skills (VIP: o sync puxa o pacote VIP do servidor da base com a chave)
$arkos = Join-Path $app 'arkos.mjs'
if (-not $j.casa) { node $arkos setup }
node $arkos skills sync
if ($LASTEXITCODE -ne 0) { Write-Host 'ATENCAO: pacote de skills incompleto (veja acima). Rode de novo: arkos skills sync' -ForegroundColor Red; exit 1 }
Write-Host 'Pronto. Abra um terminal novo e rode: arkos'
