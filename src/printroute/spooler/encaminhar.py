"""Captura o trabalho de impressão enviado à impressora PrintRoute e o encaminha, sem
nenhum processamento, para uma impressora de destino real. "Caminho mais simples" da
tarefa #6: uma impressora fixa, uma cópia, sem rasterização -- o Ghostscript (para
quando o driver da impressora de destino for diferente do de origem) fica para uma
tarefa futura, ver AGENTS.md, "Arquitetura de captura de impressão".

A captura observa a pasta de spool do próprio Windows, a mesma técnica (heurística de
"arquivo parou de crescer") já validada no protótipo da tarefa #4 (poc/), agora
apontada para a pasta de verdade do spooler em vez de uma porta própria. **Não** usa
`FindFirstPrinterChangeNotification`: essa função **não é exposta pelo pywin32**
(confirmado no código-fonte de `win32print.cpp` -- só há `OpenPrinter`, `EnumJobs`,
`GetJob`, `StartDocPrinter`, `WritePrinter` etc., nada de notificação de mudança), e
reescrevê-la via `ctypes` seria mais um componente arriscado sem necessidade, já que
observar a pasta já funciona.

Requer conseguir ler `C:\\Windows\\System32\\spool\\PRINTERS\\` (normalmente só
administradores conseguem) -- o instalador (tarefa #11) provavelmente vai precisar
rodar o PrintRoute elevado por causa disso.
"""
import pathlib
import time

import win32print

PASTA_SPOOL = pathlib.Path(r"C:\Windows\System32\spool\PRINTERS")
INTERVALO_DE_VERIFICACAO = 0.05  # segundos entre cada checagem da pasta/arquivo
PERIODO_DE_ESTABILIDADE = 0.3  # segundos sem o arquivo crescer para considerar o trabalho concluído


def _arquivos_spl() -> set[pathlib.Path]:
    # *.SPL (o trabalho já spoolado) e *.TMP (achado na prática, via CI: o processador de
    # impressão parece escrever num .TMP intermediário antes -- ou às vezes em vez -- de um
    # .SPL; observar só *.SPL perdia trabalhos que completam rápido demais). Nunca .SHD: é
    # metadado do trabalho (pequeno, estabiliza na hora), não o conteúdo.
    try:
        return set(PASTA_SPOOL.glob("*.SPL")) | set(PASTA_SPOOL.glob("*.TMP"))
    except OSError:
        return set()


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


def aguardar_trabalho(tempo_limite_s: float = 30.0) -> bytes | None:
    """Bloqueia até um novo arquivo .SPL aparecer na pasta de spool do Windows (um
    trabalho novo, de qualquer impressora do sistema) e devolve os bytes dele assim que
    ele parar de crescer. Devolve None se o tempo limite passar sem nenhum trabalho
    novo, ou se o trabalho for concluído rápido demais para ler."""
    inicio = time.monotonic()
    existentes = _arquivos_spl()
    while time.monotonic() - inicio < tempo_limite_s:
        novos = _arquivos_spl() - existentes
        if novos:
            return _ler_quando_estavel(next(iter(novos)), tempo_limite_s=10.0)
        time.sleep(INTERVALO_DE_VERIFICACAO)
    return None


def encaminhar_bytes(nome_impressora_destino: str, dados: bytes, nome_trabalho: str = "PrintRoute") -> None:
    """Envia os bytes brutos para a impressora de destino, sem nenhum processamento."""
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
