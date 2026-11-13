; RATT Inno Setup Packaging Script (SEC-R002-02 Remediation)
; Installs RATT.exe and native COM / helper DLLs into write-protected Program Files
; to prevent elevated InProcServer32 DLL hijacking from user-writable %APPDATA%.

[Setup]
AppId={{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}
AppName=RATT v2 — Rapid Access To Text
AppVersion=2.0.0
AppPublisher=Cybrox
DefaultDirName={autopf}\RATT
DefaultGroupName=RATT
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
OutputDir=dist
OutputBaseFilename=RATT_Setup_v2
Compression=lzma2
SolidCompression=yes

[Files]
Source: "dist\RATT.exe"; DestDir: "{autopf}\RATT"; Flags: ignoreversion
Source: "assets\ratt_menu.dll"; DestDir: "{autopf}\RATT"; Flags: ignoreversion
Source: "assets\ratt_daemon.dll"; DestDir: "{autopf}\RATT"; Flags: ignoreversion
Source: "assets\ratt_icon.ico"; DestDir: "{autopf}\RATT\assets"; Flags: ignoreversion
Source: "assets\ratt_icon.png"; DestDir: "{autopf}\RATT\assets"; Flags: ignoreversion
Source: "assets\ratt_logo.png"; DestDir: "{autopf}\RATT\assets"; Flags: ignoreversion

[Registry]
Root: HKCR; Subkey: "CLSID\{{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}"; ValueType: string; ValueName: ""; ValueData: "RATT right-click menu"; Flags: uninsdeletekey
Root: HKCR; Subkey: "CLSID\{{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}\InProcServer32"; ValueType: string; ValueName: ""; ValueData: "{autopf}\RATT\ratt_menu.dll"; Flags: uninsdeletekey
Root: HKCR; Subkey: "CLSID\{{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}\InProcServer32"; ValueType: string; ValueName: "ThreadingModel"; ValueData: "Apartment"; Flags: uninsdeletekey
Root: HKCR; Subkey: "*\shellex\ContextMenuHandlers\RATT"; ValueType: string; ValueName: ""; ValueData: "{{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\shellex\ContextMenuHandlers\RATT"; ValueType: string; ValueName: ""; ValueData: "{{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}"; Flags: uninsdeletekey
Root: HKCR; Subkey: "Directory\Background\shellex\ContextMenuHandlers\RATT"; ValueType: string; ValueName: ""; ValueData: "{{B2D6C4A1-3E7F-4C59-9A18-5D0E7F6A4B21}"; Flags: uninsdeletekey

[Icons]
Name: "{group}\RATT"; Filename: "{autopf}\RATT\RATT.exe"
Name: "{autodesktop}\RATT"; Filename: "{autopf}\RATT\RATT.exe"
