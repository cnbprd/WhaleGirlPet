; 鲸鱼娘桌宠 安装脚本（Inno Setup 6.7.4）· v3.0.7 对话气泡式向导
; 编译：tools\inno\ISCC.exe installer\whale_pet.iss
; 说明：不再用 Inno 默认的"欢迎/选择目录/任务/准备"四页，
;       改成大肥鱼站在右侧、左侧气泡提问的四问流程（位置 / 桌面图标 / 装完叫醒 / 选装本地模型）。

[Setup]
AppName=鲸鱼娘桌宠
AppVersion=3.0.7
AppVerName=鲸鱼娘桌宠 3.0.7
AppPublisher=本地自制
DefaultDirName={localappdata}\WhaleGirlPetApp
DefaultGroupName=鲸鱼娘桌宠
UninstallDisplayIcon={app}\WhaleGirlPet.exe
UninstallDisplayName=鲸鱼娘桌宠 3.0.7
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=WhaleGirlPet-Setup-3.0.7
SetupIconFile=..\assets\ui\pet.ico
WizardSmallImageFile=art\small_blank.png
DisableWelcomePage=yes
DisableDirPage=yes
DisableProgramGroupPage=yes
DisableReadyPage=yes
DisableFinishedPage=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
RestartApplications=no

[Messages]
ButtonNext=下一步(&N) >
ButtonBack=< 上一步(&B)
ButtonInstall=开始装(&I)
ButtonCancel=取消
ButtonFinish=完成(&F)
ButtonBrowse=浏览(&B)...
FinishedHeadingLabel=装好啦
FinishedLabel=大肥鱼已经住进这台电脑了。桌面图标点一下就能叫醒她。
ConfirmUninstall=确定要把大肥鱼请出去吗？
SetupWindowTitle=Setup: 鲸鱼娘桌宠 3.0.7

[Files]
Source: "..\dist\WhaleGirlPet.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\runtime\dafeiyu\*"; DestDir: "{app}\runtime\dafeiyu"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "copy_models.cmd"; DestDir: "{app}"; Flags: ignoreversion
; 向导美术：只嵌入安装包，运行时由 ExtractTemporaryFile 释放，不落到安装目录
Source: "art\whale.png"; Flags: dontcopy
Source: "art\bubble.png"; Flags: dontcopy
Source: "art\idle_close.ps1"; Flags: dontcopy

[Icons]
Name: "{group}\鲸鱼娘桌宠"; Filename: "{app}\WhaleGirlPet.exe"; IconFilename: "{app}\WhaleGirlPet.exe"
Name: "{group}\卸载 鲸鱼娘桌宠"; Filename: "{uninstallexe}"
Name: "{autodesktop}\鲸鱼娘桌宠"; Filename: "{app}\WhaleGirlPet.exe"; IconFilename: "{app}\WhaleGirlPet.exe"; Check: NeedDesktopIcon

[Code]
var
  PageWhere, PageIcon, PageWake, PageModel: TWizardPage;
  BmpWhale: array[0..3] of TBitmapImage;
  BmpBubble: array[0..3] of TBitmapImage;
  LblAsk: array[0..3] of TNewStaticText;
  LblSub: array[0..3] of TNewStaticText;
  BtnA: array[0..3] of TNewButton;
  BtnB: array[0..3] of TNewButton;
  WantDesktopIcon, WantWake, WantLocalModel: Boolean;
  SetupName: String;
  IdleResult: Integer;
  DirBefore: String;

function NeedDesktopIcon: Boolean;
begin
  Result := WantDesktopIcon;
end;

{ ---- 工具：在页面上摆一张透明 PNG ---- }
function PutArt(APage: TWizardPage; const AFile: String; ALeft, ATop, AWidth,
  AHeight: Integer): TBitmapImage;
var
  Png: TPngImage;
begin
  Result := TBitmapImage.Create(APage);
  Result.Parent := APage.Surface;
  Result.Left := ALeft;
  Result.Top := ATop;
  Result.Width := AWidth;
  Result.Height := AHeight;
  Result.Stretch := True;
  Result.BackColor := clNone;
  Png := TPngImage.Create;
  try
    Png.LoadFromFile(AFile);
    Result.Bitmap.Assign(Png);
  finally
    Png.Free;
  end;
end;

function PutText(APage: TWizardPage; const AText: String; ALeft, ATop, AWidth,
  AFontSize: Integer; ABold: Boolean; AColor: TColor): TNewStaticText;
begin
  Result := TNewStaticText.Create(APage);
  Result.Parent := APage.Surface;
  Result.Left := ALeft;
  Result.Top := ATop;
  Result.Width := AWidth;
  Result.AutoSize := False;
  Result.WordWrap := True;
  Result.Caption := AText;
  Result.Font.Name := 'Microsoft YaHei UI';
  Result.Font.Size := AFontSize;
  Result.Font.Style := [fsBold];
  if not ABold then
    Result.Font.Style := [];
  Result.Font.Color := AColor;
end;

function PutBtn(APage: TWizardPage; const ACaption: String; ALeft, ATop,
  AWidth: Integer): TNewButton;
begin
  Result := TNewButton.Create(APage);
  Result.Parent := APage.Surface;
  Result.Left := ALeft;
  Result.Top := ATop;
  Result.Width := AWidth;
  Result.Height := 30;
  Result.Caption := ACaption;
  Result.Font.Name := 'Microsoft YaHei UI';
  Result.Font.Size := 9;
end;

{ ---- 页 1：装到哪儿 ---- }
procedure WhereUseDefault(Sender: TObject);
begin
  WizardForm.DirEdit.Text := ExpandConstant('{localappdata}\WhaleGirlPetApp');
  if Assigned(LblSub[0]) then
    LblSub[0].Caption := '那就装到：' + WizardForm.DirEdit.Text;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

procedure WardCreateDir(const Dir: String);
begin
  if not DirExists(Dir) then
    ForceDirectories(Dir);
end;

procedure WherePickFolder(Sender: TObject);
var
  Dir: String;
begin
  DirBefore := WizardForm.DirEdit.Text;
  { 借用被隐藏的"浏览"按钮，弹系统目录选择框；取消时文本不变 }
  if WizardForm.DirBrowseButton <> nil then
    WizardForm.DirBrowseButton.OnClick(WizardForm.DirBrowseButton);
  Dir := WizardForm.DirEdit.Text;
  if Dir <> DirBefore then
  begin
    { 用户只选了盘根（如 D:\）→ 自动补一个 WhaleGirlPetApp 子目录并建好，
      不用他自己新建文件夹；选了具体目录就照那个目录建 }
    if (Length(Dir) = 3) and (Dir[2] = ':') and (Dir[3] = '\') then
    begin
      Dir := Dir + 'WhaleGirlPetApp';
      WardCreateDir(Dir);
      WizardForm.DirEdit.Text := Dir;
    end
    else
      WardCreateDir(Dir);
    if Assigned(LblSub[0]) then
      LblSub[0].Caption := '好，就装到：' + WizardForm.DirEdit.Text;
    WizardForm.NextButton.OnClick(WizardForm.NextButton);
  end;
end;

{ ---- 页 2：桌面图标 ---- }
procedure IconYes(Sender: TObject);
begin
  WantDesktopIcon := True;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

procedure IconNo(Sender: TObject);
begin
  WantDesktopIcon := False;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

{ ---- 页 3：装完叫醒 ---- }
procedure WakeYes(Sender: TObject);
begin
  WantWake := True;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

procedure WakeNo(Sender: TObject);
begin
  WantWake := False;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

{ ---- 页 4：选装本地模型服务 ---- }
procedure ModelYes(Sender: TObject);
begin
  WantLocalModel := True;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

procedure ModelNo(Sender: TObject);
begin
  WantLocalModel := False;
  WizardForm.NextButton.OnClick(WizardForm.NextButton);
end;

{ ---- 统一的页面搭建：右侧立绘 + 左侧气泡 + 问题 + 两个选项 ---- }
procedure BuildPage(APage: TWizardPage; AIndex: Integer; const AAsk, ASub: String;
  const ACapA, ACapB: String);
var
  SW, SH, ArtW, BubW, BubH, QW: Integer;
begin
  SW := APage.Surface.Width;
  SH := APage.Surface.Height;
  if SW <= 0 then
    SW := 420;
  if SH <= 0 then
    SH := 285;

  ArtW := (SH * 468) div 980;
  if ArtW < 96 then
    ArtW := 96;

  { 右侧立绘：贴底对齐，像站在页面右边 }
  BmpWhale[AIndex] := PutArt(APage, ExpandConstant('{tmp}\whale.png'),
    SW - ArtW - 2, SH - SH + 2, ArtW, SH - 4);

  BubW := SW - ArtW - 16;
  if BubW < 220 then
    BubW := 220;
  BubH := (BubW * 400) div 640;
  BmpBubble[AIndex] := PutArt(APage, ExpandConstant('{tmp}\bubble.png'),
    2, 10, BubW, BubH);

  QW := BubW - 70;
  LblAsk[AIndex] := PutText(APage, AAsk, 30, 26, QW, 12, True, clBlack);
  LblSub[AIndex] := PutText(APage, ASub, 30, 54, QW, 9, False, $00666A70);
  { 副标题可能换行：给两行高度，否则第二行会被按钮盖掉 }
  LblSub[AIndex].Height := 38;

  BtnA[AIndex] := PutBtn(APage, ACapA, 28, 96, 132);
  BtnB[AIndex] := PutBtn(APage, ACapB, 168, 96, 132);
end;

procedure InitializeWizard;
begin
  WantDesktopIcon := True;
  WantWake := True;
  WantLocalModel := False;
  { 安装器进程名（看门狗用它判断窗口还在不在） }
  SetupName := ChangeFileExt(ExtractFileName(ExpandConstant('{srcexe}')), '');

  { 从安装包体内释放图片与看门狗脚本到临时目录，供页面控件/后台进程使用 }
  ExtractTemporaryFile('whale.png');
  ExtractTemporaryFile('bubble.png');

  PageWhere := CreateCustomPage(wpWelcome, '', '');
  PageIcon := CreateCustomPage(PageWhere.ID, '', '');
  PageWake := CreateCustomPage(PageIcon.ID, '', '');
  PageModel := CreateCustomPage(PageWake.ID, '', '');

  BuildPage(PageWhere, 0, '要把我装到哪儿呀？',
    '默认装在你自己的目录里；选盘符会自动建 WhaleGirlPetApp 文件夹。',
    '就用默认位置', '浏览…选盘');
  BuildPage(PageIcon, 1, '要在桌面上放个快捷方式吗？',
    '放一个，以后点一下就能叫我出来。',
    '要，方便找你', '不用啦');
  BuildPage(PageWake, 2, '装好了要马上叫醒我吗？',
    '选"马上"的话，装完我就自己跳出来。',
    '现在就醒', '下次再说');
  BuildPage(PageModel, 3, '要不要顺手装个本地模型？',
    '装完自动下，约 1–4.5GB；先不装也行，之后到设置里补。',
    '要，装一个', '先不装');

  BtnA[0].OnClick := @WhereUseDefault;
  BtnB[0].OnClick := @WherePickFolder;
  BtnA[1].OnClick := @IconYes;
  BtnB[1].OnClick := @IconNo;
  BtnA[2].OnClick := @WakeYes;
  BtnB[2].OnClick := @WakeNo;
  BtnA[3].OnClick := @ModelYes;
  BtnB[3].OnClick := @ModelNo;

  { 页 1 的路径提示先给出默认值 }
  LblSub[0].Caption := '默认装到：' + WizardForm.DirEdit.Text;

  { 30 分钟没人动电脑就把安装窗口关掉：Inno 6 没有定时器，
    这里放一个小看门狗脚本（只杀"还没开始装文件"的窗口，安装开始后会自己退出） }
  ExtractTemporaryFile('idle_close.ps1');
  Exec('powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' +
    ExpandConstant('{tmp}\idle_close.ps1') + '" -Name "' + SetupName + '"',
    '', SW_HIDE, ewNoWait, IdleResult);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  R: Integer;
begin
  { 一进入真正装文件的阶段，就给看门狗打标记，让它别杀进程 }
  if CurStep = ssInstall then
    SaveStringToFile(ExpandConstant('{tmp}\installing.flag'), '1', False);

  { 选了"要，装一个"→ 留一个标记，程序第一次启动时自己去下本地模型 }
  if (CurStep = ssPostInstall) and WantLocalModel then
    SaveStringToFile(ExpandConstant('{app}\want_local_model.flag'), '1', False);

  if (CurStep = ssPostInstall) and WantWake then
    Exec(ExpandConstant('{app}\WhaleGirlPet.exe'), '', '', SW_SHOWNORMAL,
      ewNoWait, R);
end;

{ 只留三张自定页 + 安装进度 + 完成页 }
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpSelectTasks) or (PageID = wpSelectProgramGroup);
end;




