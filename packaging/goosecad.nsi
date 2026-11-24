Unicode true
RequestExecutionLevel user
!include "MUI2.nsh"
!include "x64.nsh"
!include "WinVer.nsh"

!ifndef BUNDLE
  !error "BUNDLE required"
!endif
!ifndef UNINSTALL_LIST
  !error "UNINSTALL_LIST required"
!endif
!ifndef OUTPUT
  !error "OUTPUT required"
!endif
Name "GooseCAD Professional 0.1.0-alpha.1 (experimental)"
OutFile "${OUTPUT}"
InstallDir "$LOCALAPPDATA\Programs\GooseCAD Professional 0.1.0-alpha.1"
SetCompressor zlib
ShowInstDetails show
ShowUninstDetails show
!define MUI_ABORTWARNING
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "Spanish"

Function .onInit
  SetShellVarContext current
  ${IfNot} ${RunningX64}
    MessageBox MB_ICONSTOP "Se requiere Windows x64." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
  ${IfNot} ${AtLeastWin10}
    MessageBox MB_ICONSTOP "Se requiere Windows 10 o posterior." /SD IDOK
    SetErrorLevel 2
    Abort
  ${EndIf}
FunctionEnd

Section "GooseCAD Professional" Main
  SetShellVarContext current
  IfFileExists "$INSTDIR\*.*" 0 fresh
    MessageBox MB_ICONSTOP "El directorio debe estar vacío. Desinstale la versión anterior o elija otro directorio." /SD IDOK
    SetErrorLevel 3
    Abort
  fresh:
  SetOutPath "$INSTDIR"
  File /r "${BUNDLE}\*.*"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
  CreateDirectory "$SMPROGRAMS\GooseCAD Professional Experimental"
  CreateShortCut "$SMPROGRAMS\GooseCAD Professional Experimental\GooseCAD Professional.lnk" "$INSTDIR\GooseCAD.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GooseCADProfessionalExperimental" "DisplayName" "GooseCAD Professional Experimental"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GooseCADProfessionalExperimental" "DisplayVersion" "0.1.0-alpha.1"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GooseCADProfessionalExperimental" "UninstallString" '$\"$INSTDIR\Uninstall.exe$\"'
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GooseCADProfessionalExperimental" "InstallLocation" "$INSTDIR"
SectionEnd

Section "Uninstall"
  SetShellVarContext current
  !include "${UNINSTALL_LIST}"
  Delete "$INSTDIR\Uninstall.exe"
  Delete "$SMPROGRAMS\GooseCAD Professional Experimental\GooseCAD Professional.lnk"
  RMDir "$SMPROGRAMS\GooseCAD Professional Experimental"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\GooseCADProfessionalExperimental"
  RMDir "$INSTDIR"
SectionEnd
