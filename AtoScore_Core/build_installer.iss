; atoscore V3 - Inno Setup Script
; This creates a professional Windows installer for atoscore

#define MyAppName "NC- AtoScore"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "NC-Engineering"
#define MyAppURL "https://github.com/your-repo/atoscore"
#define MyAppExeName "atoscore.bat"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{8A9B7C6D-5E4F-3A2B-1C0D-9E8F7A6B5C4D}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=README.md
OutputDir=installer_output
OutputBaseFilename=atoscore_V3_Setup
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin
MinVersion=10.0.17763
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files
Source: "dist\atoscore\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\atoscore.exe"
Name: "{group}\Documentation"; Filename: "{app}\START_HERE.txt"
Name: "{group}\User Guide"; Filename: "{app}\HowToUse.md"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\atoscore.exe"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "{app}\atoscore.exe"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec postinstall skipifsilent nowait

[Code]
var
  GPUCheckPage: TOutputMsgMemoWizardPage;
  HasNVIDIAGPU: Boolean;

function CheckForNVIDIAGPU: Boolean;
var
  ResultCode: Integer;
  Output: AnsiString;
  TempFile: String;
begin
  Result := False;
  TempFile := ExpandConstant('{tmp}\gpu_check.txt');
  
  // Try to detect NVIDIA GPU using wmic
  if Exec('cmd.exe', '/c wmic path win32_VideoController get name > "' + TempFile + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if LoadStringFromFile(TempFile, Output) then
    begin
      if Pos('NVIDIA', String(Output)) > 0 then
        Result := True;
    end;
    DeleteFile(TempFile);
  end;
end;

procedure InitializeWizard;
begin
  // Create a custom page for GPU information
  GPUCheckPage := CreateOutputMsgMemoPage(wpWelcome,
    'GPU Detection', 
    'Checking for NVIDIA GPU support',
    'NC- AtoScore can use GPU acceleration for faster transcription. ' +
    'Please wait while we check your system...',
    '');
end;

procedure CurPageChanged(CurPageID: Integer);
var
  GPUStatus: String;
begin
  if CurPageID = GPUCheckPage.ID then
  begin
    HasNVIDIAGPU := CheckForNVIDIAGPU;
    
    if HasNVIDIAGPU then
    begin
      GPUStatus := '✓ NVIDIA GPU Detected!' + #13#10 + #13#10 +
                   'Your system is equipped with an NVIDIA GPU. Sheet Sage will ' +
                   'automatically use GPU acceleration for improved performance.' + #13#10 + #13#10 +
                   'Supported Features:' + #13#10 +
                   '  • Basic Pitch: GPU accelerated' + #13#10 +
                   '  • Sheet Sage V3 (Lunaverus): GPU accelerated' + #13#10 +
                   '  • Demucs: GPU accelerated' + #13#10 +
                   '  • Omnizart: CPU only (due to CUDA compatibility)';
    end
    else
    begin
      GPUStatus := '⚠ No NVIDIA GPU Detected' + #13#10 + #13#10 +
                   'Sheet Sage will run in CPU-only mode. Transcription will be ' +
                   'slower but fully functional.' + #13#10 + #13#10 +
                   'For best performance, an NVIDIA GPU with 6GB+ VRAM is recommended.' + #13#10 + #13#10 +
                   'Note: If you have an NVIDIA GPU but it wasn''t detected, please ' +
                   'ensure your NVIDIA drivers are up to date.';
    end;
    
    GPUCheckPage.RichEditViewer.Text := GPUStatus;
  end;
end;

function NeedRestart: Boolean;
begin
  Result := False;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Create output directories
    CreateDir(ExpandConstant('{app}\output'));
    CreateDir(ExpandConstant('{app}\temp'));
    CreateDir(ExpandConstant('{app}\temp_playback'));
    CreateDir(ExpandConstant('{app}\cache'));
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nNC- AtoScore is an AI-powered music transcription suite that converts audio to sheet music using state-of-the-art machine learning models.%n%nIt is recommended that you close all other applications before continuing.
FinishedHeadingLabel=Completing the [name] Setup Wizard
FinishedLabelNoIcons=Setup has finished installing [name] on your computer.%n%nRecommended: Read the START_HERE.txt file for important usage information.

[UninstallDelete]
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\temp_playback"
Type: filesandordirs; Name: "{app}\cache"
Type: filesandordirs; Name: "{app}\output"

