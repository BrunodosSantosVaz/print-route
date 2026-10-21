"""Gera packaging/windows/icon.ico (tarefa #40) a partir do mesmo desenho usado pelo
ícone da bandeja (src/printroute/ui/icone.py) -- garante que o ícone do .exe e o da
bandeja sejam sempre o mesmo desenho, em vez de dois arquivos mantidos à mão.

Roda uma vez (ou de novo, se o desenho mudar); o .ico gerado é commitado no repositório
como um recurso estático -- build_exe.py só o referencia (--icon), não o gera a cada
build.

    python packaging/windows/gerar_icone.py
"""
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(RAIZ, "src"))
from printroute.ui.icone import desenhar_icone  # noqa: E402

DESTINO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
TAMANHOS = (16, 32, 48, 64, 128, 256)


def main() -> None:
    desenhar_icone(256).save(DESTINO, sizes=[(t, t) for t in TAMANHOS])
    print(f"OK: {os.path.relpath(DESTINO, RAIZ)}")


if __name__ == "__main__":
    main()
