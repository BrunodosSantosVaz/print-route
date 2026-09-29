## O que mudou
<!-- Resumo em poucas linhas. -->

## Issue
Refs #
<!-- Use "Refs #n" (nao "Closes"): as issues fecham sozinhas quando a versao e publicada em producao.
     Excecao: hotfix -> main pode usar "Closes #n". No PR de release, um "Refs #n" por tarefa. -->

## Como testar
1.

## Testes automatizados
- Gate local: `python -m unittest discover -s tests` — resultado e nº de testes:
- Testes novos/alterados:
- [ ] Para bug: teste de regressão que falhava antes da correção

## Impacto
- Muda o executável ou o build (PyInstaller, versão)?
- Muda a interação com o spooler de impressão do Windows (portas, impressoras, drivers)? O que foi testado manualmente?
- Muda algo que o usuário configura (impressoras pré-configuradas, seletor)? README/telas atualizados?

## Checklist
- [ ] Definition of Done atendida
- [ ] README/CHANGELOG atualizados quando aplicável
- [ ] Sem dados reais de terceiros (nome de impressora/rede que identifique alguém) em código, testes ou capturas de tela
