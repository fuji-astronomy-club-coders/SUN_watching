#define AppName "SUN_watching"
#ifndef AppVersion
  #define AppVersion "1.0.1"
#endif
#define AppPublisher "fuji-astronomy-club-coders"
#define AppExeName "SUN_watching.exe"

[Setup]
AppId={{D3F6E68E-6677-4F5B-A3D3-0B76F4A68C8D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\SUN_watching
DefaultGroupName={#AppName}
OutputDir=..\dist\installer
OutputBaseFilename=SUN_watching-setup-windows-x64
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
UninstallDisplayIcon={app}\{#AppExeName}

[Files]
Source: "..\dist\SUN_watching\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SUN_watching"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\SUN_watching"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "デスクトップにショートカットを作成"; GroupDescription: "追加タスク:"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "SUN_watchingを起動"; Flags: postinstall nowait skipifsilent
