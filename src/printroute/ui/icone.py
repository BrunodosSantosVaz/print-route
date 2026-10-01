"""Desenho do ícone do PrintRoute (tarefa #40): um só lugar, reaproveitado pelo ícone
da bandeja (`bandeja.py`, em tempo de execução) e pelo gerador do `.ico` do `.exe`
(`packaging/windows/gerar_icone.py`, rodado uma vez, no desenvolvimento) -- garante que
os dois sejam sempre o mesmo desenho, sem duplicar a lógica.

Desenhado numa resolução bem maior que o pedido e reduzido no final (supersampling):
sem isso, as bordas arredondadas saem serrilhadas. O desenho em si é propositalmente
simples (só duas formas brancas sólidas -- papel e corpo da impressora, sem linhas
finas internas) porque o ícone da bandeja normalmente aparece a 16px, onde qualquer
detalhe fino vira borrão -- confirmado desenhando e comparando os tamanhos de verdade
antes de decidir a versão final."""
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
