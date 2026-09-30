"""Diálogo do seletor de impressora na hora (tarefa #9) -- a tela de verdade, em
Tkinter, seguindo o protótipo validado (issue #3, artboard "SeletorNaHora"). Usa a
lógica de `printroute.selecao`, que é testada separadamente: este módulo **não tem
teste automatizado** (é interface gráfica, precisa de um display) -- só o
`python -m compileall` confere a sintaxe."""
import tkinter as tk
from tkinter import ttk

from printroute.configuracao import Configuracao
from printroute.selecao import EscolhaDoUsuario, impressoras_candidatas, validar_escolha


def abrir_seletor(config: Configuracao, nome_do_trabalho: str = "") -> EscolhaDoUsuario | None:
    """Abre o diálogo e bloqueia até o usuário escolher (devolve a escolha, já
    validada) ou cancelar/fechar a janela (devolve None)."""
    candidatas = impressoras_candidatas(config)
    resultado: list[EscolhaDoUsuario | None] = [None]

    janela = tk.Tk()
    janela.title("Novo trabalho de impressão")
    janela.resizable(False, False)

    corpo = ttk.Frame(janela, padding=20)
    corpo.pack(fill="both", expand=True)

    ttk.Label(corpo, text="Para qual impressora enviar?", font=("Segoe UI", 12, "bold")).pack(anchor="w")
    if nome_do_trabalho:
        ttk.Label(corpo, text=f'"{nome_do_trabalho}" chegou no PrintRoute.').pack(anchor="w", pady=(2, 12))
    else:
        ttk.Label(corpo, text="").pack(pady=(2, 6))

    impressora_escolhida = tk.StringVar(value=candidatas[0] if candidatas else "")
    for nome in candidatas:
        ttk.Radiobutton(corpo, text=nome, value=nome, variable=impressora_escolhida).pack(anchor="w")

    linha_copias = ttk.Frame(corpo)
    linha_copias.pack(fill="x", pady=(12, 16))
    ttk.Label(linha_copias, text="Cópias").pack(side="left")
    copias = tk.IntVar(value=config.copias_no_seletor)
    ttk.Spinbox(linha_copias, from_=1, to=20, textvariable=copias, width=5).pack(side="right")

    def _imprimir():
        resultado[0] = EscolhaDoUsuario(impressora=impressora_escolhida.get(), copias=copias.get())
        janela.destroy()

    def _cancelar():
        janela.destroy()

    botoes = ttk.Frame(corpo)
    botoes.pack(fill="x")
    ttk.Button(botoes, text="Cancelar", command=_cancelar).pack(side="right", padx=(8, 0))
    ttk.Button(
        botoes, text="Imprimir", command=_imprimir, state="normal" if candidatas else "disabled"
    ).pack(side="right")

    janela.protocol("WM_DELETE_WINDOW", _cancelar)
    janela.mainloop()

    if resultado[0] is not None:
        validar_escolha(resultado[0], config)
    return resultado[0]
