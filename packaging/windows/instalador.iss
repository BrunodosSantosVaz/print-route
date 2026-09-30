; Instalador do PrintRoute (Inno Setup). Empacota o .exe já compilado pelo build_exe.py
; e wrapado por build_installer.py: instala em Program Files, cria atalho no Menu
; Iniciar, registra a impressora PrintRoute (o próprio .exe faz isso ao rodar pela
; primeira vez -- ver src/printroute/__main__.py) e, ao desinstalar, roda o .exe com
; --desinstalar (remove a impressora e a entrada de início automático) antes de apagar
; os arquivos. Sem assinatura de código (decisão registrada na issue #3): o
; SmartScreen pode avisar na instalação -- aceitável nesta fase.
;
; Uso: ISCC.exe /DMyAppVersion=0.1.0 /DMyAppExe="caminho\para\PrintRoute.exe" instalador.iss
; (build_installer.py monta esses defines automaticamente; não rode ISCC direto à mão
; para uma release oficial -- essas só saem do CI.)
;
; Também embute o Ghostscript/ghostxps (gxpswin64.exe + gxpsdll64.dll, baixados e
; conferidos por build_installer.py -- tarefa #34): reconstrói o trabalho capturado
; (pacote XPS) na impressora de destino, pelo driver dela própria, em vez de copiar
; bytes brutos (que corrompia documentos reais). Ver src/printroute/spooler/encaminhar.py.

#ifndef MyAppVersion
  #define MyAppVersion "0.0.0"
#endif
#ifndef MyAppExe
  #define MyAppExe "..\..\build-local\PrintRoute.exe"
#endif
#ifndef MyGhostXpsDir
  #define MyGhostXpsDir "..\..\build-local\ghostxps-cache"
#endif
#ifndef MyOutputDir
  #define MyOutputDir "..\..\build-local"
#endif
#ifndef MyOutputBaseFilename
  #define MyOutputBaseFilename "PrintRoute-Setup-v" + MyAppVersion + "-windows-x64"
#endif

[Setup]
AppId={{9ED4EE32-BDE3-418D-8C5E-B359D3326F02}
AppName=PrintRoute
AppVersion={#MyAppVersion}
AppPublisher=Bruno dos Santos Vaz
AppPublisherURL=https://github.com/BrunodosSantosVaz/print-route
AppSupportURL=https://github.com/BrunodosSantosVaz/print-route/issues
DefaultDirName={autopf}\PrintRoute
DefaultGroupName=PrintRoute
UninstallDisplayIcon={app}\PrintRoute.exe
UninstallDisplayName=PrintRoute
OutputDir={#MyOutputDir}
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
SetupLogging=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Criar um atalho na área de trabalho"; GroupDescription: "Atalhos adicionais:"; Flags: unchecked

[Files]
Source: "{#MyAppExe}"; DestDir: "{app}"; DestName: "PrintRoute.exe"; Flags: ignoreversion
Source: "{#MyGhostXpsDir}\gxpswin64.exe"; DestDir: "{app}\ghostxps"; Flags: ignoreversion
Source: "{#MyGhostXpsDir}\gxpsdll64.dll"; DestDir: "{app}\ghostxps"; Flags: ignoreversion

[Icons]
Name: "{group}\PrintRoute"; Filename: "{app}\PrintRoute.exe"
Name: "{group}\Desinstalar o PrintRoute"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PrintRoute"; Filename: "{app}\PrintRoute.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PrintRoute.exe"; Description: "Abrir o PrintRoute agora"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{app}\PrintRoute.exe"; Parameters: "--desinstalar"; RunOnceId: "DesinstalarImpressora"; Flags: waituntilterminated runhidden
