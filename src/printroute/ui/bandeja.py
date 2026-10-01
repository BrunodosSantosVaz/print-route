"""Ícone na bandeja do sistema (tarefa #10), com o menu de contexto que dá acesso às
configurações -- protótipo validado na issue #3 (artboard "Bandeja"). Usa `pystray`:
mais simples e confiável do que reimplementar `Shell_NotifyIcon` (e o laço de mensagens
de janela que ele exige) na mão. Sem teste automatizado (interface gráfica/bandeja,
precisa de um ambiente de desktop real) -- as camadas de lógica que ele usa
(`estado.py`, `configuracao.py`) são testadas separadamente.

Bug real (achado testando o instalador de verdade): "Abrir configurações" chamava
`abrir_configuracoes()` (Tkinter, `tk.Tk()` + `mainloop()`) direto daqui -- mas este
menu roda na thread própria do `pystray` (`run_detached()`), não na principal. Tkinter
não é thread-safe; criar uma segunda janela Tk fora da thread principal deixava a
bandeja abrindo a janela várias vezes e corrompia o Tcl/Tk do processo a ponto do
seletor (que abre na thread principal, ver __main__.py) parar de funcionar. Por isso
"Abrir configurações" agora só *pede* (callback `ao_abrir_configuracoes`, chamado sem
argumentos): quem de fato abre a janela é sempre a thread principal. "Sobre o
PrintRoute" (tarefa #40) segue a mesma regra, com `ao_abrir_sobre`: antes chamava
`icone.notify` (só uma notificação de balão, sem risco de thread porque não é Tkinter),
mas virou uma janela de verdade (`ui/sobre.py`), então também precisa passar pela
thread principal."""
import pystray

from printroute.estado import EstadoApp
from printroute.ui.icone import desenhar_icone


def criar_icone(
    estado: EstadoApp, ao_sair=lambda: None, ao_abrir_configuracoes=lambda: None, ao_abrir_sobre=lambda: None
) -> pystray.Icon:
    """`ao_sair` é chamado (sem argumentos) quando o usuário escolhe "Sair", além de
    `icone.stop()` -- usado pelo `__main__.py` de verdade para também parar o laço de
    observação da impressora, que roda numa thread separada da bandeja.

    `ao_abrir_configuracoes`/`ao_abrir_sobre` são chamados (sem argumentos) ao escolher
    o item correspondente: só *sinalizam* o pedido (ex.: numa fila) -- quem abre a
    janela de verdade é sempre a thread principal (ver módulo, acima)."""

    def _abrir_configuracoes(icone, item):
        ao_abrir_configuracoes()

    def _alternar_reencaminhamento(icone, item):
        estado.alternar()
        icone.update_menu()

    def _texto_reencaminhamento(item):
        return "Reencaminhamento: Ativado" if estado.ativo else "Reencaminhamento: Pausado"

    def _sobre(icone, item):
        ao_abrir_sobre()

    def _sair(icone, item):
        ao_sair()
        icone.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Abrir configurações", _abrir_configuracoes, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_texto_reencaminhamento, _alternar_reencaminhamento, checked=lambda item: estado.ativo),
        pystray.MenuItem("Sobre o PrintRoute", _sobre),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", _sair),
    )
    return pystray.Icon("PrintRoute", icon=desenhar_icone(64), title="PrintRoute", menu=menu)


def executar() -> None:
    """Ponto de entrada: cria e roda o ícone da bandeja (bloqueia até "Sair")."""
    criar_icone(EstadoApp()).run()
