"""Configuração do PrintRoute: para onde e como encaminhar. Ver o protótipo de telas
validado (issue #3): modo "impressora(s) fixas" (com cópias por impressora) ou
"perguntar a cada impressão" (com uma quantidade de cópias sugerida no seletor).

Fica em C:\\ProgramData\\PrintRoute\\config.json -- todo o sistema, não por usuário: o
PrintRoute é um recurso da máquina, como qualquer impressora instalada.

Sem dependência do Windows (só biblioteca padrão): dá para testar em qualquer sistema,
passando um caminho próprio em vez do padrão.
"""
import dataclasses
import json
import pathlib

CAMINHO_PADRAO = pathlib.Path(r"C:\ProgramData\PrintRoute\config.json")

MODO_FIXO = "fixo"
MODO_PERGUNTAR = "perguntar"
MODOS_VALIDOS = (MODO_FIXO, MODO_PERGUNTAR)


@dataclasses.dataclass
class ImpressoraDestino:
    nome: str
    copias: int = 1

    def __post_init__(self):
        if self.copias < 1:
            raise ValueError(f"copias deve ser pelo menos 1 (recebeu {self.copias!r})")


@dataclasses.dataclass
class Configuracao:
    modo: str = MODO_FIXO
    impressoras: list[ImpressoraDestino] = dataclasses.field(default_factory=list)
    copias_no_seletor: int = 1

    def __post_init__(self):
        if self.modo not in MODOS_VALIDOS:
            raise ValueError(f"modo inválido: {self.modo!r} (esperado um de {MODOS_VALIDOS!r})")
        if self.copias_no_seletor < 1:
            raise ValueError(f"copias_no_seletor deve ser pelo menos 1 (recebeu {self.copias_no_seletor!r})")

    def para_dict(self) -> dict:
        return {
            "modo": self.modo,
            "impressoras": [{"nome": i.nome, "copias": i.copias} for i in self.impressoras],
            "copias_no_seletor": self.copias_no_seletor,
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Configuracao":
        return cls(
            modo=dados.get("modo", MODO_FIXO),
            impressoras=[ImpressoraDestino(**i) for i in dados.get("impressoras", [])],
            copias_no_seletor=dados.get("copias_no_seletor", 1),
        )


def carregar(caminho: pathlib.Path = CAMINHO_PADRAO) -> Configuracao:
    """Lê a configuração salva. Se o arquivo não existir (primeira vez que o PrintRoute
    roda), devolve uma configuração vazia no modo padrão, sem lançar erro.

    "utf-8-sig" (não "utf-8"): o arquivo é editável à mão (é só JSON), e editores comuns
    no Windows -- Notepad com a opção "UTF-8", ou `Set-Content -Encoding UTF8` do
    PowerShell -- gravam um BOM no início. "utf-8" puro não tolera isso (bug real,
    achado ao vivo: `json.JSONDecodeError: Unexpected UTF-8 BOM`, derrubando o laço de
    captura inteiro); "utf-8-sig" lê os dois casos (com ou sem BOM) sem diferença."""
    if not caminho.exists():
        return Configuracao()
    dados = json.loads(caminho.read_text(encoding="utf-8-sig"))
    return Configuracao.de_dict(dados)


def salvar(configuracao: Configuracao, caminho: pathlib.Path = CAMINHO_PADRAO) -> None:
    """Grava a configuração, criando a pasta se ainda não existir."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(configuracao.para_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
