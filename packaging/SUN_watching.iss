#define AppName "SUN_watching"
#ifndef AppVersion
  #define AppVersion "1.10.0"
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
; 既定でチェックする。ドライバ本体は同梱せず、インストール時に公式サイトから取得する。
; サイレント導入で不要な場合は /MERGETASKS=!asidriver を指定してスキップできる。
Name: "asidriver"; Description: "ZWO ASI カメラドライバを公式サイトからダウンロードしてインストール (管理者権限とネットワークが必要)"; GroupDescription: "追加タスク:"

[Run]
Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Description: "SUN_watchingを起動"; Flags: postinstall nowait skipifsilent

[Code]
const
  AsiDriverTask = 'asidriver';

procedure VerifyBundledResources();
var
  DllPath: String;
begin
  DllPath := ExpandConstant('{app}\_internal\camera\bin\ASICamera2.dll');
  if not FileExists(DllPath) then
    MsgBox('同梱の ASICamera2.dll が見つかりません: ' + DllPath + #13#10 + '配布物が破損している可能性があります。インストーラーを再ダウンロードしてください。', mbError, MB_OK);
end;

procedure InstallAsiDriver();
var
  ScriptPath: String;
  Params: String;
  ResultCode: Integer;
begin
  ScriptPath := ExpandConstant('{app}\tools\install-asi-driver.ps1');
  if not FileExists(ScriptPath) then
  begin
    MsgBox('ZWO ASI ドライバ用スクリプトが見つかりません: ' + ScriptPath, mbError, MB_OK);
    exit;
  end;

  Params := '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '"';
  if not ShellExec('open', ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params, '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
  begin
    MsgBox('ZWO ASI ドライバのインストールを開始できませんでした。' + #13#10 + '公式サイトから手動でインストールしてください: https://www.zwoastro.com/software/camera-driver/', mbError, MB_OK);
    exit;
  end;

  if ResultCode <> 0 then
    MsgBox('ZWO ASI ドライバのインストールに失敗しました (終了コード ' + IntToStr(ResultCode) + ')。' + #13#10 + '公式サイトから手動でインストールしてください: https://www.zwoastro.com/software/camera-driver/', mbError, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    VerifyBundledResources();
    if WizardIsTaskSelected(AsiDriverTask) then
      InstallAsiDriver();
  end;
end;
