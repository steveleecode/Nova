!define APP_NAME "Fathom"
!define APP_VERSION "0.9.0-beta"
!define INSTALL_DIR "$PROGRAMFILES64\${APP_NAME}"

Name "${APP_NAME} ${APP_VERSION}"
OutFile "FathomInstaller.exe"
InstallDir "${INSTALL_DIR}"

SetCompressor /SOLID lzma

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\*.*"
  CreateShortCut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\main.exe"
SectionEnd
