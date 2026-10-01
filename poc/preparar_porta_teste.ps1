<#
Cria a porta e a impressora de teste do protótipo da tarefa #4 (ver poc/README.md).
Usa só recursos já embutidos no Windows: nenhum programa externo é instalado.
Rode como Administrador.
#>

$ErrorActionPreference = 'Stop'

$pasta = 'C:\PrintRouteTeste'
$arquivo = Join-Path $pasta 'trabalho.out'
$nomeImpressora = 'PrintRoute POC'

New-Item -ItemType Directory -Path $pasta -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $pasta 'capturas') -Force | Out-Null

if (-not (Get-PrinterPort -Name $arquivo -ErrorAction SilentlyContinue)) {
    Add-PrinterPort -Name $arquivo
    Write-Host "Porta criada: $arquivo"
} else {
    Write-Host "Porta ja existia: $arquivo"
}

if (-not (Get-Printer -Name $nomeImpressora -ErrorAction SilentlyContinue)) {
    Add-Printer -Name $nomeImpressora -DriverName 'Generic / Text Only' -PortName $arquivo
    Write-Host "Impressora criada: $nomeImpressora"
} else {
    Write-Host "Impressora ja existia: $nomeImpressora"
}

Write-Host ""
Write-Host "Pronto. Proximos passos (veja poc/README.md):"
Write-Host "  1. python capturar_e_encaminhar.py `"$arquivo`""
Write-Host "  2. Bloco de Notas > escrever algo > Arquivo > Imprimir > `"$nomeImpressora`""
