"""Protótipo mínimo da tarefa #4: prova que um trabalho de impressão enviado a uma
impressora do Windows chega até um processo Python — sem monitor de porta nativo, sem
RedMon, só uma Porta Local (recurso já embutido no Windows) apontando para um arquivo,
mais este script observando esse arquivo. Ver poc/README.md para o passo a passo.

Uso:
    python capturar_e_encaminhar.py <caminho-do-arquivo-da-porta>
"""
import datetime
import pathlib
import sys
import time

INTERVALO_DE_VERIFICACAO = 0.3  # segundos entre cada checagem do arquivo
PERIODO_DE_ESTABILIDADE = 1.0  # segundos sem o arquivo crescer para considerar o trabalho concluído


def aguardar_trabalho(caminho: pathlib.Path) -> bytes:
    """Bloqueia até o arquivo da porta parar de crescer por PERIODO_DE_ESTABILIDADE
    (heurística de que o spooler terminou de escrever e fechou o trabalho)."""
    tamanho_anterior = -1
    estavel_desde = None
    while True:
        if caminho.exists():
            tamanho_atual = caminho.stat().st_size
            if tamanho_atual > 0:
                if tamanho_atual == tamanho_anterior:
                    if estavel_desde is None:
                        estavel_desde = time.monotonic()
                    elif time.monotonic() - estavel_desde >= PERIODO_DE_ESTABILIDADE:
                        return caminho.read_bytes()
                else:
                    estavel_desde = None
                tamanho_anterior = tamanho_atual
        time.sleep(INTERVALO_DE_VERIFICACAO)


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python capturar_e_encaminhar.py <caminho-do-arquivo-da-porta>")
        raise SystemExit(2)

    caminho_porta = pathlib.Path(sys.argv[1])
    pasta_capturas = caminho_porta.parent / "capturas"
    pasta_capturas.mkdir(exist_ok=True)

    print(f"Observando {caminho_porta} ... (Ctrl+C para parar)")
    print("Imprima algo na impressora de teste para ver o trabalho chegar aqui.\n")

    contador = 0
    while True:
        dados = aguardar_trabalho(caminho_porta)
        contador += 1
        agora = datetime.datetime.now()
        destino = pasta_capturas / f"trabalho-{agora:%Y%m%d-%H%M%S}-{contador}.bin"
        destino.write_bytes(dados)

        print(f"[{agora:%H:%M:%S}] Trabalho #{contador} capturado: {len(dados)} bytes -> {destino.name}")
        amostra = dados[:200].decode("latin-1", errors="replace")
        print(f"  Primeiros bytes (como texto): {amostra!r}\n")


if __name__ == "__main__":
    main()
