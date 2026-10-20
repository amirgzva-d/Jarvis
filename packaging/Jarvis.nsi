Unicode True
!include "MUI2.nsh"
Name "Jarvis"
OutFile "..\dist\Jarvis-Setup-1.1.0.exe"
InstallDir "$LOCALAPPDATA\Programs\Jarvis"
RequestExecutionLevel user
SetCompressor /SOLID lzma
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
Section "Install"
  SetOutPath "$INSTDIR"
  File "..\dist\Jarvis.exe"
  CreateDirectory "$SMPROGRAMS\Jarvis"
  CreateShortcut "$SMPROGRAMS\Jarvis\Jarvis.lnk" "$INSTDIR\Jarvis.exe"
  CreateShortcut "$DESKTOP\Jarvis.lnk" "$INSTDIR\Jarvis.exe"
  WriteUninstaller "$INSTDIR\Uninstall-Jarvis.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Jarvis" "DisplayName" "Jarvis"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Jarvis" "UninstallString" '"$INSTDIR\Uninstall-Jarvis.exe"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Jarvis" "DisplayVersion" "1.1.0"
SectionEnd
Section "Uninstall"
  Delete "$INSTDIR\Jarvis.exe"
  Delete "$INSTDIR\Uninstall-Jarvis.exe"
  RMDir "$INSTDIR"
  Delete "$SMPROGRAMS\Jarvis\Jarvis.lnk"
  RMDir "$SMPROGRAMS\Jarvis"
  Delete "$DESKTOP\Jarvis.lnk"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\Jarvis"
  ; Deliberately KEEP $LOCALAPPDATA\Jarvis (private notes, settings, memory).
SectionEnd
