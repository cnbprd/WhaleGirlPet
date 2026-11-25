; 鲸鱼娘桌宠 安装脚本（Inno Setup 6.7.4）
; 编译：tools\inno\ISCC.exe installer\whale_pet.iss
; v3.0.23（第 1 条）：按用户手绘稿重做——左侧大肥鱼立绘 + 右侧提问；
;   安装中页只留大肥鱼和“安装中…”；卸载加“是否保留数据”，并带哭脸动画。

[Setup]
AppName=鲸鱼娘桌宠
; v3.0.24：动作导演第一版（Action 卡 + Director 仲裁），安装器界面沿用 v3.0.23。
AppVersion=3.0.24
AppVerName=鲸鱼娘桌宠 3.0.24
AppPublisher=本地自制
DefaultDirName={localappdata}\WhaleGirlPetApp
DefaultGroupName=鲸鱼娘桌宠
UninstallDisplayIcon={app}\WhaleGirlPet.exe
UninstallDisplayName=鲸鱼娘桌宠 3.0.24
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=WhaleGirlPet-Setup-3.0.24
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
ConfirmUninstall=你确定要卸载吗？卸载后大肥鱼就不在这台电脑上了。
SetupWindowTitle=Setup: 鲸鱼娘桌宠 3.0.24

[Files]
; v3.0.19：onedir —— 安装包内容 = dist\WhaleGirlPet\ 整个目录（exe + _internal）
Source: "..\dist\WhaleGirlPet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\runtime\dafeiyu\*"; DestDir: "{app}\runtime\dafeiyu"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist
Source: "copy_models.cmd"; DestDir: "{app}"; Flags: ignoreversion
; 向导/卸载美术：只嵌入安装包，运行时由 ExtractTemporaryFile 释放，不落到安装目录
Source: "art\whale.png"; Flags: dontcopy
Source: "art\whale_cry1.png"; Flags: dontcopy
Source: "art\whale_cry2.png"; Flags: dontcopy
Source: "art\idle_close.ps1"; Flags: dontcopy
Source: "art\keep_data.ps1"; Flags: dontcopy

[Icons]
Name: "{group}\鲸鱼娘桌宠"; Filename: "{app}\WhaleGirlPet.exe"; IconFilename: "{app}\WhaleGirlPet.exe"
Name: "{group}\卸载 鲸鱼娘桌宠"; Filename: "{uninstallexe}"; Parameters: "/SILENT"
Name: "{autodesktop}\鲸鱼娘桌宠"; Filename: "{app}\WhaleGirlPet.exe"; IconFilename: "{app}\WhaleGirlPet.exe"; Check: NeedDesktopIcon

[Code]
var
  PageWhere, PageIcon, PageWake, PageModel: TWizardPage;
  BmpWhale: array[0..3] of TBitmapImage;
  LblAsk: array[0..3] of TNewStaticText;
  LblSub: array[0..3] of TNewStaticText;
  BtnA: array[0..3] of TNewButton;
  BtnB: array[0..3] of TNewButton;
  LblPath: TNewStaticText;
  InstallArt: TBitmapImage;
  InstallTxt, InstallSub: TNewStaticText;
  WantDesktopIcon, WantWake, WantLocalModel: Boolean;
  SetupName: String;
  IdleResult: Integer;
  DirBefore: String;
  { 卸载对话框 }
  AskForm: TSetupForm;
  CryImage: TBitmapImage;
  CryIndex, CryTimer: Longword;
  AskResult: Boolean;
  KeepData: Boolean;
  KeepDataAsked: Boolean;
  BackupDir: String;

function SetTimer(hWnd, nIDEvent, uElapse, lpTimerFunc: Longword): Longword;
external 'SetTimer@user32.dll stdcall';
function KillTimer(hWnd, nIDEvent: Longword): Bool;
external 'KillTimer@user32.dll stdcall';

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
  Result.Height := 32;
  Result.Caption := ACaption;
  Result.Font.Name := 'Microsoft YaHei UI';
  Result.Font.Size := 9;
end;

{ ---- 页 1：装到哪儿 ---- }
procedure WhereUseDefault(Sender: TObject);
begin
  WizardForm.DirEdit.Text := ExpandConstant('{localappdata}\WhaleGirlPetApp');
  LblPath.Caption := '装到：' + WizardForm.DirEdit.Text;
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
    { 用户只选了盘根（如 D:\）→ 自动补一个 WhaleGirlPetApp 子目录并建好 }
    if (Length(Dir) = 3) and (Dir[2] = ':') and (Dir[3] = '\') then
    begin
      Dir := Dir + 'WhaleGirlPetApp';
      WardCreateDir(Dir);
      WizardForm.DirEdit.Text := Dir;
    end
    else
      WardCreateDir(Dir);
    LblPath.Caption := '装到：' + WizardForm.DirEdit.Text;
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

{ ---- 统一的页面搭建：左侧大肥鱼 + 右侧提问 + 两个选项 ---- }
procedure BuildPage(APage: TWizardPage; AIndex: Integer; const AAsk, ASub: String;
  const ACapA, ACapB: String);
var
  SW, SH, ArtW, TX, TW: Integer;
begin
  SW := APage.Surface.Width;
  SH := APage.Surface.Height;
  if SW <= 0 then
    SW := 420;
  if SH <= 0 then
    SH := 285;

  { 立绘贴底站在左侧，高度占满页面，宽度按 468:980 等比 }
  ArtW := ((SH - 4) * 468) div 980;
  if ArtW < 90 then
    ArtW := 90;
  BmpWhale[AIndex] := PutArt(APage, ExpandConstant('{tmp}\whale.png'),
    4, SH - (SH - 4), ArtW, SH - 4);

  TX := ArtW + 22;
  TW := SW - TX - 16;
  if TW < 180 then
    TW := 180;

  LblAsk[AIndex] := PutText(APage, AAsk, TX, 34, TW, 13, True, clBlack);
  LblSub[AIndex] := PutText(APage, ASub, TX, 70, TW, 9, False, $00555555);
  LblSub[AIndex].Height := 56;

  BtnA[AIndex] := PutBtn(APage, ACapA, TX, 140, 106);
  BtnB[AIndex] := PutBtn(APage, ACapB, TX + 116, 140, 106);
end;

procedure InitializeWizard;
begin
  WantDesktopIcon := True;
  WantWake := True;
  WantLocalModel := False;
  SetupName := ChangeFileExt(ExtractFileName(ExpandConstant('{srcexe}')), '');

  { 从安装包体内释放图片与脚本到临时目录 }
  ExtractTemporaryFile('whale.png');
  ExtractTemporaryFile('whale_cry1.png');
  ExtractTemporaryFile('whale_cry2.png');
  ExtractTemporaryFile('idle_close.ps1');
  ExtractTemporaryFile('keep_data.ps1');

  PageWhere := CreateCustomPage(wpWelcome, '', '');
  PageIcon := CreateCustomPage(PageWhere.ID, '', '');
  PageWake := CreateCustomPage(PageIcon.ID, '', '');
  PageModel := CreateCustomPage(PageWake.ID, '', '');

  BuildPage(PageWhere, 0, '要把我装到哪儿呀？',
    '默认装在你自己的目录里；选盘符会自动建 WhaleGirlPetApp 文件夹。',
    '就用默认位置', '浏览…选盘');
  { 页 1 单独加一行当前路径，按钮往上挪一点 }
  LblPath := PutText(PageWhere, '装到：' + WizardForm.DirEdit.Text,
    BmpWhale[0].Left + BmpWhale[0].Width + 22, 98, 220, 9, False, $00303030);
  LblPath.Height := 34;
  BtnA[0].Top := 140;
  BtnB[0].Top := 140;

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

  { 安装中页：只留大肥鱼 + “安装中…”，把进度条和文件行藏起来 }
  InstallArt := TBitmapImage.Create(WizardForm.InstallingPage);
  InstallArt.Parent := WizardForm.InstallingPage;
  InstallArt.Left := 16;
  InstallArt.Top := 4;
  InstallArt.Width := 160;
  InstallArt.Height := 270;
  InstallArt.Stretch := True;
  InstallArt.BackColor := clNone;
  InstallArt.Bitmap.Assign(BmpWhale[0].Bitmap);

  InstallTxt := TNewStaticText.Create(WizardForm.InstallingPage);
  InstallTxt.Parent := WizardForm.InstallingPage;
  InstallTxt.Left := 200;
  InstallTxt.Top := 100;
  InstallTxt.Width := 200;
  InstallTxt.AutoSize := False;
  InstallTxt.Caption := '安装中…';
  InstallTxt.Font.Name := 'Microsoft YaHei UI';
  InstallTxt.Font.Size := 18;
  InstallTxt.Font.Style := [fsBold];
  InstallTxt.Font.Color := clBlack;

  InstallSub := TNewStaticText.Create(WizardForm.InstallingPage);
  InstallSub.Parent := WizardForm.InstallingPage;
  InstallSub.Left := 200;
  InstallSub.Top := 140;
  InstallSub.Width := 200;
  InstallSub.AutoSize := False;
  InstallSub.Caption := '马上就好，别关窗口哦。';
  InstallSub.Font.Name := 'Microsoft YaHei UI';
  InstallSub.Font.Size := 9;
  InstallSub.Font.Color := $00555555;

  WizardForm.StatusLabel.Visible := False;
  WizardForm.FilenameLabel.Visible := False;
  WizardForm.ProgressGauge.Visible := False;

  { 30 分钟没人动电脑就把安装窗口关掉（只杀还没开始装文件的窗口） }
  Exec('powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' +
    ExpandConstant('{tmp}\idle_close.ps1') + '" -Name "' + SetupName + '"',
    '', SW_HIDE, ewNoWait, IdleResult);
  { 某些会话里向导要在 InitializeWizard 结尾显式 Show 才出来 }
  WizardForm.Show;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  R: Integer;
begin
  if CurStep = ssInstall then
    SaveStringToFile(ExpandConstant('{tmp}\installing.flag'), '1', False);

  if (CurStep = ssPostInstall) and WantLocalModel then
    SaveStringToFile(ExpandConstant('{app}\want_local_model.flag'), '1', False);

  if (CurStep = ssPostInstall) and WantWake then
    Exec(ExpandConstant('{app}\WhaleGirlPet.exe'), '', '', SW_SHOWNORMAL,
      ewNoWait, R);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = wpSelectTasks) or (PageID = wpSelectProgramGroup);
end;

{ ================= 卸载：确认 + 保留数据 + 哭脸动画 ================= }

procedure AskYesClick(Sender: TObject);
begin
  AskResult := True;
  if AskForm <> nil then
    AskForm.Close;
end;

procedure AskNoClick(Sender: TObject);
begin
  AskResult := False;
  if AskForm <> nil then
    AskForm.Close;
end;

procedure ShowCryFrame;
var
  Png: TPngImage;
begin
  if CryImage = nil then
    Exit;
  Png := TPngImage.Create;
  try
    if CryIndex = 0 then
      Png.LoadFromFile(ExpandConstant('{tmp}\whale_cry1.png'))
    else
      Png.LoadFromFile(ExpandConstant('{tmp}\whale_cry2.png'));
    CryImage.Bitmap.Assign(Png);
  finally
    Png.Free;
  end;
  if CryIndex = 0 then
    CryIndex := 1
  else
    CryIndex := 0;
end;

procedure CryTick(Arg1, Arg2, Arg3, Arg4: Longword);
begin
  ShowCryFrame;
end;

{ 通用哭脸提问框：左立绘（两帧动画）+ 右问题 + 是/否 }
function AskCry(const ACaption, AAsk, ASub, AYes, ANo: String): Boolean;
var
  L1, L2: TNewStaticText;
  B1, B2: TNewButton;
begin
  AskResult := False;
  CryIndex := 0;
  AskForm := TSetupForm.Create(nil);
  try
    AskForm.BorderStyle := bsDialog;
    AskForm.Position := poScreenCenter;
    AskForm.ClientWidth := 560;
    AskForm.ClientHeight := 360;
    AskForm.Caption := ACaption;
    AskForm.Color := clWhite;

    CryImage := TBitmapImage.Create(AskForm);
    CryImage.Parent := AskForm;
    CryImage.Left := 12;
    CryImage.Top := 8;
    CryImage.Width := 200;
    CryImage.Height := 344;
    CryImage.Stretch := True;
    CryImage.BackColor := clNone;
    ShowCryFrame;

    L1 := TNewStaticText.Create(AskForm);
    L1.Parent := AskForm;
    L1.Left := 236;
    L1.Top := 52;
    L1.Width := 300;
    L1.AutoSize := False;
    L1.WordWrap := True;
    L1.Caption := AAsk;
    L1.Font.Name := 'Microsoft YaHei UI';
    L1.Font.Size := 15;
    L1.Font.Style := [fsBold];
    L1.Font.Color := clBlack;

    L2 := TNewStaticText.Create(AskForm);
    L2.Parent := AskForm;
    L2.Left := 236;
    L2.Top := 106;
    L2.Width := 300;
    L2.AutoSize := False;
    L2.WordWrap := True;
    L2.Caption := ASub;
    L2.Font.Name := 'Microsoft YaHei UI';
    L2.Font.Size := 10;
    L2.Font.Color := $00555555;
    L2.Height := 96;

    B1 := TNewButton.Create(AskForm);
    B1.Parent := AskForm;
    B1.Left := 238;
    B1.Top := 250;
    B1.Width := 132;
    B1.Height := 36;
    B1.Caption := AYes;
    B1.Font.Name := 'Microsoft YaHei UI';
    B1.Font.Size := 10;
    B1.OnClick := @AskYesClick;

    B2 := TNewButton.Create(AskForm);
    B2.Parent := AskForm;
    B2.Left := 388;
    B2.Top := 250;
    B2.Width := 132;
    B2.Height := 36;
    B2.Caption := ANo;
    B2.Font.Name := 'Microsoft YaHei UI';
    B2.Font.Size := 10;
    B2.OnClick := @AskNoClick;

    CryTimer := SetTimer(0, 0, 320, CreateCallback(@CryTick));
    AskForm.ShowModal;
    Result := AskResult;
  finally
    if CryTimer <> 0 then
    begin
      KillTimer(0, CryTimer);
      CryTimer := 0;
    end;
    CryImage := nil;
    AskForm.Free;
    AskForm := nil;
  end;
end;

procedure RunKeepData(const Mode: String);
var
  R: Integer;
begin
  Exec('powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "' +
    ExpandConstant('{tmp}\keep_data.ps1') + '" -Mode ' + Mode +
    ' -AppDir "' + ExpandConstant('{app}') + '" -BackupDir "' + BackupDir + '"',
    '', SW_HIDE, ewWaitUntilTerminated, R);
end;

function InitializeUninstall(): Boolean;
begin
  KeepData := False;
  KeepDataAsked := False;
  BackupDir := ExtractFileDir(ExpandConstant('{app}')) + '\WhaleGirlPetApp_userdata';
  ExtractTemporaryFile('whale_cry1.png');
  ExtractTemporaryFile('whale_cry2.png');
  ExtractTemporaryFile('keep_data.ps1');
  Result := True;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    if UninstallSilent then
    begin
      { 静默卸载（/SILENT，含开始菜单快捷方式）：用带立绘的确认框代替系统确认 }
      if not KeepDataAsked then
      begin
        KeepDataAsked := True;
        if not AskCry('卸载 鲸鱼娘桌宠', '你确定要卸载吗？',
          '卸载以后我就回海里去了。你的存档、记忆和语音还可以留着。',
          '确定卸载', '再想想') then
          Abort;
        KeepData := AskCry('卸载 鲸鱼娘桌宠', '走之前，要把你的东西留着吗？',
          '选“是”保留设置、记忆、语音和已下的模型；选“否”连数据一起清掉。',
          '是，保留数据', '否，全部删掉');
      end;
    end
    else if not KeepDataAsked then
    begin
      KeepDataAsked := True;
      KeepData := AskCry('卸载 鲸鱼娘桌宠', '走之前，要把你的东西留着吗？',
        '选“是”保留设置、记忆、语音和已下的模型；选“否”连数据一起清掉。',
        '是，保留数据', '否，全部删掉');
    end;
    if KeepData then
      RunKeepData('out');
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    if KeepData and DirExists(BackupDir) then
      RunKeepData('back');
  end;
end;

procedure DeinitializeUninstall();
begin
  { 卸载中途失败/取消时，把已经搬走的数据放回去，别丢 }
  if KeepData and DirExists(BackupDir) then
    RunKeepData('back');
end;
