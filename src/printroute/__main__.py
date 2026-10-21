"""Ponto de entrada do PrintRoute: garante a impressora instalada, mostra o ícone na
bandeja (em segundo plano, via pystray) e observa a fila da impressora no laço
principal. O laço de observação fica na thread principal porque é ele quem abre
janelas Tkinter (o seletor, no modo "perguntar", as configurações e o "Sobre"), e
Tkinter não é thread-safe -- criar uma janela fora da thread principal (bug real,
achado testando o instalador de verdade: a bandeja abria "Configurações" na própria
thread do pystray) deixava a bandeja abrindo janela repetida e quebrava até o seletor.
Por isso a bandeja (`ui/bandeja.py`) só *sinaliza* os pedidos de abrir janela -- por
uma fila -- e quem abre de verdade é sempre este laço.

Com o argumento `--desinstalar` (usado pelo desinstalador do instalador, tarefa #11,
antes de apagar os arquivos): só remove a impressora e a entrada de início automático,
sem abrir a bandeja nem o laço de observação."""
import datetime
import queue
import sys
import threading
import time
import traceback

from printroute import inicializacao
from printroute.configuracao import CAMINHO_PADRAO, MODO_FIXO, carregar
from printroute.estado import EstadoApp
from printroute.spooler import encaminhar, gerenciar
from printroute.ui import bandeja
from printroute.ui.configuracoes import abrir_configuracoes
from printroute.ui.seletor import abrir_seletor
from printroute.ui.sobre import abrir_sobre

_parar = threading.Event()
_pedidos_de_ui: queue.Queue = queue.Queue()
CAMINHO_LOG_ERROS = CAMINHO_PADRAO.parent / "erro.log"
PAUSA_APOS_ERRO_S = 1.0  # ver _observar_e_encaminhar: evita laço apertado se o erro persistir


def _desinstalar() -> None:
    gerenciar.desinstalar()
    inicializacao.desabilitar()


def _registrar_erro(origem: str) -> None:
    """Guarda o traceback (mesma pasta da configuração) e deixa o laço seguir rodando.

    Bug real, achado ao vivo: um `config.json` inválido (ou qualquer outro erro
    inesperado num trabalho) derrubava **o processo inteiro** sem deixar nenhum
    vestígio -- o `.exe` é `--windowed`, sem console, então uma exceção não aparece em
    lugar nenhum. Um trabalho ou uma configuração ruim não pode tirar o PrintRoute do
    ar; só esse trabalho é perdido, registrado aqui para investigar depois."""
    try:
        CAMINHO_LOG_ERROS.parent.mkdir(parents=True, exist_ok=True)
        with open(CAMINHO_LOG_ERROS, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now().isoformat()} [{origem}]\n{traceback.format_exc()}\n")
    except OSError:
        pass  # sem lugar pra registrar -- mas isso também não pode derrubar o laço


def _pedidos_de_ui_pendentes() -> set:
    """Esvazia a fila e devolve quais pedidos distintos havia (ex.: {"configuracoes"},
    {"sobre"}) -- mais de um clique no mesmo item enquanto o laço está ocupado (ex.:
    aguardando um trabalho) vira um só pedido, não um por clique."""
    pedidos = set()
    while True:
        try:
            pedidos.add(_pedidos_de_ui.get_nowait())
        except queue.Empty:
            return pedidos


def _observar_e_encaminhar(estado: EstadoApp) -> None:
    while not _parar.is_set():
        try:
            dados = encaminhar.aguardar_trabalho(gerenciar.NOME_IMPRESSORA, tempo_limite_s=5.0)
            pedidos = _pedidos_de_ui_pendentes()
            if "configuracoes" in pedidos:
                abrir_configuracoes(carregar())
            if "sobre" in pedidos:
                abrir_sobre()
            if dados is None or not estado.ativo:
                continue
            config = carregar()
            if config.modo == MODO_FIXO:
                encaminhar.encaminhar_para_configuracao(dados, config)
            else:
                escolha = abrir_seletor(config)
                if escolha is not None:
                    encaminhar.encaminhar_escolha(dados, escolha)
        except Exception:
            # Achado ao vivo: sem a pausa, um erro que se repete a cada volta (ex.: a
            # impressora ainda não existe bem no instante em que o laço começa a rodar)
            # martela o disco e enche o erro.log em segundos -- a pausa dá tempo da
            # causa (quase sempre transitória) se resolver sozinha antes da próxima
            # tentativa.
            _registrar_erro("observar_e_encaminhar")
            time.sleep(PAUSA_APOS_ERRO_S)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--desinstalar":
        _desinstalar()
        return
    try:
        gerenciar.instalar()
    except Exception:
        # Bug real, achado ao vivo em produção (tarefa #43): uma falha aqui (ex.: uma
        # condição de corrida externa ao spooler, já corrigida na origem, mas o
        # princípio vale pra qualquer outra) derrubava o app INTEIRO antes até da
        # bandeja aparecer -- sem vestígio nenhum (--windowed, sem console). Registra e
        # segue: o laço principal (já protegido, tarefa #28) continua tentando a cada
        # trabalho, e o usuário ainda consegue abrir a bandeja/configurações nesse
        # meio tempo, em vez do processo simplesmente não abrir.
        _registrar_erro("instalar")
    estado = EstadoApp()
    icone = bandeja.criar_icone(
        estado,
        ao_sair=_parar.set,
        ao_abrir_configuracoes=lambda: _pedidos_de_ui.put_nowait("configuracoes"),
        ao_abrir_sobre=lambda: _pedidos_de_ui.put_nowait("sobre"),
    )
    icone.run_detached()
    try:
        _observar_e_encaminhar(estado)
    finally:
        icone.stop()


if __name__ == "__main__":
    main()
