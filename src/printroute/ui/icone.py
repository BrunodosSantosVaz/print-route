"""Desenho do ícone do PrintRoute (tarefa #40): um só lugar, reaproveitado pelo ícone
da bandeja (`bandeja.py`, em tempo de execução), pelas janelas Tkinter (`aplicar_icone`,
abaixo -- tarefa #43) e pelo gerador do `.ico` do `.exe`
(`packaging/windows/gerar_icone.py`, rodado uma vez, no desenvolvimento) -- garante que
todos sejam sempre o mesmo desenho, sem duplicar a lógica.

Desenhado numa resolução bem maior que o pedido e reduzido no final (supersampling):
sem isso, as bordas arredondadas saem serrilhadas. O desenho em si é propositalmente
simples (só duas formas brancas sólidas -- papel e corpo da impressora, sem linhas
finas internas) porque o ícone da bandeja normalmente aparece a 16px, onde qualquer
detalhe fino vira borrão -- confirmado desenhando e comparando os tamanhos de verdade
antes de decidir a versão final."""
import os

from PIL import Image, ImageDraw

COR_DE_FUNDO = (15, 108, 189, 255)  # o mesmo azul do protótipo de telas (issue #3)
_COR_DO_GLIFO = (255, 255, 255, 255)
_SUPERSAMPLING = 8


def desenhar_icone(tamanho: int) -> Image.Image:
    """Devolve uma imagem RGBA quadrada (`tamanho` x `tamanho`): o selo azul
    arredondado com o glifo de impressora, no mesmo estilo do protótipo (issue #3)."""
    s = tamanho * _SUPERSAMPLING
    imagem = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    desenho = ImageDraw.Draw(imagem)

    desenho.rounded_rectangle((0, 0, s - 1, s - 1), radius=int(s * 0.22), fill=COR_DE_FUNDO)

    cx = s / 2
    corpo_w, corpo_h, corpo_topo = s * 0.56, s * 0.26, s * 0.50
    desenho.rounded_rectangle(
        (cx - corpo_w / 2, corpo_topo, cx + corpo_w / 2, corpo_topo + corpo_h),
        radius=s * 0.05, fill=_COR_DO_GLIFO,
    )

    papel_w, papel_h, papel_topo = s * 0.36, s * 0.32, s * 0.18
    desenho.rounded_rectangle(
        (cx - papel_w / 2, papel_topo, cx + papel_w / 2, papel_topo + papel_h),
        radius=s * 0.02, fill=_COR_DO_GLIFO,
    )

    bandeja_w, bandeja_h = s * 0.44, s * 0.09
    bandeja_topo = corpo_topo + corpo_h - s * 0.015
    desenho.rounded_rectangle(
        (cx - bandeja_w / 2, bandeja_topo, cx + bandeja_w / 2, bandeja_topo + bandeja_h),
        radius=s * 0.015, fill=_COR_DO_GLIFO,
    )

    return imagem.resize((tamanho, tamanho), Image.LANCZOS)


def aplicar_icone(janela) -> None:
    """Aplica o ícone do PrintRoute numa janela Tkinter (título, Alt+Tab e barra de
    tarefas enquanto ela estiver aberta) -- sem isso, a janela usa o ícone padrão do
    Tcl/Tk (bug real, achado ao vivo em produção: "o ícone da barra de tarefa, com ele
    aberto, ainda é o antigo").

    Duas partes, as duas achadas ao vivo testando o `.exe` de verdade já publicado
    (2ª volta nesta mesma tarefa #43):

    1. `iconbitmap` (não `iconphoto`: por baixo, no Windows, os dois só mexem no
       ícone da *classe* da janela -- `GCLP_HICON`, o que o título e o Alt+Tab usam;
       `iconbitmap` foi escolhido por não precisar guardar referência nenhuma pra
       evitar coleta de lixo, ao contrário do `PhotoImage` do `iconphoto`).
    2. `WM_SETICON` de verdade via Win32 (`win32gui`, pywin32 já é dependência do
       projeto), em cima disso -- sem essa parte, a barra de tarefas do Windows
       continua com o ícone genérico: ela cacheia o ícone do botão quando a janela é
       criada (antes desta função rodar) e só reconsulta de novo ao receber
       `WM_SETICON`; só trocar `GCLP_HICON` não dispara esse recálculo.

    O `.ico` de verdade é gerado num arquivo temporário a partir do mesmíssimo
    `desenhar_icone` usado pela bandeja e pelo `.exe` -- ambas as partes usam ele
    (`iconbitmap` lê o arquivo; o `LoadImage` do Win32 também)."""
    import ctypes
    import tempfile

    import win32con
    import win32gui

    with tempfile.NamedTemporaryFile(suffix=".ico", delete=False) as arquivo_temp:
        caminho = arquivo_temp.name
    try:
        desenhar_icone(256).save(caminho, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
        janela.iconbitmap(default=caminho)

        user32 = ctypes.windll.user32
        # Sem isso, o ctypes trata HWND/HICON como 32 bits em Python 64-bit.
        user32.GetAncestor.restype = ctypes.c_void_p
        user32.GetAncestor.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        GA_ROOT = 2
        hwnd = user32.GetAncestor(janela.winfo_id(), GA_ROOT)

        flags = win32con.LR_LOADFROMFILE
        hicon_grande = win32gui.LoadImage(0, caminho, win32con.IMAGE_ICON, 32, 32, flags)
        hicon_pequeno = win32gui.LoadImage(0, caminho, win32con.IMAGE_ICON, 16, 16, flags)
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_BIG, hicon_grande)
        win32gui.SendMessage(hwnd, win32con.WM_SETICON, win32con.ICON_SMALL, hicon_pequeno)
    finally:
        # O Tk (iconbitmap) e o LoadImage já carregaram o ícone pra memória: o
        # arquivo temporário não precisa sobreviver.
        os.remove(caminho)
