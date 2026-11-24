# SUN_watching

太陽像を撮影し、太陽中心の軌跡から「西の方角」の角度をリアルタイムに求めて、ずれを PyQt6 のダッシュボードに表示するツールです(`sun_find_west_v2`)。

## 処理の流れ

1. カメラ(ZWO ASI 実機、または動画ファイルを再生するダミーカメラ)からフレームを取得する
2. `MIN2ver2` で各フレームの太陽の中心座標と半径を求める
3. 直近 `buf_lookback` フレームの中心座標と撮影時刻から、RANSAC で西向きの角度を頑健に推定する
4. カメラ映像・軌跡・角度のずれを PyQt6 の画面に描画し、解析結果を CSV に記録する

## 画面の機能

- 軌跡は撮影時刻で色分けされます(古い=紫 → 新しい=黄)。画面下の凡例で確認できます
- マウスホイールでポインタ位置を中心にズーム(最大 12 倍)、左ドラッグで移動、ダブルクリックでリセット
- 左下のオーバービューマップをクリックすると、表示範囲をその位置へ移動できます

## 必要環境

- Python 3.13 以上
- 依存ライブラリは `pyproject.toml` に記載(PyYAML, jsonschema, matplotlib, PyQt6, numpy, opencv-python, scikit-learn)
- 実機の ASI カメラを使う場合のみ `zwoasi` と 64bit の `ASICamera2.dll` が必要です(`pyproject.toml` には含まれていません)

## セットアップ

```bash
python -m pip install -e ".[dev]"
```

`dev` を付けない場合は実行に必要なライブラリだけが入ります。

## 使い方

```bash
python run.py                              # 既定の設定で起動
python run.py --config path/to/config.yaml # 別の設定ファイルを使う
python run.py --edit-config                # 設定エディタ (GUI) を起動
```

設定は `sun_find_west_v2/config/config.yaml` に書きます。`run.py` が起動時に `config_schema.json` で検証し、項目の欠落・未知の項目・範囲外の値があるとエラーで停止します。

### 設定エディタ (GUI)

`--edit-config` を付けると、YAML を直接編集せずに設定を変更できます。

```bash
python run.py --edit-config                                 # 既定の設定を編集
python run.py --edit-config --config path/to/config.yaml    # 別の設定を編集
SUN_watching.exe --edit-config                              # 配布物の場合
```

- `config_schema.json` から入力欄を自動生成するため、`Camera` / `Run` / `sun_find_west_v2` の全項目をタブで編集できます。
- 数値は範囲付きの入力欄、真偽値はチェックボックス、`img_type` は選択肢、`grid_color` は色選択ダイアログになります。
- 「検証」でスキーマ違反を確認でき、「保存」は検証に通った場合だけ書き込みます。保存は一時ファイル経由なので、失敗しても元の設定は壊れません。
- コメントは `config_schema.json` の説明から再生成されます。YAML を直接編集したい場合は従来どおりエディタで開けます。
- 環境変数 `SUN_WATCHING_EDIT_CONFIG=1` でも起動できます。

| 項目 | 内容 |
| --- | --- |
| `Camera` | 露出・ゲイン・転送設定など ASI カメラのパラメータ |
| `Run.camera_source.dummy_camera` | `true` でダミーカメラ(動画再生)、`false` で実機 ASI カメラ |
| `Run.output.report_dir` | レポート(CSV・キャプチャ画像)の出力先。空なら `data/report`、相対パスは出力先ルート基準、絶対パスはそのまま |
| `sun_find_west_v2.Analyzer` | 許容角度 `acceptable`、軌道推定に使うフレーム数 `buf_lookback` |
| `sun_find_west_v2.MIN2ver2` | 太陽検出のパラメータ(格子分割数・しきい値・縁の幅・黒点除外の回数) |
| `sun_find_west_v2.Visualizer` | 画面のグリッド色・分割数・透明度など |

## ディレクトリ構成

```
run.py                  実行用エントリポイント(設定の読み込みと検証)
generate_dependencies.py  import と pyproject.toml の依存関係を同期・検査する
sun_find_west_v2/
  main.py               メインループ(撮影 → 解析 → 描画 → CSV 記録)
  qt_visualizer.py      PyQt6 ダッシュボード
  camera/               ASI カメラ制御とダミーカメラ
  config/               config.yaml、スキーマ、ローダー、設定エディタ
  core/                 MIN2ver2(太陽検出)、RANSAC(角度推定)
tests/                  pytest
materials/              調整マニュアルなどの資料
report/                 観測ログ
log/                    実行ログ(ソース実行時。配布物は exe と同じフォルダ)
```

## 開発

```bash
python generate_dependencies.py --check   # 依存関係と import の整合性チェック
ruff check .                              # Lint
basedpyright                              # 型チェック
QT_QPA_PLATFORM=offscreen python -m pytest   # テスト(ヘッドレス環境)
```

CI(`.github/workflows/ci.yml`)では依存関係チェック、Ruff、basedpyright が実行されます。

## Windows 11向け配布物の作成

Windows 11 x64向けの配布物は、GitHub Actionsの `Build Windows distribution` を手動実行すると作成できます。Actionsの実行結果から、次のファイルをダウンロードできます。

ファイル名には `pyproject.toml` のバージョンが入ります（例: `1.10.2`）。

- `SUN_watching-<バージョン>-windows-x64.zip` ... 展開して `SUN_watching.exe` を実行するポータブル版
- `SUN_watching-<バージョン>-setup-windows-x64.exe` ... Inno Setupによるインストーラー
- `SUN_watching-<バージョン>-SHA256SUMS.txt` ... 上記2ファイルのSHA-256ハッシュ

インストーラーはユーザー単位（既定: `%LOCALAPPDATA%\Programs\SUN_watching`）に導入され、管理者権限や PATH の変更を必要としません。設定ファイル・スキーマ・DLL は実行ファイルから相対的に参照されます。ログは実行ファイルと同じフォルダの `log`、解析結果は既定で `%LOCALAPPDATA%\SUN_watching\data` に保存され、起動時に自動作成されます。解析結果の場所を別にしたい場合は環境変数 `SUN_WATCHING_HOME` を設定してください（ログは exe 側の `log` のままです）。ASI SDK の `ASICamera2.dll` はビルド時にソースとの SHA-256 一致と 64bit (AMD64) であることを検証したうえで `_internal\camera\bin` に同梱され、インストール後の配置も検証されます。万一同梱 DLL が無い場合は、ZWO ドライバが導入したシステム側の `ASICamera2.dll`（`%SystemRoot%\System32`）を使用します。

配布物の動作確認には `SUN_watching.exe --check-config` を使えます。これは設定ファイルと `config_schema.json` の検証だけを行い、画面を開かずに終了します。

インストーラーには「ZWO ASI カメラドライバを公式サイトからダウンロードしてインストール」という任意タスクがあり、既定でチェックされています。このタスクを選択すると、インストール時に ZWO 公式サイトから Camera Driver を取得し、Authenticode 署名を検証したうえで管理者権限で導入します（UAC の確認とネットワーク接続が必要です）。ドライバ本体は再配布せず、公式配布物をそのまま取得します。不要な場合はタスクのチェックを外してください。ポータブル版（ZIP）には `tools\install-asi-driver.ps1` が含まれるので、必要な場合は管理者権限の PowerShell から次を実行します。

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\install-asi-driver.ps1
```

リポジトリに `v1.10.2` のようなタグをpushした場合は、同じファイルがGitHub Releaseにも自動添付されます。ビルドはPython 3.13 x64、Windows Server 2022 runnerで行うため、Windows 11 x64での利用を対象にしています。ASIカメラを使用する場合は上記タスクまたはスクリプトでネイティブドライバを導入してください（`zwoasi` は実行ファイルに同梱済みです）。初回確認は `config.yaml` の `dummy_camera: true` による動画入力を推奨します。

## ライセンス

`LICENSE` を参照してください。
