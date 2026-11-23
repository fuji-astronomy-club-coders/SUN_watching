#define AppName "SUN_watching"
#ifndef AppVersion
  #define AppVersion "1.9.1"
#endif
#define AppPublisher "fuji-astronomy-club-coders"
#define AppExeName "SUN_watching.exe"

[Setup]
AppId={{D3F6E68E-6677-4F5B-A3D3-0B76F4A68C8D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; 管理者権限を要求せず、PATH も変更しないユーザー単位のインストールにする。
PrivilegesRequired=lowest
ChangesEnvironment=no
DefaultDirName={localappdata}\Programs\SUN_watching
DefaultGroupName={#AppName}
OutputDir=..\dist\installer
OutputBaseFilename=SUN_watching-{#AppVersion}-setup-windows-x64
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}

[Files]
Source: "..\dist\SUN_watching\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Dirs]
; アプリ本体とは別に、書き込み可能な出力先をあらかじめ用意する。
Name: "{localappdata}\SUN_watching"; Flags: uninsneveruninstall
Name: "{localappdata}\SUN_watching\log"; Flags: uninsneveruninstall
Name: "{localappdata}\SUN_watching\data"; Flags: uninsneveruninstall
Name: "{localappdata}\SUN_watching\data\report"; Flags: uninsneveruninstall

[Icons]
Name: "{group}\SUN_watching"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\SUN_watching"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加タスク:"

[Run]
Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Description: "SUN_watchingを起動"; Flags: postinstall nowait skipifsilent
