"""Ponto de entrada do PrintRoute (Tkinter).

Ainda não há funcionalidade real: este é o esqueleto que a esteira usa para compilar, testar e lintar
o projeto antes do primeiro épico (a arquitetura de como interceptar a impressão no Windows) ser
decidido e implementado. Veja AGENTS.md."""
import tkinter as tk
from tkinter import ttk

from printroute.version import __version__

TITULO_APP = f"PrintRoute v{__version__}"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(TITULO_APP)
        self.geometry("480x260")
        self.minsize(360, 200)
        corpo = ttk.Frame(self, padding=24)
        corpo.pack(fill="both", expand=True)
        ttk.Label(corpo, text=TITULO_APP, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(
            corpo,
            text="Em desenvolvimento: ainda não reencaminha impressões.\n"
                 "Veja o progresso em github.com/BrunodosSantosVaz/print-route",
            justify="left",
        ).pack(anchor="w", pady=(12, 0))


def main():
    App().mainloop()


if __name__ == "__main__":
    main()
