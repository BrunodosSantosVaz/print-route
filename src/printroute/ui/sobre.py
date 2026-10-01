"""Janela "Sobre o PrintRoute" (tarefa #40) -- a tela de verdade, em Tkinter, seguindo
o mesmo estilo de `configuracoes.py`/`seletor.py`. Antes era só uma notificação de
balão (`icone.notify`, em `bandeja.py`); virou uma janela porque uma notificação some
sozinha e não dá pra copiar a versão/link dela. Sem teste automatizado (interface
gráfica, precisa de um display)."""
import tkinter as tk
import webbrowser
from tkinter import ttk

from printroute.version import __version__

_URL_DO_REPOSITORIO = "https://github.com/BrunodosSantosVaz/print-route"


def abrir_sobre() -> None:
    """Abre a janela "Sobre"; bloqueia até ela ser fechada."""
    janela = tk.Tk()
    janela.title("Sobre o PrintRoute")
    janela.resizable(False, False)

    corpo = ttk.Frame(janela, padding=24)
    corpo.pack(fill="both", expand=True)

    ttk.Label(corpo, text="PrintRoute", font=("Segoe UI", 16, "bold")).pack(anchor="w")
    ttk.Label(corpo, text=f"Versão {__version__}").pack(anchor="w", pady=(2, 12))
    ttk.Label(
        corpo,
        text="Impressora virtual que reencaminha a impressão recebida\npara uma ou mais impressoras reais.",
        justify="left",
    ).pack(anchor="w")

    link = ttk.Label(corpo, text=_URL_DO_REPOSITORIO, foreground="#0F6CBD", cursor="hand2")
    link.pack(anchor="w", pady=(12, 0))
    link.bind("<Button-1>", lambda _evento: webbrowser.open(_URL_DO_REPOSITORIO))

    ttk.Label(corpo, text="Licença AGPL-3.0-or-later. Sem garantia.", foreground="gray").pack(
        anchor="w", pady=(12, 16)
    )

    ttk.Button(corpo, text="Fechar", command=janela.destroy).pack(anchor="e")

    janela.protocol("WM_DELETE_WINDOW", janela.destroy)
    janela.mainloop()
