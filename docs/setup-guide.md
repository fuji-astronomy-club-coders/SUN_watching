# セットアップガイド

SUN_watching(`sun_find_west_v2`)を動かすまでの手順です。まず「ダミーカメラ(動画再生)」で動作を確認し、そのあと必要なら実機の ASI カメラに切り替えます。仕様の詳細は [specification.md](specification.md) を参照してください。

## 1. 用意するもの

| 項目 | ダミーカメラ | 実機カメラ |
| --- | --- | --- |
| Python 3.13 以上 | 必要 | 必要 |
| Git | 必要 | 必要 |
| 太陽の動画ファイル(`.mp4 .avi .mov .mkv .wmv .ser`) | 必要 | 不要 |
| ZWO ASI カメラ本体と USB 3.0 ケーブル | 不要 | 必要 |
| Windows 64bit・Python 64bit | 不要 | 必要(同梱の DLL が Windows 用) |
| ZWO ASI Camera Driver(Windows ネイティブドライバ) | 不要 | 必要 |
| `zwoasi`(Python ライブラリ) | 不要 | 必要 |
| `ASICamera2.dll` | 不要 | 必要(リポジトリに同梱) |

## 2. 取得とインストール

```bash
git clone https://github.com/fuji-astronomy-club-coders/SUN_watching.git
cd SUN_watching

python -m venv .venv
# Windows (PowerShell):  .venv\Scripts\Activate.ps1
# macOS / Linux:         source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -e .
```

開発もする場合(テスト・Lint・型チェックを使う場合)は `-e ".[dev]"` にします。

```bash
python -m pip install -e ".[dev]"
```

依存ライブラリは `pyproject.toml` に固定バージョンで書かれています。インストールに時間がかかるのは OpenCV や scikit-learn によるものです。

## 3. ダミーカメラで動かす(最初の確認)

1. `sun_find_west_v2/config/config.yaml` の次の行が `true` になっていることを確認する(初期値は `true`)。

   ```yaml
   Run:
     camera_source:
       dummy_camera: true
   ```

2. 起動する。

   ```bash
   python run.py
   ```

3. ファイル選択ダイアログが開くので、太陽を撮影した動画を選ぶ。キャンセルすると起動を中止する。
4. ダッシュボードが開き、太陽の検出円・軌跡・角度が表示されれば成功。動画は終端まで再生すると先頭に戻って繰り返す。
5. 終了は Quit ボタン、またはウィンドウを閉じる。

画面操作(ズーム・オーバービュー・Capture など)は [specification.md の 5 章](specification.md#5-画面仕様visualizer) を参照してください。

## 4. 実機の ASI カメラで動かす

実機接続は **Windows 64bit + Python 64bit** を対象としています。Windows用のネイティブドライバ、Pythonライブラリ `zwoasi`、SDK DLL はそれぞれ別のものです。次の順番で準備してください。

### 4.1 ZWO ASI Camera Driver のインストール

1. [ZWO公式 Camera Driver ダウンロードページ](https://www.zwoastro.com/software/camera-driver/) を開く。
2. Windows 用の **Camera Driver** をダウンロードする。公開されている最新版を使用する。
   - WindowsでASIカメラを使用するには、このネイティブドライバが必要です。
   - **ASCOM Driver** や **DirectShow Driver** ではなく、**Camera Driver** を選択してください。このプロジェクトは `zwoasi` からASIカメラを直接操作するため、ASCOM Platform と ASCOM Driver は必要ありません。
3. ダウンロードしたインストーラーを実行し、画面の案内に従ってインストールする。管理者権限の確認が表示された場合は許可する。
4. インストーラーから再起動を求められた場合は、Windowsを再起動する。

インストール後、必要に応じて [ZWO公式 Software Center](https://www.zwoastro.com/software/) から **ASIStudio** もインストールしてください。ASIStudioでカメラが認識されるか確認できます(本プロジェクトの実行自体には必須ではありません)。

### 4.2 Python ライブラリ `zwoasi` のインストール

本プロジェクトの仮想環境を有効にした状態で、次を実行する。

```powershell
python -m pip install zwoasi
```

`zwoasi` はPythonからASIカメラを操作するためのライブラリです。上記のWindows用ネイティブドライバの代わりにはならないため、**両方をインストールしてください**。

Pythonが64bit版であることも確認する。

```powershell
python -c "import struct; print(struct.calcsize('P') * 8)"
```

出力が `64` であることを確認する。32bit版Pythonでは、同梱の64bit DLLを利用できません。

### 4.3 SDK DLL の確認

1. `sun_find_west_v2/camera/bin/ASICamera2.dll` が存在することを確認する。このDLLはリポジトリに同梱されています。
2. 通常は追加ダウンロードやコピーは不要です。DLLを差し替える場合は、Windows 64bit用の `ASICamera2.dll` を同じ場所に配置してください。

> **補足:** ZWO公式サイトの Product SDK は開発者向けです。本プロジェクトではDLLをリポジトリに同梱しているため、通常の利用者が別途 SDK をダウンロードする必要はありません。

### 4.4 カメラ接続と起動

1. ドライバのインストール後、ASIカメラをPCの **USB 3.0 ポート**に接続する。カメラの電源が必要な機種では、機種の取扱説明書に従って電源も接続する。
2. 必要に応じてASIStudioを起動し、カメラが認識されることを確認する。
3. `sun_find_west_v2/config/config.yaml` の設定を変更する。

   ```yaml
   Run:
     camera_source:
       dummy_camera: false
   ```

4. 太陽観測用にカメラの値を確認・調整する。ND フィルタ(ND5.0 など)を使用する場合、設定ファイルのコメントに記載された露出 100〜1000 µs、ゲイン 0 を初期目安とし、使用するカメラやフィルタに合わせて調整する。

5. 起動する。

   ```bash
   python run.py
   ```

カメラが見つからない場合、プログラムは接続を待ち続けます。トラブルシューティングの項目を確認してください。

> **太陽観測時の安全上の注意:** 太陽を観測するときは、必ず太陽観測に適合した減光フィルタを光学系の前面に取り付けてください。フィルタ無しで太陽を見たり、カメラに導いたりしないでください。目やセンサーを損傷します。

## 5. 設定ファイルを分けて使う

`--config` で別の設定ファイルを指定できます。観測場所ごとの設定を分けたいときに使います。

```bash
python run.py --config path/to/my_config.yaml
```

設定は起動時に検証されます。項目の欠落、未知の項目、範囲外の値があると、エラーメッセージを出して起動しません。値の範囲は [specification.md の 7 章](specification.md#7-設定仕様configyaml) にあります。

注意点:

- `grid_color` は `"#FFFFFF"` のように引用符で囲む(`#` が YAML のコメントになるため)。
- `light_threshod`、`limb_wigth` は綴りのまま書く。

## 6. 出力の場所

起動日ごとに `report/YYYYMMDD/` ができ、次が保存されます。

- `logs/` ... 実行ログ
- `sun_data_..._BYsunfindwestV2.csv` ... 解析結果(1フレーム1行)
- `captures/` ... Capture ボタンで保存した画像

## 7. 動作確認用コマンド(開発者向け)

`.[dev]` を入れた場合に使えます。

```bash
python generate_dependencies.py --check   # import と pyproject.toml の依存関係の整合
ruff check .                              # Lint
basedpyright                              # 型チェック
QT_QPA_PLATFORM=offscreen python -m pytest   # テスト(Windows の PowerShell では $env:QT_QPA_PLATFORM="offscreen" を先に設定)
```

現状、`tests/test_config_loader.py::test_shipped_config_is_valid` は初期設定が `dummy_camera: true` のため失敗します(設定の値とテストの期待値が食い違っています)。CI ではテストを実行していません。

## 8. トラブルシューティング

| 症状 | 原因と対処 |
| --- | --- |
| 起動直後に設定エラーが出る | メッセージに書かれた項目を `config.yaml` で修正する。欠落・綴り違い・範囲外が原因 |
| `動画ファイルが選択されませんでした` | ダミーモードでダイアログをキャンセルした。再度起動して動画を選ぶ |
| `動画ファイルを開けませんでした` | 動画の形式・コーデックが OpenCV で読めない。 `.mp4` などに変換するか `.ser` を使う |
| `zwoasi がインストールされていません` | 実機モードで `zwoasi` が未導入。仮想環境を有効にして `python -m pip install zwoasi` を実行するか、`dummy_camera: true` に戻す |
| ASIStudioでもカメラが認識されない | Windows用のZWO ASI Camera Driverが未導入、USB接続、ケーブル、電源などに問題がないか確認する |
| `Waiting for camera connection...` のまま進まない | カメラが検出されていない。ネイティブドライバの導入、USB 3.0接続、カメラの電源、ASIStudioでの認識を確認する |
| `DLL not found` と出て Enter 待ちになる | `sun_find_west_v2/camera/bin/ASICamera2.dll` が無い。リポジトリに同梱されたDLLが存在するか確認し、差し替えた場合は64bit版を置く |
| SDK初期化時にエラーが出る | PythonとDLLのbit数が一致していない可能性がある。Pythonが64bit版であることと、DLLが64bit版であることを確認する |
| 太陽の検出に失敗し続ける(Dropped が増える) | 露出・ゲインを調整して太陽の縁がはっきり写るようにする(`MIN2ver2` の設定値は現状は検出に反映されないため、ここでは調整できない) |
| 角度が `N/A`(INSUFFICIENT DATA) のまま | 解析点が 3 点未満、または角度計算に失敗している。しばらく撮影を続けるか、ログの警告を確認する |
| ずれの表示が安定しない | `buf_lookback` を増やして平均する時間を長くする。軌跡が短すぎると推定がぶれる |
| 画面が固まる / PyQt6 が起動しない | ヘッドレス環境(ディスプレイ無し)では起動できない。デスクトップ環境で実行する |
