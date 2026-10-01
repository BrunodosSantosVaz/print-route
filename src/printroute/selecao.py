"""Lógica do seletor de impressora na hora (tarefa #9, modo "perguntar" da
configuração): a partir da lista de impressoras candidatas (`config.impressoras`) e da
escolha do usuário, decide para onde e quantas cópias mandar. Sem Tkinter aqui -- a
tela de verdade (`printroute.ui.seletor`) usa esta lógica; assim dá para testar sem
interface gráfica, em qualquer sistema."""
import dataclasses

from printroute.configuracao import Configuracao


@dataclasses.dataclass
class EscolhaDoUsuario:
    impressora: str
    copias: int


class SemImpressoraCandidataError(RuntimeError):
    """A configuração está no modo "perguntar" mas não há nenhuma impressora candidata
    (`config.impressoras` vazia) -- não há o que oferecer no seletor."""


def impressoras_candidatas(config: Configuracao) -> list[str]:
    """Nomes das impressoras a oferecer no seletor, na ordem configurada."""
    return [impressora.nome for impressora in config.impressoras]


def escolha_padrao(config: Configuracao) -> EscolhaDoUsuario:
    """A pré-seleção do diálogo: a primeira impressora candidata, com as cópias
    sugeridas da configuração."""
    candidatas = impressoras_candidatas(config)
    if not candidatas:
        raise SemImpressoraCandidataError("Nenhuma impressora candidata configurada para o seletor.")
    return EscolhaDoUsuario(impressora=candidatas[0], copias=config.copias_no_seletor)


def validar_escolha(escolha: EscolhaDoUsuario, config: Configuracao) -> None:
    """Levanta ValueError se a escolha não for válida: impressora fora da lista de
    candidatas, ou cópias menor que 1."""
    candidatas = impressoras_candidatas(config)
    if escolha.impressora not in candidatas:
        raise ValueError(f"{escolha.impressora!r} não está entre as impressoras candidatas: {candidatas!r}")
    if escolha.copias < 1:
        raise ValueError(f"copias deve ser pelo menos 1 (recebeu {escolha.copias!r})")
