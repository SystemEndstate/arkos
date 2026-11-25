#!/usr/bin/env pwsh
# Shim do comando `arkos` para PowerShell (evita o "Terminate batch job?" do .cmd no Ctrl+C).
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
& node (Join-Path $PSScriptRoot '..\arkos.mjs') @args
exit $LASTEXITCODE
