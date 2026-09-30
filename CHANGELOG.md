# Changelog

Todas as mudanças relevantes deste projeto são registradas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e versionamento
[SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.1.0] - 2026-09-30

### Adicionado
- Registrar o PrintRoute como impressora no Windows (porta + impressora, instalação e remoção) (#5)
- Encaminhar o trabalho recebido para uma impressora real configurada (caminho mais simples: 1 impressora fixa, 1 cópia) (#6)
- Configuração local (arquivo/registro): impressoras de destino, número de cópias, modo seletor-na-hora (#7)
- Encaminhar para mais de uma impressora e com mais de uma cópia (#8)
- Seletor de impressora na hora (diálogo ao chegar um trabalho, quando configurado) (#9)
- Ícone na bandeja do sistema com o painel de configuração (#10)
- Instalador Windows (empacota o executável, registra a impressora, inicia o painel da bandeja com o Windows) (#11)
- Desinstalador padrão (Configurações → Aplicativos / Programas e Recursos), removendo porta, impressora, início automático e arquivos (#12)

### Corrigido
- PyInstaller não empacota win32timezone: captura de impressão trava com ModuleNotFoundError (#24)
- Configurações abre janela repetida (e quebra o seletor): Tkinter criado fora da thread principal (#26)
- Laço de captura quebra silenciosamente: config.json com BOM e qualquer erro inesperado derrubam o app todo (#28)
- PrintRoute.exe roda sem elevação e não consegue ler a pasta de spool (seletor nunca abre pro usuário normal) (#30)
- Instalador falha ao abrir/desinstalar o PrintRoute: CreateProcess exige elevação (erro 740) (#32)
- Encaminhamento corrompe documentos reais: precisa reconstruir via Ghostscript (XPS), não copiar bytes brutos (#34)
- Console do Ghostscript aparece na tela ao encaminhar (deveria ser invisível) (#36)

