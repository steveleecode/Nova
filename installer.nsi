Outfile "StorageAssistantSetup.exe"
InstallDir $PROGRAMFILES\StorageAssistant
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
  SetOutPath $INSTDIR
  File "build\main.exe"
  CreateShortcut "$DESKTOP\StorageAssistant.lnk" "$INSTDIR\main.exe"
SectionEnd
