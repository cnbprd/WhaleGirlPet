; 鲸鱼娘 3D 核心包安装脚本（Inno Setup 6）
; 推荐编译：powershell -ExecutionPolicy Bypass -File installer\build_3d_installers.ps1
; 手动编译前先把对应 zip 解压到 build\3d-installer-payload\<版本>，然后：
;   tools\inno\ISCC.exe /DAppVersion=3.1.0 "/DPayloadDir=<绝对路径>" installer\whale3d.iss
; 两个版本使用同一个 AppId / 默认目录：安装 3.1.0 会覆盖升级 3.0.28。

#ifndef AppVersion
  #define AppVersion "3.1.0"
#endif
#ifndef PayloadDir
  #define PayloadDir "..\3d\_installer\3.1.0"
#endif

[Setup]
AppId=WhaleGirlPet3D
AppName=鲸鱼娘 3D
AppVersion={#AppVersion}
AppVerName=鲸鱼娘 3D {#AppVersion}
AppPublisher=cnbprd
AppPublisherURL=https://github.com/cnbprd/WhaleGirlPet
AppSupportURL=https://github.com/cnbprd/WhaleGirlPet/issues
AppUpdatesURL=https://github.com/cnbprd/WhaleGirlPet/releases
VersionInfoVersion={#AppVersion}
VersionInfoProductVersion={#AppVersion}
VersionInfoCompany=cnbprd
VersionInfoDescription=鲸鱼娘 3D 安装包
DefaultDirName={localappdata}\WhaleGirlPet3D
DefaultGroupName=鲸鱼娘 3D
UninstallDisplayIcon={app}\whale3d.exe
UninstallDisplayName=鲸鱼娘 3D {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
OutputDir=..\dist\3d
OutputBaseFilename=WhaleGirlPet-3D-Setup-{#AppVersion}
SetupIconFile=..\3d\assets\ui\pet.ico
LicenseFile=..\LICENSE
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Messages]
SetupWindowTitle=安装鲸鱼娘 3D {#AppVersion}
ButtonNext=下一步(&N) >
ButtonBack=< 上一步(&B)
ButtonInstall=开始安装(&I)
ButtonCancel=取消
ButtonFinish=完成(&F)
FinishedHeadingLabel=装好啦
FinishedLabel=鲸鱼娘 3D 已经安装到这台电脑。开始菜单或桌面图标点一下就能叫醒她。
ConfirmUninstall=确定卸载鲸鱼娘 3D 吗？安装目录和角色资源会被移除。

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\鲸鱼娘 3D"; Filename: "{app}\whale3d.exe"; IconFilename: "{app}\assets\ui\pet.ico"
Name: "{group}\卸载 鲸鱼娘 3D"; Filename: "{uninstallexe}"; Parameters: "/SILENT"
Name: "{autodesktop}\鲸鱼娘 3D"; Filename: "{app}\whale3d.exe"; IconFilename: "{app}\assets\ui\pet.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\whale3d.exe"; Description: "启动鲸鱼娘 3D"; Flags: nowait postinstall skipifsilent
