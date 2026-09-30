"""Painel de configuração do PrintRoute (tarefa #10) -- a tela de verdade, em Tkinter,
seguindo o protótipo validado (issue #3, artboard "Main"). Sem teste automatizado
(interface gráfica, precisa de um display) -- as camadas de lógica que ela usa
(`configuracao.py`, `inicializacao.py`) são testadas separadamente."""
import sys
import tkinter as tk
from tkinter import ttk

from printroute import inicializacao
from printroute.configuracao import MODO_FIXO, MODO_PERGUNTAR, Configuracao, ImpressoraDestino, salvar


def _impressoras_instaladas() -> list[str]:
    import win32print

    # Level 2 (não o padrão, nível 1): nível 1 devolve tuplas por compatibilidade
    # antiga, sem a chave "pPrinterName" que este código usa.
    impressoras = win32print.EnumPrinters(
        win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS, None, 2
    )
    return [info["pPrinterName"] for info in impressoras if info["pPrinterName"] != "PrintRoute"]


def abrir_configuracoes(config: Configuracao) -> None:
    """Abre a janela de configurações; bloqueia até ela ser fechada (Salvar ou
    Cancelar)."""
    copias_por_impressora = {impressora.nome: impressora.copias for impressora in config.impressoras}
    marcadas_inicialmente = set(copias_por_impressora)

    janela = tk.Tk()
    janela.title("Configurações do PrintRoute")

    corpo = ttk.Frame(janela, padding=20)
    corpo.pack(fill="both", expand=True)

    ttk.Label(corpo, text="Reencaminhamento de impressão", font=("Segoe UI", 14, "bold")).pack(anchor="w")
    ttk.Label(corpo, text="Escolha para onde o PrintRoute envia o que chega nele.").pack(
        anchor="w", pady=(2, 12)
    )

    modo = tk.StringVar(value=config.modo)
    linha_modo = ttk.Frame(corpo)
    linha_modo.pack(fill="x", pady=(0, 16))
    ttk.Radiobutton(linha_modo, text="Impressora(s) fixas", value=MODO_FIXO, variable=modo).pack(side="left")
    ttk.Radiobutton(
        linha_modo, text="Perguntar a cada impressão", value=MODO_PERGUNTAR, variable=modo
    ).pack(side="left", padx=(16, 0))

    ttk.Label(corpo, text="Impressoras").pack(anchor="w")
    lista = ttk.Frame(corpo, relief="groove", borderwidth=1)
    lista.pack(fill="both", expand=True, pady=(4, 16))

    variaveis_marcada: dict[str, tk.BooleanVar] = {}
    variaveis_copias: dict[str, tk.IntVar] = {}
    instaladas = _impressoras_instaladas()
    if not instaladas:
        ttk.Label(lista, text="Nenhuma impressora instalada foi encontrada.").pack(padx=8, pady=8)
    for nome in instaladas:
        linha = ttk.Frame(lista)
        linha.pack(fill="x", padx=8, pady=4)
        marcada = tk.BooleanVar(value=nome in marcadas_inicialmente)
        variaveis_marcada[nome] = marcada
        ttk.Checkbutton(linha, text=nome, variable=marcada).pack(side="left")
        copias = tk.IntVar(value=copias_por_impressora.get(nome, 1))
        variaveis_copias[nome] = copias
        ttk.Spinbox(linha, from_=1, to=20, textvariable=copias, width=5).pack(side="right", padx=(0, 8))
        ttk.Label(linha, text="Cópias").pack(side="right")

    iniciar_com_windows = tk.BooleanVar(value=inicializacao.esta_habilitado())
    ttk.Checkbutton(corpo, text="Iniciar o PrintRoute com o Windows", variable=iniciar_com_windows).pack(
        anchor="w"
    )

    def _salvar():
        nova_config = Configuracao(
            modo=modo.get(),
            impressoras=[
                ImpressoraDestino(nome, variaveis_copias[nome].get())
                for nome, marcada in variaveis_marcada.items()
                if marcada.get()
            ],
            copias_no_seletor=config.copias_no_seletor,
        )
        salvar(nova_config)
        if iniciar_com_windows.get():
            inicializacao.habilitar(sys.executable)
        else:
            inicializacao.desabilitar()
        janela.destroy()

    def _cancelar():
        janela.destroy()

    rodape = ttk.Frame(corpo)
    rodape.pack(fill="x", pady=(8, 0))
    ttk.Button(rodape, text="Cancelar", command=_cancelar).pack(side="right", padx=(8, 0))
    ttk.Button(rodape, text="Salvar", command=_salvar).pack(side="right")

    janela.mainloop()
