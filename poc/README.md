# Protótipo mínimo da captura de impressão (tarefa #4)

Prova que um trabalho de impressão enviado a uma impressora do Windows chega até um
processo Python — sem monitor de porta nativo, sem RedMon, sem instalar nada além do
Windows em si. Ver a decisão de arquitetura completa na
[issue #3](https://github.com/BrunodosSantosVaz/print-route/issues/3#user-content-riscos-e-depend%C3%AAncias)
("Riscos e dependências").

**Isto não é o PrintRoute ainda.** É só a menor prova possível de que a ideia funciona,
para o dono rodar num Windows de verdade antes do resto do épico avançar. Fica fora de
`src/` de propósito (não muda o programa, não gera versão).

## Como funciona

1. Uma **Porta Local** (recurso já embutido no Windows — `Add-PrinterPort`, sem instalar
   nada) aponta para um arquivo fixo em vez de uma porta física (LPT1, USB etc.).
2. Uma impressora de teste usa essa porta com o driver **"Generic / Text Only"** (também
   já vem no Windows).
3. Quando você imprime nela, o Windows escreve os bytes do trabalho nesse arquivo.
4. Um script Python (`capturar_e_encaminhar.py`) observa o arquivo e, quando detecta que
   o trabalho terminou de ser escrito, lê os bytes — isso é o "trabalho chegou até o
   Python" que a tarefa #4 precisa provar.

Nenhuma DLL nativa, nenhum monitor de porta customizado, nada fora do que o Windows já
traz. `pywin32` nem é necessário para esta prova mínima — só biblioteca padrão do Python.

## Passo a passo

**1. Criar a porta e a impressora de teste** (PowerShell **como Administrador**):

```powershell
cd caminho\para\print-route\poc
.\preparar_porta_teste.ps1
```

**2. Rodar o observador** (outro terminal, não precisa ser Administrador):

```powershell
python capturar_e_encaminhar.py C:\PrintRouteTeste\trabalho.out
```

**3. Imprimir um teste**: abra o Bloco de Notas, escreva algumas linhas, **Arquivo →
Imprimir**, escolha a impressora **"PrintRoute POC"**.

**4. Ver o resultado** no terminal do Python: deve aparecer algo como

```
[14:32:07] Trabalho #1 capturado: 118 bytes -> trabalho-20260929-143207-1.bin
  Primeiros bytes (como texto): 'Isto é um teste do PrintRoute...\r\n\x0c'
```

Os trabalhos capturados também ficam salvos em `C:\PrintRouteTeste\capturas\`, um arquivo
por impressão, para conferir depois.

**5. Repetir** imprimindo 2-3 vezes seguidas (inclusive rápido, quase junto) para ver se
o script separa os trabalhos corretamente, sem misturar bytes de um trabalho com o
outro.

**6. Limpar** quando terminar (PowerShell como Administrador):

```powershell
.\remover_porta_teste.ps1
```

## O que reportar de volta

Para a tarefa #4 ser considerada validada, preciso saber:

- [ ] O terminal do Python mostrou os trabalhos chegando, com o texto certo?
- [ ] Imprimir várias vezes seguidas funcionou sem misturar/perder trabalhos?
- [ ] Algum erro ao rodar `preparar_porta_teste.ps1` (ex.: precisa de outro driver, a
      porta não pôde ser criada, algo pediu permissão extra)?
- [ ] Alguma trava de segurança do Windows (SmartScreen, antivírus, UAC) apareceu em
      algum passo?

Cole a saída do terminal (ou uma captura de tela) na issue #4. Com isso validado, a
tarefa 2 (registrar o PrintRoute como impressora de verdade) já pode usar o mesmo
princípio de porta, só trocando "Generic / Text Only" pelo fluxo real de captura +
Ghostscript + reenvio.

## Limitações conhecidas desta prova mínima (de propósito)

- Driver **"Generic / Text Only"**: qualquer coisa que não seja texto simples (uma
  imagem, um PDF do navegador) vai sair como lixo/texto convertido. Não importa aqui —
  só estamos provando que os bytes chegam, não que eles fazem sentido. A tarefa 3
  (encaminhar para uma impressora real) é quem decide o driver/pipeline de verdade
  (Ghostscript, provavelmente).
- Detecção de "trabalho terminou" por **heurística de tempo** (o arquivo parou de
  crescer por 1 segundo): funciona bem para um teste manual, mas não é a técnica final
  — a tarefa 2/3 deve usar a notificação de verdade do spooler
  (`FindFirstPrinterChangeNotification`, via `pywin32`) em vez de ficar checando o
  tamanho do arquivo.
- A porta é um **arquivo único e fixo**: dois trabalhos verdadeiramente simultâneos
  (não apenas em sequência rápida) poderiam colidir. Vale testar (passo 5), mas o
  comportamento definitivo do spooler nisso só se confirma na prática.
