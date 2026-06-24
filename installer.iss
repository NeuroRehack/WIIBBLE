; WIIBBLE Inno Setup script
; Build with: iscc installer.iss
; Or via compiler.bat which calls this automatically after Nuitka.
;
; Prerequisites:
;   Inno Setup 6.x  https://jrsoftware.org/isinfo.php
;   The Nuitka standalone output must exist at dist_nuitka\wiibble.dist\
;   before running this script.

#define AppName      "WIIBBLE"
; Override at build time: iscc /DAppVersion=2.0.0 installer.iss
; Default matches pyproject.toml — keep in sync when bumping releases locally.
#ifndef AppVersion
  #define AppVersion "2.0.1"
#endif
#define AppPublisher "NeuroRehack"
#define AppURL       "https://github.com/NeuroRehack/WIIBBLE"
#define AppExeName   "WIIBBLE.exe"
#define SourceDir    "dist_nuitka\wiibble.dist"

[Setup]
AppId={{A3F2C1D4-8B7E-4F6A-9C2D-1E5B3A7F4C8D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}

; Installation directory
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}

; Output
OutputDir=installer_output
OutputBaseFilename=WIIBBLE-{#AppVersion}-Setup
SetupIconFile=images\logoPerson.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Silent install support (for IT managed deployment)
; /SILENT        — progress window, no prompts
; /VERYSILENT    — no windows at all
; /SUPPRESSMSGBOXES — suppress message boxes (use with /VERYSILENT)
; /NORESTART     — suppress automatic restart
AllowNoIcons=yes

; Require admin rights (writes to Program Files)
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; Windows 10 or later
MinVersion=10.0

; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Wizard appearance
WizardStyle=modern
DisableWelcomePage=no
DisableDirPage=no
DisableProgramGroupPage=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; Bundle the entire Nuitka standalone output directory
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Start Menu shortcut
Name: "{group}\{#AppName}";          Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
; Optional Desktop shortcut (only if user ticked the task above)
Name: "{autodesktop}\{#AppName}";    Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch the app after install (not shown in silent mode)
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up the recordings folder only if empty — never delete patient data
; (Inno Setup removes files it installed; user recordings in %APPDATA% are untouched)
Type: dirifempty; Name: "{app}"
