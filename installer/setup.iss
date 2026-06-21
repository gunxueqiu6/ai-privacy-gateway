; AI Privacy Gateway — Inno Setup installer script
; Build: ISCC.exe installer\setup.iss

#define MyAppName "AI Privacy Gateway"
#define MyAppPublisher "AI Privacy Gateway"
#define MyAppURL "https://privacygw.pages.dev"
#define MyAppExeName "PrivacyGateway.exe"
#define MyAppVersion "1.1.0"

[Setup]
AppId={{A7B8E9C4-2D3F-4A1B-8E6C-9F0D1A2B3C4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=commandline dialog
OutputDir=Output
OutputBaseFilename=AI-Privacy-Gateway-Setup-{#MyAppVersion}
SetupIconFile=app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=no
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
; Main executable
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Environment config — include .env.example as .env if no .env provided at build time
Source: "..\.env.example"; DestDir: "{app}"; DestName: ".env.example"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\.env"; DestDir: "{app}"; DestName: ".env"; Flags: ignoreversion skipifsourcedoesntexist

; Pre-generated secrets (auto-generated during first run, but bundle if exists)
Source: "..\vault_data\.secrets.json"; DestDir: "{app}\vault_data"; Flags: ignoreversion skipifsourcedoesntexist

; App icon (used for shortcuts)
Source: "app.ico"; DestDir: "{app}"; Flags: ignoreversion

; License
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\app.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: postinstall nowait skipifsilent unchecked shellexec; WorkingDir: "{app}"

[UninstallDelete]
; Remove vault data directory (user-created data)
Type: dirifempty; Name: "{app}\vault_data"
; Remove the application directory
Type: dirifempty; Name: "{app}"

[UninstallRun]
; Clean: ask to delete vault data on uninstall
Filename: "{cmd}"; Parameters: "/c if exist ""{app}\vault_data"" ( echo Would you like to keep your vault data? )"; Flags: runhidden

[Code]

{ Helper: launch URL in browser }
procedure OpenBrowser(Url: string);
var
    ErrorCode: Integer;
begin
    ShellExec('open', Url, '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
end;

{ Called after successful install, before the Finish page }
procedure CurPageChanged(CurPageID: Integer);
begin
    if CurPageID = wpFinished then
    begin
        WizardForm.RunList.Checked[0] := True;
    end;
end;

{ Ask about vault data on uninstall via a custom confirmation }
function InitializeUninstall(): Boolean;
var
    ResultCode: Integer;
begin
    Result := True;
end;
