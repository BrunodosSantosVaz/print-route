"""Iniciar o PrintRoute com o Windows: grava/remove um valor na chave Run do usuário
atual (HKEY_CURRENT_USER) -- o jeito padrão e mais simples de iniciar um programa no
login, sem precisar de administrador nem de um serviço do Windows.

`winreg` é importado dentro de cada função, não no topo do arquivo: assim o módulo
importa em qualquer sistema (`winreg` só existe no Windows)."""

NOME_DO_VALOR = "PrintRoute"
CHAVE_RUN = r"Software\Microsoft\Windows\CurrentVersion\Run"


def esta_habilitado() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN) as chave:
            winreg.QueryValueEx(chave, NOME_DO_VALOR)
            return True
    except FileNotFoundError:
        return False


def habilitar(caminho_do_executavel: str) -> None:
    """Grava o caminho do executável na chave Run. Repetir a chamada só sobrescreve o
    valor (idempotente)."""
    import winreg

    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, CHAVE_RUN) as chave:
        winreg.SetValueEx(chave, NOME_DO_VALOR, 0, winreg.REG_SZ, caminho_do_executavel)


def desabilitar() -> None:
    """Remove o valor da chave Run. Não falha se ele já não existir (idempotente)."""
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, CHAVE_RUN, 0, winreg.KEY_SET_VALUE) as chave:
            winreg.DeleteValue(chave, NOME_DO_VALOR)
    except FileNotFoundError:
        pass
