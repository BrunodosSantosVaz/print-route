"""Estado em memória do PrintRoute enquanto ele roda: se o reencaminhamento está
ativado ou pausado (usado pelo menu da bandeja, tarefa #10). Não é persistido -- ao
reiniciar o PrintRoute, volta a ativado."""
import dataclasses


@dataclasses.dataclass
class EstadoApp:
    ativo: bool = True

    def alternar(self) -> None:
        self.ativo = not self.ativo
