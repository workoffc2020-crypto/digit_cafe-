; Inno Setup script — builds CyberCafeStudio_Setup.exe (https://jrsoftware.org/isinfo.php)
#define AppName "Cyber Cafe Studio"
#define AppVersion "1.0.0"
#define AppExe "CyberCafeStudio.exe"

[Setup]
AppId={{B7E5A0C2-3C41-4F0B-9E57-6D1A2C8F4A11}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Cyber Cafe Studio
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExe}
SetupIconFile=..\assets\app.ico
OutputDir=..\dist_installer
OutputBaseFilename=CyberCafeStudio_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
ChangesAssociations=no

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "sendto"; Description: "Add to the right-click ""Send to"" menu (convert selected images to PDF)"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\CyberCafeStudio\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion createallsubdirs
Source: "..\assets\app.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\THIRD_PARTY_LICENSES.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\models\*"; DestDir: "{app}\models"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\app.ico"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\app.ico"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Windows\SendTo\{#AppName}"; Filename: "{app}\{#AppExe}"; IconFilename: "{app}\app.ico"; Tasks: sendto

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
