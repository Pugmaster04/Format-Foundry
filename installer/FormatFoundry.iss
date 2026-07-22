#define MyAppName "Format Foundry"
#define MyAppVersion "0.5.0-beta"
#define MyAppDisplayVersion "Beta 0.5"
#define MyAppPublisher "Format Foundry"
#define MyAppExeName "FormatFoundry.exe"
#define MyUpdaterExeName "FormatFoundry_Updater.exe"

[Setup]
AppId={{33D7E9DA-6CF5-44F7-84E8-06DF57C05495}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppDisplayVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://pugmaster04.github.io/Format-Foundry/index.html
AppSupportURL=https://github.com/Pugmaster04/Format-Foundry/issues
AppUpdatesURL=https://pugmaster04.github.io/Format-Foundry/downloads.html
AppComments=Self-contained desktop application. Optional third-party feature tools are managed through the updater.
LicenseFile=..\LICENSE
DefaultDirName={autopf}\Format Foundry
UsePreviousAppDir=yes
DisableDirPage=auto
DisableWelcomePage=no
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
SetupLogging=yes
AppMutex=Local\UniversalFileUtilitySuite_SingleInstanceMutex,Local\UniversalFileUtilitySuiteUpdater_SingleInstanceMutex,Local\UniversalConversionHubHCB_SingleInstanceMutex,Local\UniversalConversionHubHCBUpdater_SingleInstanceMutex,Local\UniversalConversionHubUCH_SingleInstanceMutex,Local\UniversalConversionHubUCHUpdater_SingleInstanceMutex,Local\FormatFoundry_SingleInstanceMutex,Local\FormatFoundryUpdater_SingleInstanceMutex
OutputDir=..\installer_output
OutputBaseFilename=FormatFoundry_Setup
SetupIconFile=..\assets\universal_file_utility_suite.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
ArchitecturesAllowed=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName} {#MyAppDisplayVersion}
VersionInfoVersion=0.5.0.0
VersionInfoProductVersion=0.5.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"
Name: "reviewbackends"; Description: "Review optional feature tools after setup (recommended)"; GroupDescription: "After installation:"; Flags: checkedonce

[Files]
Source: "..\dist\FormatFoundry.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\FormatFoundry_Updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PROJECT_PLAN.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\update_manifest.example.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Format Foundry"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\Format Foundry Updater"; Filename: "{app}\{#MyUpdaterExeName}"
Name: "{autoprograms}\Uninstall Format Foundry"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Format Foundry"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyUpdaterExeName}"; Parameters: "--backends"; Description: "Review optional feature tools"; Flags: nowait postinstall skipifsilent; Tasks: reviewbackends
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Format Foundry"; Flags: nowait postinstall skipifsilent; Tasks: not reviewbackends

[Code]
const
  ProductUninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{33D7E9DA-6CF5-44F7-84E8-06DF57C05495}_is1';
  ProductUninstallKey32 = 'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\{33D7E9DA-6CF5-44F7-84E8-06DF57C05495}_is1';

function ReadRegisteredVersion(var ExistingName: String; var ExistingVersion: String): Boolean;
begin
  Result := RegQueryStringValue(HKLM, ProductUninstallKey, 'DisplayName', ExistingName);
  if Result then
    RegQueryStringValue(HKLM, ProductUninstallKey, 'DisplayVersion', ExistingVersion);

  if not Result then
  begin
    Result := RegQueryStringValue(HKLM, ProductUninstallKey32, 'DisplayName', ExistingName);
    if Result then
      RegQueryStringValue(HKLM, ProductUninstallKey32, 'DisplayVersion', ExistingVersion);
  end;

  if not Result then
  begin
    Result := RegQueryStringValue(HKCU, ProductUninstallKey, 'DisplayName', ExistingName);
    if Result then
      RegQueryStringValue(HKCU, ProductUninstallKey, 'DisplayVersion', ExistingVersion);
  end;
end;

procedure InitializeWizard;
var
  ExistingName: String;
  ExistingVersion: String;
  ExistingExecutable: String;
begin
  ExistingName := '';
  ExistingVersion := '';
  if ReadRegisteredVersion(ExistingName, ExistingVersion) then
  begin
    WizardForm.WelcomeLabel2.Caption :=
      'Setup found ' + ExistingName + ' ' + ExistingVersion + '.' + #13#10 + #13#10 +
      'It will be upgraded in place to {#MyAppDisplayVersion}. Your settings and output files are preserved. ' +
      'Running app or updater windows will be closed safely before files are replaced.';
  end
  else
  begin
    ExistingExecutable := ExpandConstant('{autopf}\Format Foundry\{#MyAppExeName}');
    if FileExists(ExistingExecutable) then
      WizardForm.WelcomeLabel2.Caption :=
        'Setup found older unregistered Format Foundry files and will replace them with {#MyAppDisplayVersion}.' + #13#10 + #13#10 +
        'The app is self-contained and does not require Codex, Python, or a source-code folder.'
    else
      WizardForm.WelcomeLabel2.Caption :=
        'This appears to be a clean installation of {#MyAppDisplayVersion}.' + #13#10 + #13#10 +
        'The app is self-contained and does not require Codex, Python, or a source-code folder. ' +
        'Optional third-party feature tools can be reviewed safely after setup.';
  end;
end;
