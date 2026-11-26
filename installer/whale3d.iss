; 鲸鱼娘 核心包安装脚本（Inno Setup 6）
; 推荐编译：powershell -ExecutionPolicy Bypass -File installer\build_3d_installers.ps1
; 手动编译前先把对应 zip 解压到 build\3d-installer-payload\<版本>，然后：
;   tools\inno\ISCC.exe /DAppVersion=3.1.2 "/DPayloadDir=<绝对路径>" installer\whale3d.iss
; 3.0.28 / 3.1.0 / 3.1.1 / 3.1.2 使用同一个 AppId 与安装目录，后装覆盖升级。
; 如果检测到旧版 2D 3.0.27，默认升级到它所在目录，并由安装器内 migrate_legacy.ps1 直接迁移；旧卸载器有 bug，不再调用。

#ifndef AppVersion
  #define AppVersion "3.1.2"
#endif
#ifndef PayloadDir
  #define PayloadDir "..\3d\_installer\3.1.2"
#endif
#ifndef BuildSuffix
  #define BuildSuffix ""
#endif

[Setup]
AppId=WhaleGirlPet3D
AppName=鲸鱼娘
AppVersion={#AppVersion}
AppVerName=鲸鱼娘 {#AppVersion}
AppPublisher=cnbprd
AppPublisherURL=https://github.com/cnbprd/WhaleGirlPet
AppSupportURL=https://github.com/cnbprd/WhaleGirlPet/issues
AppUpdatesURL=https://github.com/cnbprd/WhaleGirlPet/releases
VersionInfoVersion={#AppVersion}.0
VersionInfoProductVersion={#AppVersion}.0
VersionInfoCompany=cnbprd
VersionInfoDescription=鲸鱼娘 安装包
DefaultDirName={code:GetPreferredDir}
DefaultGroupName=鲸鱼娘
UninstallDisplayIcon={app}\whale3d.exe
UninstallDisplayName=鲸鱼娘 {#AppVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
WizardImageFile=art\wizard_left.png
WizardSmallImageFile=art\wizard_small.png
PrivilegesRequired=lowest
; 3.1.0 已经装过时，Inno 默认会记住上次的 %LOCALAPPDATA% 目录，覆盖 GetPreferredDir 的旧版 2D 检测。
; 这里显式关闭，保证检测到 3.0.27 时目录页默认回到旧版安装目录。
UsePreviousAppDir=no
OutputDir=..\dist\3d
OutputBaseFilename=WhaleGirlPet-Setup-{#AppVersion}{#BuildSuffix}
SetupIconFile=..\3d\assets\ui\pet.ico
LicenseFile=..\LICENSE
DisableWelcomePage=yes
DisableDirPage=no
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
SetupWindowTitle=安装鲸鱼娘 {#AppVersion}
ButtonNext=下一步(&N) >
ButtonBack=< 上一步(&B)
ButtonInstall=开始安装(&I)
ButtonCancel=取消
ButtonFinish=完成(&F)
FinishedHeadingLabel=装好啦
FinishedLabel=鲸鱼娘已经安装到这台电脑。开始菜单或桌面图标点一下就能叫醒她。
ConfirmUninstall=确定卸载鲸鱼娘吗？安装目录和角色资源会被移除。

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
; 安装向导第一页的立绘只嵌入安装包，不落到安装目录
Source: "art\whale.png"; Flags: dontcopy
; 旧版 2D 的卸载器本身有 bug（InitializeUninstall 里调用 ExtractTemporaryFile），
; 不能让它运行；由这个脚本完成保留数据的迁移。
Source: "art\migrate_legacy.ps1"; Flags: dontcopy

[Icons]
Name: "{group}\鲸鱼娘"; Filename: "{app}\whale3d.exe"; IconFilename: "{app}\assets\ui\pet.ico"
Name: "{group}\卸载 鲸鱼娘"; Filename: "{uninstallexe}"; Parameters: "/SILENT"
Name: "{autodesktop}\鲸鱼娘"; Filename: "{app}\whale3d.exe"; IconFilename: "{app}\assets\ui\pet.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\whale3d.exe"; Description: "启动鲸鱼娘"; Flags: nowait postinstall skipifsilent

[Code]
var
  HeroPage: TWizardPage;
  HeroArt: TBitmapImage;
  BtnRemoveLegacy: TNewButton;
  LegacyFound: Boolean;
  LegacyDir: String;
  Existing3D: Boolean;

function GetExisting3DDir(): String;
var
  Loc, Cmd: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\WhaleGirlPet3D_is1',
    'InstallLocation', Loc) and DirExists(Loc) then
    Result := RemoveBackslashUnlessRoot(Loc)
  else if RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\WhaleGirlPet3D_is1',
    'UninstallString', Cmd) then
  begin
    Cmd := RemoveQuotes(Cmd);
    if FileExists(Cmd) then
      Result := ExtractFileDir(Cmd);
  end;
end;

function GetLegacyDir(): String;
var
  Loc, Cmd: String;
begin
  Result := '';
  if RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\鲸鱼娘桌宠_is1',
    'InstallLocation', Loc) then
    Result := RemoveBackslashUnlessRoot(Loc)
  else if RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\鲸鱼娘桌宠_is1',
    'UninstallString', Cmd) then
  begin
    Cmd := RemoveQuotes(Cmd);
    if FileExists(Cmd) then
      Result := ExtractFileDir(Cmd);
  end;
end;

function GetPreferredDir(Param: String): String;
var
  Loc: String;
begin
  // 升级优先沿用当前 3D 安装位置；用户仍可在目录页改成别的文件夹。
  Loc := GetExisting3DDir();
  if Loc <> '' then
    Result := Loc
  else
  begin
    // 首次安装：旧版 2D 位置优先；没有旧版时才用 F 盘，最后回退 LocalAppData。
    if RegQueryStringValue(HKCU,
      'Software\Microsoft\Windows\CurrentVersion\Uninstall\鲸鱼娘桌宠_is1',
      'InstallLocation', Loc) and DirExists(Loc) then
      Result := RemoveBackslashUnlessRoot(Loc)
    else if DirExists('F:\') then
      Result := 'F:\WhaleGirlPetApp'
    else
      Result := ExpandConstant('{localappdata}\WhaleGirlPet3D');
  end;
end;

function MigrateLegacy(): Boolean;
var
  Code: Integer;
  BackupDir, Cmd: String;
begin
  Result := False;
  Log('MigrateLegacy: begin');
  Log('MigrateLegacy: dir=' + LegacyDir);
  if LegacyDir = '' then
    Exit;
  Log('MigrateLegacy: nonempty');
  if not DirExists(LegacyDir) then
    Exit;
  Log('MigrateLegacy: exists');

  BackupDir := LegacyDir + '\WhaleGirlPetApp_userdata_' +
               GetDateTimeString('yyyymmdd-hhnnss', '-', ':');
  Log('MigrateLegacy: backup=' + BackupDir);
  Cmd := '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' +
         ExpandConstant('{tmp}\migrate_legacy.ps1') + '" -AppDir "' +
         LegacyDir + '" -BackupDir "' + BackupDir + '"';
  Log('MigrateLegacy: exec');
  if not Exec('powershell.exe', Cmd, '', SW_HIDE, ewWaitUntilTerminated, Code) then
  begin
    MsgBox('无法启动旧版迁移脚本，数据没有改动。', mbError, MB_OK);
    Exit;
  end;
  Log('MigrateLegacy: exit=' + IntToStr(Code));
  if Code <> 0 then
  begin
    MsgBox('旧版 2D 迁移失败（退出码 ' + IntToStr(Code) +
           '）。迁移脚本会尽量把用户数据放回旧目录；请检查 F 盘旧目录后再重试。',
           mbError, MB_OK);
    Exit;
  end;
  if GetLegacyDir() <> '' then
  begin
    MsgBox('旧版 2D 的卸载登记还在系统里，迁移没有完成。', mbError, MB_OK);
    Exit;
  end;
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  Log('PrepareToInstall: existing3d=' + IntToStr(Ord(Existing3D)) +
      ' legacy=' + IntToStr(Ord(LegacyFound)) +
      ' app=' + ExpandConstant('{app}') + ' legacyDir=' + LegacyDir);
  // 已有 3D 安装时这是覆盖升级：默认目录已经沿用当前安装位置，不再被旧 2D 迁移拦住。
  if Existing3D then
    Exit;
  if not LegacyFound then
    Exit;

  if CompareText(RemoveBackslashUnlessRoot(ExpandConstant('{app}')),
                 RemoveBackslashUnlessRoot(LegacyDir)) <> 0 then
  begin
    Result := '检测到旧版 2D 3.0.27，但本次安装目录不是旧版目录。' + #13#10 +
              '要保留旧版数据升级，请返回目录页，使用默认的旧版目录。' + #13#10 +
              '如果要安装到其他目录，请先手动处理旧版 2D。';
    Exit;
  end;

  if MsgBox('检测到旧版 2D 3.0.27。' + #13#10 +
            '旧版卸载器本身有 bug（会报 ExtractTemporaryFile），不能直接运行。' + #13#10 +
            '安装器会改为直接迁移：保留设置、账号、记忆、语音和模型，' + #13#10 +
            '删除旧程序文件、快捷方式和旧卸载登记，然后继续安装。' + #13#10#13#10 +
            '现在开始迁移并升级吗？', mbConfirmation, MB_YESNO) <> IDYES then
  begin
    Result := '升级已取消。旧版 2D 没有被改动；你可以先退出安装，稍后手动处理。';
    Exit;
  end;

  if not MigrateLegacy() then
  begin
    Result := '旧版 2D 迁移失败，安装已暂停。用户数据应仍在旧目录；请检查后重试。';
    Exit;
  end;

  LegacyFound := False;
  LegacyDir := '';
end;

procedure MigrateLegacyClick(Sender: TObject);
begin
  if MsgBox('这会直接迁移旧版 2D：保留用户数据，删除旧程序、快捷方式和卸载登记。' + #13#10#13#10 +
            '现在迁移吗？', mbConfirmation, MB_YESNO) = IDYES then
  begin
    if MigrateLegacy() then
    begin
      BtnRemoveLegacy.Enabled := False;
      BtnRemoveLegacy.Caption := '旧版 2D 已迁移';
      LegacyFound := False;
      LegacyDir := '';
    end;
  end;
end;

procedure InitializeWizard();
var
  Png: TPngImage;
  Title, SubTitle, Body, Hint: TNewStaticText;
begin
  ExtractTemporaryFile('whale.png');
  ExtractTemporaryFile('migrate_legacy.ps1');
  LegacyDir := GetLegacyDir();
  Existing3D := GetExisting3DDir() <> '';
  LegacyFound := (LegacyDir <> '') and (not Existing3D);

  HeroPage := CreateCustomPage(wpWelcome, '鲸鱼娘', '先认识一下，再开始安装');

  HeroArt := TBitmapImage.Create(HeroPage);
  HeroArt.Parent := HeroPage.Surface;
  HeroArt.Left := 8;
  HeroArt.Top := 4;
  HeroArt.Width := 150;
  HeroArt.Height := 280;
  HeroArt.Stretch := True;
  HeroArt.BackColor := clWhite;
  Png := TPngImage.Create;
  try
    Png.LoadFromFile(ExpandConstant('{tmp}\whale.png'));
    HeroArt.Bitmap.Assign(Png);
  finally
    Png.Free;
  end;

  Title := TNewStaticText.Create(HeroPage);
  Title.Parent := HeroPage.Surface;
  Title.Left := 178;
  Title.Top := 8;
  Title.Width := 230;
  Title.Height := 34;
  Title.Caption := '鲸鱼娘';
  Title.Font.Name := 'Microsoft YaHei UI';
  Title.Font.Size := 18;
  Title.Font.Style := [fsBold];

  SubTitle := TNewStaticText.Create(HeroPage);
  SubTitle.Parent := HeroPage.Surface;
  SubTitle.Left := 178;
  SubTitle.Top := 44;
  SubTitle.Width := 230;
  SubTitle.Height := 22;
  SubTitle.Caption := 'v{#AppVersion} · 主程序';
  SubTitle.Font.Name := 'Microsoft YaHei UI';
  SubTitle.Font.Size := 9;
  SubTitle.Font.Color := $00777777;

  Body := TNewStaticText.Create(HeroPage);
  Body.Parent := HeroPage.Surface;
  Body.Left := 178;
  Body.Top := 76;
  Body.Width := 230;
  Body.Height := 76;
  Body.AutoSize := False;
  Body.WordWrap := True;
  Body.Caption := '透明置顶、VRM 身体、头发和尾巴弹簧、托盘菜单与设置页。' + #13#10 +
                  '升级时默认沿用当前安装目录，也可以在这里改；不需要管理员权限。';
  Body.Font.Name := 'Microsoft YaHei UI';
  Body.Font.Size := 9;

  Hint := TNewStaticText.Create(HeroPage);
  Hint.Parent := HeroPage.Surface;
  Hint.Left := 178;
  Hint.Top := 158;
  Hint.Width := 230;
  Hint.Height := 74;
  Hint.AutoSize := False;
  Hint.WordWrap := True;
  Hint.Font.Name := 'Microsoft YaHei UI';
  Hint.Font.Size := 9;
  if LegacyFound then
    Hint.Caption := '检测到旧版 2D 3.0.27。旧版卸载器本身有 bug，不能直接运行；' +
                    '默认升级到旧版目录，点下面按钮由安装器迁移并保留数据。'
  else if Existing3D then
    Hint.Caption := '检测到已安装的 3D 版本，默认沿用当前安装目录；' +
                    '想换位置可以在目录页修改。'
  else
    Hint.Caption := '没有检测到旧版安装，直接安装即可。';

  if LegacyFound then
  begin
    BtnRemoveLegacy := TNewButton.Create(HeroPage);
    BtnRemoveLegacy.Parent := HeroPage.Surface;
    BtnRemoveLegacy.Left := 178;
    BtnRemoveLegacy.Top := 238;
    BtnRemoveLegacy.Width := 170;
    BtnRemoveLegacy.Height := 30;
    BtnRemoveLegacy.Caption := '迁移旧版 2D（保留数据）…';
    BtnRemoveLegacy.OnClick := @MigrateLegacyClick;
  end;
  WizardForm.Show;
end;
