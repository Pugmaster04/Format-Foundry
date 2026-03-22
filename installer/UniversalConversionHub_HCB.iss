#define MyAppName "Universal Conversion Hub (HCB)"
#define MyAppVersion "0.5"
#define MyAppPublisher "Universal Conversion Hub (HCB)"
#define MyAppExeName "UniversalConversionHub_HCB.exe"
#define MyUpdaterExeName "UniversalConversionHub_HCB_Updater.exe"

[Setup]
AppId={{33D7E9DA-6CF5-44F7-84E8-06DF57C05495}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Universal Conversion Hub (HCB)
UsePreviousAppDir=yes
DisableDirPage=auto
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
AppMutex=Local\UniversalFileUtilitySuite_SingleInstanceMutex,Local\UniversalFileUtilitySuiteUpdater_SingleInstanceMutex,Local\UniversalConversionHubHCB_SingleInstanceMutex,Local\UniversalConversionHubHCBUpdater_SingleInstanceMutex
OutputDir=..\installer_output
OutputBaseFilename=UniversalConversionHub_HCB_Setup
SetupIconFile=..\assets\universal_file_utility_suite.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop icon"; GroupDescription: "Additional icons:"

[Files]
Source: "..\dist\UniversalConversionHub_HCB.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\UniversalConversionHub_HCB_Updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\PROJECT_PLAN.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\update_manifest.example.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Universal Conversion Hub (HCB)"; Filename: "{app}\{#MyAppExeName}"
Name: "{autoprograms}\Universal Conversion Hub (HCB) Updater"; Filename: "{app}\{#MyUpdaterExeName}"
Name: "{autodesktop}\Universal Conversion Hub (HCB)"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Universal Conversion Hub (HCB)"; Flags: nowait postinstall skipifsilent
