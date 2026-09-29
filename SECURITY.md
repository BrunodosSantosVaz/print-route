# Política de segurança

## Versões que recebem correção

Somente a **versão mais recente** publicada em [Releases](https://github.com/BrunodosSantosVaz/print-route/releases).
Ainda não há nenhuma release publicada.

## Como relatar uma vulnerabilidade

**Não abra uma issue pública.** Use o relato privado do GitHub:
[Security > Report a vulnerability](https://github.com/BrunodosSantosVaz/print-route/security/advisories/new).

Inclua, se puder: a versão do PrintRoute, o que acontece, os passos para reproduzir e o impacto. A
resposta inicial costuma sair em até 7 dias (projeto mantido em tempo parcial, sem SLA).

## O que é considerado vulnerabilidade

O PrintRoute é diferente de um programa só de leitura local: ele se registra como impressora e precisa
falar com o **spooler de impressão do Windows** (portas, impressoras, drivers, trabalhos de impressão de
outros processos). Essa é a superfície que mais importa aqui. Interessam relatos como:

- um documento ou trabalho de impressão malformado que cause execução de código, travamento sério ou
  consumo excessivo de recursos ao ser processado;
- vazamento do conteúdo de uma impressão para um destino não configurado, ou para outro usuário/processo
  do sistema;
- elevação de privilégio através do componente que fala com o spooler (porta, monitor ou serviço);
- configuração de impressoras/portas gravada de forma insegura (ex.: credenciais em texto puro quando
  não deveriam estar);
- o executável publicado não corresponder ao código-fonte, ou ter sido adulterado;
- dependências do processo de build com falhas conhecidas que afetem o executável gerado.

Como o projeto ainda está no início e não tem funcionalidade real de reencaminhamento (veja o
[README](README.md#estado-atual)), esta seção será revisada conforme a arquitetura for implementada.

## Conferindo o executável

Quando houver uma release publicada:

- Compare o **SHA-256** do `.exe` com o `SHA256SUMS.txt` da release
  (`Get-FileHash .\PrintRoute-vX.Y.Z-windows-x64.exe -Algorithm SHA256`).
- Executáveis gerados pelo CI (release candidata `-rc.N` e produção, que é o mesmo binário da candidata
  aprovada) têm **atestado de procedência**:
  `gh attestation verify PrintRoute-vX.Y.Z-windows-x64.exe --repo BrunodosSantosVaz/print-route`.
- O `.exe` **não é assinado digitalmente**, então o Windows SmartScreen pode avisar. Se preferir,
  compile a partir do código-fonte (veja o [README](README.md)).
