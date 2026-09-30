"""Captura o trabalho de impressão enviado à impressora PrintRoute e o encaminha para
uma impressora de destino real, reconstruindo-o pelo driver dela própria (via
Ghostscript/XPS) quando o trabalho capturado for um pacote XPS -- ver
`encaminhar_bytes`, tarefa #34 -- em vez do "caminho mais simples" original da tarefa
#6 (bytes brutos, sem nenhum processamento), que corrompia qualquer documento real
quando a impressora de destino precisava processar o conteúdo de verdade.

A captura confirma o trabalho novo pela fila da própria impressora (`EnumJobs`) e só
então lê o arquivo correspondente na pasta de spool do Windows -- a mesma heurística de
"arquivo parou de crescer" já validada no protótipo da tarefa #4 (poc/), agora apontada
para a pasta de verdade do spooler em vez de uma porta própria. A confirmação por
`EnumJobs` é necessária: a pasta de spool é compartilhada por todas as impressoras do
sistema, e observar só "apareceu um arquivo novo" confunde atividade de outra
impressora (ou do próprio Windows) com um trabalho nosso -- foi exatamente isso que
aconteceu na CI (um PrintTicket XML de outra origem apareceu no meio do teste). **Não**
usa `FindFirstPrinterChangeNotification`: essa função **não é exposta pelo pywin32**
(confirmado no código-fonte de `win32print.cpp` -- só há `OpenPrinter`, `EnumJobs`,
`GetJob`, `StartDocPrinter`, `WritePrinter` etc., nada de notificação de mudança), e
reescrevê-la via `ctypes` seria mais um componente arriscado sem necessidade.

Requer conseguir ler `C:\\Windows\\System32\\spool\\PRINTERS\\`: confirmado com
`icacls` que o grupo Usuários só tem permissão de **escrita** ali (submeter um
trabalho), nunca de leitura do conteúdo -- só SYSTEM/Administradores (token elevado)
leem. Sem elevação, `_arquivos_spl()` engole o erro de permissão como pasta vazia
(nenhuma exceção) e a captura nunca encontra nada, silenciosamente -- bug real,
achado testando de verdade (tarefa #30), corrigido fazendo o `.exe` pedir elevação
sozinho (`--uac-admin` no PyInstaller, `packaging/windows/build_exe.py`).

`win32print` é importado dentro de `_encaminhar_raw`, não no topo do arquivo: assim o
módulo inteiro (inclusive `encaminhar_para_configuracao`, que só orquestra chamadas)
importa em qualquer sistema, e os testes que usam mock em vez de uma impressora de
verdade rodam também no Linux da CI, sem precisar do runner Windows.
"""
import os
import pathlib
import subprocess
import tempfile
import time

from printroute.configuracao import Configuracao
from printroute.selecao import EscolhaDoUsuario

PASTA_SPOOL = pathlib.Path(r"C:\Windows\System32\spool\PRINTERS")
INTERVALO_DE_VERIFICACAO = 0.05  # segundos entre cada checagem da pasta/arquivo
PERIODO_DE_ESTABILIDADE = 0.3  # segundos sem o arquivo crescer para considerar o trabalho concluído
_ASSINATURA_ZIP = b"PK\x03\x04"  # início de todo pacote XPS (é um ZIP por baixo)


def _arquivos_spl() -> set[pathlib.Path]:
    # *.SPL (o trabalho já spoolado) e *.TMP (achado na prática, via CI: o processador de
    # impressão parece escrever num .TMP intermediário antes -- ou às vezes em vez -- de um
    # .SPL; observar só *.SPL perdia trabalhos que completam rápido demais). Nunca .SHD: é
    # metadado do trabalho (pequeno, estabiliza na hora), não o conteúdo.
    try:
        return set(PASTA_SPOOL.glob("*.SPL")) | set(PASTA_SPOOL.glob("*.TMP"))
    except OSError:
        return set()


def _estado_dos_arquivos() -> dict[pathlib.Path, tuple[float, int]]:
    # (mtime, tamanho) de cada arquivo candidato -- não só "quais existem". Achado na
    # CI: com o driver "Microsoft Print To PDF", o Windows reaproveita o MESMO nome de
    # arquivo ("FP00000.SPL") para cada trabalho, em vez de um nome novo por trabalho;
    # só olhar "apareceu um caminho novo" perdia esses trabalhos por inteiro.
    estado = {}
    for arquivo in _arquivos_spl():
        try:
            info = arquivo.stat()
        except OSError:
            continue
        estado[arquivo] = (info.st_mtime, info.st_size)
    return estado


def _ler_quando_estavel(arquivo: pathlib.Path, tempo_limite_s: float) -> bytes | None:
    inicio = time.monotonic()
    tamanho_anterior = -1
    estavel_desde = None
    while time.monotonic() - inicio < tempo_limite_s:
        try:
            tamanho_atual = arquivo.stat().st_size
        except OSError:
            return None  # o spooler já apagou o arquivo (trabalho concluído rápido demais)
        # Só considera "estável" com tamanho > 0: o arquivo é criado (0 bytes) antes dos
        # dados serem escritos -- sem esta guarda, um 0 que "não muda" por
        # PERIODO_DE_ESTABILIDADE é lido como um trabalho vazio (bug real, achado pela CI).
        if tamanho_atual > 0:
            if tamanho_atual == tamanho_anterior:
                if estavel_desde is None:
                    estavel_desde = time.monotonic()
                elif time.monotonic() - estavel_desde >= PERIODO_DE_ESTABILIDADE:
                    try:
                        return arquivo.read_bytes()
                    except OSError:
                        return None
            else:
                estavel_desde = None
            tamanho_anterior = tamanho_atual
        time.sleep(INTERVALO_DE_VERIFICACAO)
    return None


def _ids_dos_trabalhos(nome_impressora: str) -> set[int]:
    import win32print

    hprinter = win32print.OpenPrinter(nome_impressora)
    try:
        return {trabalho["JobId"] for trabalho in win32print.EnumJobs(hprinter, 0, 999)}
    finally:
        win32print.ClosePrinter(hprinter)


def aguardar_trabalho(nome_impressora: str, tempo_limite_s: float = 30.0) -> bytes | None:
    """Bloqueia até um trabalho novo aparecer na fila **desta impressora** (confirmado
    por `EnumJobs`) e devolve os bytes dele assim que o arquivo correspondente parar de
    crescer. Devolve None se o tempo limite passar sem nenhum trabalho novo, ou se ele
    completar rápido demais para ler.

    Confirmar por `EnumJobs` (não só "apareceu um arquivo novo na pasta de spool") é
    necessário: a pasta é compartilhada por todas as impressoras do sistema, e
    atividade alheia (achado na prática, via CI: o próprio Windows gera um PrintTicket
    XML às vezes) seria confundida com um trabalho nosso. E o candidato certo pode ser
    um arquivo já existente sendo REESCRITO, não só um caminho novo (ver
    `_estado_dos_arquivos`) -- por isso a comparação é por (mtime, tamanho), não só por
    quais caminhos existem."""
    inicio = time.monotonic()
    ids_existentes = _ids_dos_trabalhos(nome_impressora)
    estado_existente = _estado_dos_arquivos()
    while time.monotonic() - inicio < tempo_limite_s:
        if _ids_dos_trabalhos(nome_impressora) - ids_existentes:
            # Trabalho confirmado na fila: o arquivo pode levar um instante a mais para
            # refletir a mudança, então dá uma folga curta específica para isso antes de
            # desistir.
            fim_da_espera = time.monotonic() + 3.0
            while time.monotonic() < fim_da_espera:
                estado_atual = _estado_dos_arquivos()
                candidatos = [
                    arquivo for arquivo, info in estado_atual.items() if estado_existente.get(arquivo) != info
                ]
                if candidatos:
                    return _ler_quando_estavel(candidatos[0], tempo_limite_s=10.0)
                time.sleep(INTERVALO_DE_VERIFICACAO)
            return None  # o trabalho foi confirmado, mas nenhum arquivo mudou a tempo
        estado_existente.update(_estado_dos_arquivos())  # nunca esquece mudança alheia já vista
        time.sleep(INTERVALO_DE_VERIFICACAO)
    return None


def _e_xps(dados: bytes) -> bool:
    """O driver "Microsoft Print To PDF" (e outros drivers v4, baseados no pipeline
    XPS do Windows) spoola um **pacote XPS** (ZIP, com FixedDocumentSequence, páginas,
    fontes) em vez de bytes brutos de dispositivo -- descoberto ao vivo (tarefa #34).
    Mandar esse pacote como RAW pra outra impressora não funciona: nem o
    `System.Windows.Xps.Packaging.XpsDocument` do .NET nem o processador de impressão
    nativo do Windows (`MS_XPS_PROC`, erro 0x80004005 confirmado no log de eventos do
    spooler) conseguem reprocessá-lo fora do contexto original -- só o Ghostscript
    (`ghostxps`) lê corretamente. Só o driver "Generic / Text Only" (v3 clássico,
    primeiro candidato em `gerenciar.CANDIDATOS_DE_DRIVER`) ainda produz texto puro de
    verdade, que `_encaminhar_raw` continua atendendo."""
    return dados[:4] == _ASSINATURA_ZIP


def _localizar_gxps() -> str:
    """Caminho do `gxpswin64.exe` (Ghostscript/`ghostxps` -- o interpretador de XPS;
    **não** é o `gs`/`gswin64c.exe` principal, que não lê XPS sozinho): embutido pelo
    instalador em `<pasta do .exe>/ghostxps/` (ver `instalador.iss`). A variável de
    ambiente `PRINTROUTE_GXPS` sobrescreve -- só para desenvolvimento/testes, rodando
    do código-fonte sem precisar compilar o instalador primeiro."""
    de_ambiente = os.environ.get("PRINTROUTE_GXPS")
    if de_ambiente:
        return de_ambiente
    import sys

    return os.path.join(os.path.dirname(sys.executable), "ghostxps", "gxpswin64.exe")


TEMPO_LIMITE_GHOSTSCRIPT_S = 60.0  # ver _encaminhar_xps: nunca travar o laço pra sempre


def _encaminhar_xps(nome_impressora_destino: str, dados: bytes) -> None:
    """Reconstrói o trabalho (pacote XPS) na impressora de destino, pelo driver dela
    própria, via Ghostscript -- não por um pass-through cego de bytes. É a
    "Conversão: Ghostscript" que a arquitetura original já previa (AGENTS.md),
    confirmada ao vivo: renderiza igual ao documento original e o job chega certo na
    fila de destino (`-sDEVICE=mswinpr2`, saída direta pra uma impressora pelo nome).

    `timeout`: uma impressora de destino que precise de interação (ex.: "Microsoft
    Print to PDF" perguntando onde salvar) não trava numa caixa de diálogo visível
    aqui -- ela só nunca completa. Sem limite, esse UM trabalho travaria o laço de
    captura inteiro para sempre; com o limite, `subprocess.TimeoutExpired` é só mais
    uma exceção que `_observar_e_encaminhar` já registra e segue (tarefa #28).

    `creationflags=CREATE_NO_WINDOW`: bug real, achado ao vivo (tarefa #36) -- o
    `gxpswin64.exe` é um programa de linha de comando; sem isso, abre a própria janela
    de console na tela a cada trabalho, mesmo o PrintRoute sendo `--windowed` (isso só
    evita o PrintRoute ter console próprio, não os filhos que ele lança). Só existe no
    Windows (`getattr` com 0 como padrão: não quebra a importação do módulo em
    nenhum outro sistema, ex.: os testes que rodam na CI em Linux)."""
    with tempfile.NamedTemporaryFile(suffix=".xps", delete=False) as tmp:
        tmp.write(dados)
        caminho_tmp = tmp.name
    try:
        subprocess.run(
            [
                _localizar_gxps(), "-dBATCH", "-dNOPAUSE", "-dQUIET",
                "-sDEVICE=mswinpr2", f"-sOutputFile=%printer%{nome_impressora_destino}",
                caminho_tmp,
            ],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            check=True, capture_output=True, text=True, timeout=TEMPO_LIMITE_GHOSTSCRIPT_S,
        )
    finally:
        os.remove(caminho_tmp)


def _encaminhar_raw(nome_impressora_destino: str, dados: bytes, nome_trabalho: str) -> None:
    """Envia os bytes brutos para a impressora de destino, sem nenhum processamento --
    só correto quando origem e destino falam o mesmo formato (texto puro; ver
    `_e_xps`)."""
    import win32print

    hprinter = win32print.OpenPrinter(nome_impressora_destino)
    try:
        win32print.StartDocPrinter(hprinter, 1, (nome_trabalho, None, "RAW"))
        try:
            win32print.StartPagePrinter(hprinter)
            try:
                win32print.WritePrinter(hprinter, dados)
            finally:
                win32print.EndPagePrinter(hprinter)
        finally:
            win32print.EndDocPrinter(hprinter)
    finally:
        win32print.ClosePrinter(hprinter)


def encaminhar_bytes(nome_impressora_destino: str, dados: bytes, nome_trabalho: str = "PrintRoute") -> None:
    """Encaminha o trabalho capturado para a impressora de destino: reconstrói pelo
    driver dela própria (Ghostscript) quando é um pacote XPS -- a maioria dos casos
    reais, ver `_e_xps` -- ou copia os bytes brutos quando é texto puro de verdade."""
    if _e_xps(dados):
        _encaminhar_xps(nome_impressora_destino, dados)
    else:
        _encaminhar_raw(nome_impressora_destino, dados, nome_trabalho)


def encaminhar_para_configuracao(dados: bytes, config: Configuracao) -> None:
    """Encaminha os bytes capturados para cada impressora do modo fixo (`config.impressoras`),
    respeitando a quantidade de cópias de cada uma -- tarefa #8. Não se aplica ao modo
    "perguntar" (o destino ali vem do seletor: ver `encaminhar_escolha`, tarefa #9)."""
    for destino in config.impressoras:
        for _ in range(destino.copias):
            encaminhar_bytes(destino.nome, dados)


def encaminhar_escolha(dados: bytes, escolha: EscolhaDoUsuario) -> None:
    """Encaminha os bytes capturados para a impressora escolhida no seletor (modo
    "perguntar"), pelo número de cópias que o usuário pediu ali -- tarefa #9."""
    for _ in range(escolha.copias):
        encaminhar_bytes(escolha.impressora, dados)
