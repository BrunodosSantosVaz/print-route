<#
Remove a impressora, a porta e a pasta de teste criadas por preparar_porta_teste.ps1.
Rode como Administrador.
#>

$ErrorActionPreference = 'Stop'

$pasta = 'C:\PrintRouteTeste'
$arquivo = Join-Path $pasta 'trabalho.out'
$nomeImpressora = 'PrintRoute POC'

Remove-Printer -Name $nomeImpressora -ErrorAction SilentlyContinue
Remove-PrinterPort -Name $arquivo -ErrorAction SilentlyContinue
Remove-Item -Path $pasta -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "Impressora '$nomeImpressora', porta e pasta de teste removidas."
