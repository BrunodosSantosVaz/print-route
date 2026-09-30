"""Ponto de entrada do PrintRoute: garante a impressora instalada, mostra o ícone na
bandeja (em segundo plano, via pystray) e observa a fila da impressora no laço
principal. O laço de observação fica na thread principal porque é ele quem abre o
seletor (Tkinter) no modo "perguntar", e Tkinter não é confiável fora da thread
principal -- ainda não testado numa sessão de desktop de verdade (ver AGENTS.md).

Com o argumento `--desinstalar` (usado pelo desinstalador do instalador, tarefa #11,
antes de apagar os arquivos): só remove a impressora e a entrada de início automático,
sem abrir a bandeja nem o laço de observação."""
import sys
import threading

from printroute import inicializacao
from printroute.configuracao import MODO_FIXO, carregar
from printroute.estado import EstadoApp
from printroute.spooler import encaminhar, gerenciar
from printroute.ui import bandeja
from printroute.ui.seletor import abrir_seletor

_parar = threading.Event()


def _desinstalar() -> None:
    gerenciar.desinstalar()
    inicializacao.desabilitar()


def _observar_e_encaminhar(estado: EstadoApp) -> None:
    while not _parar.is_set():
        dados = encaminhar.aguardar_trabalho(gerenciar.NOME_IMPRESSORA, tempo_limite_s=5.0)
        if dados is None or not estado.ativo:
            continue
        config = carregar()
        if config.modo == MODO_FIXO:
            encaminhar.encaminhar_para_configuracao(dados, config)
        else:
            escolha = abrir_seletor(config)
            if escolha is not None:
                encaminhar.encaminhar_escolha(dados, escolha)


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--desinstalar":
        _desinstalar()
        return
    gerenciar.instalar()
    estado = EstadoApp()
    icone = bandeja.criar_icone(estado, ao_sair=_parar.set)
    icone.run_detached()
    try:
        _observar_e_encaminhar(estado)
    finally:
        icone.stop()


if __name__ == "__main__":
    main()
