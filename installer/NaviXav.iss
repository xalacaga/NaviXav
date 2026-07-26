#define MyAppName "NaviXav"
#ifndef MyAppVersion
#define MyAppVersion "0.1.0"
#endif
#define MyAppPublisher "Galvo"
#define MyAppExeName "NaviXav.exe"

[Setup]
AppId={{A50F86F9-7DB6-4C89-AEC8-D2B7898CA12B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\release
OutputBaseFilename=NaviXav-Setup-{#MyAppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
CloseApplicationsFilter={#MyAppExeName}
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=NaviXav - assistant de vol IFR pour MSFS
SetupIconFile=..\assets\navixav.ico

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "Créer un raccourci sur le bureau"; GroupDescription: "Raccourcis :"; Flags: unchecked

[Files]
Source: "..\dist\NaviXav\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "assets\MicrosoftEdgeWebView2Setup.exe"; Flags: dontcopy

[Icons]
Name: "{group}\NaviXav"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Documentation NaviXav"; Filename: "{app}\README.md"
Name: "{autodesktop}\NaviXav"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Lancer NaviXav"; Flags: nowait postinstall skipifsilent

[Code]
var
  PrerequisitesPage: TWizardPage;

function WebView2Detected(): Boolean;
var
  Version: String;
  ClientKey: String;
begin
  ClientKey :=
    'Software\Microsoft\EdgeUpdate\Clients\' +
    '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  Result :=
    RegQueryStringValue(HKLM32, ClientKey, 'pv', Version) or
    RegQueryStringValue(HKCU, ClientKey, 'pv', Version);
  Result := Result and (Version <> '') and (Version <> '0.0.0.0');
end;

function MsfsDetected(): Boolean;
begin
  Result :=
    DirExists(ExpandConstant('{localappdata}\Packages\Microsoft.FlightSimulator_8wekyb3d8bbwe')) or
    DirExists(ExpandConstant('{localappdata}\Packages\Microsoft.Limitless_8wekyb3d8bbwe')) or
    RegKeyExists(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 1250410') or
    RegKeyExists(HKLM64, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 2537590');
end;

function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  GetWindowsVersionEx(Version);
  if Version.Major < 10 then
  begin
    MsgBox('NaviXav nécessite Windows 10 ou Windows 11.', mbCriticalError, MB_OK);
    Result := False;
    Exit;
  end;
  if not IsWin64 then
  begin
    MsgBox('NaviXav nécessite une version 64 bits de Windows.', mbCriticalError, MB_OK);
    Result := False;
    Exit;
  end;
  Result := True;
end;

procedure AddCheckLine(const Text: String; const Available: Boolean);
var
  LabelControl: TNewStaticText;
begin
  LabelControl := TNewStaticText.Create(PrerequisitesPage);
  LabelControl.Parent := PrerequisitesPage.Surface;
  LabelControl.Left := 0;
  LabelControl.Top := 24 + (PrerequisitesPage.Surface.ControlCount * 24);
  if Available then
  begin
    LabelControl.Caption := '✓  ' + Text;
    LabelControl.Font.Color := $00632720;
  end
  else
  begin
    LabelControl.Caption := 'ℹ  ' + Text;
    LabelControl.Font.Color := $00905B18;
  end;
end;

procedure InitializeWizard();
begin
  PrerequisitesPage := CreateCustomPage(
    wpWelcome,
    'Contrôle des prérequis',
    'Tout ce qui est nécessaire à NaviXav est vérifié avant l’installation.'
  );
  AddCheckLine('Windows 64 bits compatible', True);
  AddCheckLine('Python et bibliothèques : inclus dans NaviXav', True);
  AddCheckLine(
    'SimConnect : connecteur autonome NaviXav inclus, aucune installation système',
    True
  );
  if WebView2Detected() then
    AddCheckLine('Interface Microsoft WebView2 détectée', True)
  else
    AddCheckLine('Microsoft WebView2 sera installé automatiquement', False);
  if MsfsDetected() then
    AddCheckLine('Microsoft Flight Simulator détecté', True)
  else
    AddCheckLine('MSFS non détecté : le mode Démo restera utilisable', False);
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  Bootstrapper: String;
begin
  Result := '';
  if WebView2Detected() then
    Exit;

  ExtractTemporaryFile('MicrosoftEdgeWebView2Setup.exe');
  Bootstrapper := ExpandConstant('{tmp}\MicrosoftEdgeWebView2Setup.exe');
  if not Exec(
    Bootstrapper,
    '/silent /install',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) then
  begin
    Result := 'Impossible de lancer l''installation de Microsoft WebView2.';
    Exit;
  end;
  if (ResultCode <> 0) or not WebView2Detected() then
    Result :=
      'Microsoft WebView2 n''a pas pu être installé. ' +
      'Vérifiez votre connexion Internet puis relancez l''installation.';
end;
