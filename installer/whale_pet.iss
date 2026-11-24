; 鲸鱼娘桌宠 v2.5.0 安装脚本（Inno Setup 6.7.4）
; 编译：tools\inno\ISCC.exe installer\whale_pet.iss

[Setup]
AppName=鲸鱼娘桌宠
AppVersion=2.9.3
AppVerName=鲸鱼娘桌宠 2.9.3
AppPublisher=本地自制
DefaultDirName={localappdata}\WhaleGirlPetApp
DefaultGroupName=鲸鱼娘桌宠
UninstallDisplayIcon={app}\WhaleGirlPet.exe
UninstallDisplayName=鲸鱼娘桌宠 2.9.3
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=WhaleGirlPet-Setup-2.9.3
SetupIconFile=..\assets\ui\pet.ico
DisableProgramGroupPage=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Messages]
ButtonNext=下一步(&N) >
ButtonBack=< 上一步(&B)
ButtonInstall=安装(&I)
ButtonCancel=取消
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
WelcomeLabel1=欢迎安装 鲸鱼娘桌宠
WelcomeLabel2=这个安装包会把桌宠装到本机用户目录，不写系统级配置，卸载时自动清干净。%n%n装完后桌面会出现一个鲸鱼娘图标。
FinishedHeadingLabel=安装完成
FinishedLabel=鲸鱼娘已经装好了。桌面图标点一下就能叫醒她。
SelectDirLabel3=选择安装位置：
SelectDirDesc=默认装在当前用户目录下，不需要管理员权限。
ConfirmUninstall=确定要卸载鲸鱼娘桌宠吗？

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: checkablealone

[Files]
Source: "..\dist\WhaleGirlPet.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\runtime\dafeiyu\*"; DestDir: "{app}\runtime\dafeiyu"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "copy_models.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\鲸鱼娘桌宠"; Filename: "{app}\WhaleGirlPet.exe"; IconFilename: "{app}\WhaleGirlPet.exe"
Name: "{group}\卸载 鲸鱼娘桌宠"; Filename: "{uninstallexe}"
Name: "{autodesktop}\鲸鱼娘桌宠"; Filename: "{app}\WhaleGirlPet.exe"; IconFilename: "{app}\WhaleGirlPet.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\WhaleGirlPet.exe"; Description: "立即叫醒鲸鱼娘"; Flags: nowait postinstall skipifsilent

