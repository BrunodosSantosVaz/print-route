"""Ícone na bandeja do sistema (tarefa #10), com o menu de contexto que dá acesso às
configurações -- protótipo validado na issue #3 (artboard "Bandeja"). Usa `pystray`:
mais simples e confiável do que reimplementar `Shell_NotifyIcon` (e o laço de mensagens
de janela que ele exige) na mão. Sem teste automatizado (interface gráfica/bandeja,
precisa de um ambiente de desktop real) -- as camadas de lógica que ele usa
(`estado.py`, `configuracao.py`) são testadas separadamente."""
import pystray
from PIL import Image, ImageDraw

from printroute.configuracao import carregar
from printroute.estado import EstadoApp
from printroute.ui.configuracoes import abrir_configuracoes

_COR_DE_FUNDO = (15, 108, 189, 255)  # o mesmo azul do protótipo de telas (issue #3)


def _icone_padrao() -> Image.Image:
    tamanho = 64
    imagem = Image.new("RGBA", (tamanho, tamanho), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)
    desenho.ellipse((4, 4, tamanho - 4, tamanho - 4), fill=_COR_DE_FUNDO)
    desenho.text((tamanho // 2 - 4, tamanho // 2 - 8), "P", fill="white")
    return imagem


def criar_icone(estado: EstadoApp) -> pystray.Icon:
    def _abrir_configuracoes(icone, item):
        abrir_configuracoes(carregar())

    def _alternar_reencaminhamento(icone, item):
        estado.alternar()
        icone.update_menu()

    def _texto_reencaminhamento(item):
        return "Reencaminhamento: Ativado" if estado.ativo else "Reencaminhamento: Pausado"

    def _sobre(icone, item):
        icone.notify(
            "Impressora virtual que reencaminha para uma ou mais impressoras reais.\n"
            "github.com/BrunodosSantosVaz/print-route",
            "Sobre o PrintRoute",
        )

    def _sair(icone, item):
        icone.stop()

    menu = pystray.Menu(
        pystray.MenuItem("Abrir configurações", _abrir_configuracoes, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem(_texto_reencaminhamento, _alternar_reencaminhamento, checked=lambda item: estado.ativo),
        pystray.MenuItem("Sobre o PrintRoute", _sobre),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", _sair),
    )
    return pystray.Icon("PrintRoute", icon=_icone_padrao(), title="PrintRoute", menu=menu)


def executar() -> None:
    """Ponto de entrada: cria e roda o ícone da bandeja (bloqueia até "Sair")."""
    criar_icone(EstadoApp()).run()
