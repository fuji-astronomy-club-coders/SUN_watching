# SUN_watching 仕様書(sun_find_west_v2)

本書は `sun_find_west_v2` の機能・処理・入出力の仕様をまとめたものです。環境構築の手順は [setup-guide.md](setup-guide.md) を参照してください。

## 1. 目的

太陽像を連続撮影し、画像上の太陽中心の移動軌跡から「西の方角」の向きを推定して、望遠鏡・カメラの向きのずれをリアルタイムに表示する。ずれが許容角度以内かどうかを画面上で判定できる。

## 2. システム構成

```
run.py ── 設定の読み込み・検証 ──▶ main.main(config)
                                      │
        ┌─────────────────────────────┼───────────────────────────┐
        ▼                             ▼                           ▼
   camera/                       core/                    qt_visualizer.py
   controller.py (実機 ASI)      MIN2ver2.py (太陽検出)    Visualizer (PyQt6)
   vid_dummy.py (動画再生)       RANSAC.py  (角度推定)
```

| モジュール | 役割 |
| --- | --- |
| `run.py` | 引数解析、`config.yaml` の読み込みとスキーマ検証、`main()` の起動。設定の読み込みはここだけが行う |
| `sun_find_west_v2/main.py` | `SunTrackerApp`。撮影・解析・描画・CSV記録・手動キャプチャのメインループ |
| `sun_find_west_v2/config/loader.py` | YAML 読み込みと JSON Schema(Draft 7)検証。違反は `ConfigError` |
| `sun_find_west_v2/config/editor.py` | tkinter 製の設定エディタ GUI。`--edit-config` で起動 |
| `sun_find_west_v2/config/editor_model.py` | 設定エディタ用のスキーマ解析、YAML 入出力、検証 |
| `sun_find_west_v2/camera/controller.py` | カメラ接続(`connect_camera`)、パラメータ一括設定(`apply_camera_config`)、実行中の値変更(`handle_config`) |
| `sun_find_west_v2/camera/vid_dummy.py` | `VideoDummyCamera`。動画ファイルを `zwoasi.Camera` 互換のカメラとして扱う |
| `sun_find_west_v2/core/MIN2ver2.py` | 最小二乗法による太陽の円近似。黒点を除外して中心・半径を返す |
| `sun_find_west_v2/core/RANSAC.py` | RANSAC による移動方向(角度・速度ベクトル)の推定 |
| `sun_find_west_v2/qt_visualizer.py` | PyQt6 のダッシュボード |

## 3. 処理フロー

起動から終了までの流れ。

1. `python run.py [--config PATH]` で起動する。設定は `config.yaml`(または `--config` の指定先)を `config_schema.json` で検証する。違反があれば起動せずエラーで終了する(補完・既定値の代入は行わない)。`--edit-config` を付けた場合は解析を開始せず、設定エディタ GUI を起動する。
2. ログ出力先と保存先を作成する(§6)。
3. `Run.camera_source.dummy_camera` に従ってカメラを接続する。
   - `true`: ダミーカメラ。動画ファイルをファイルダイアログで選ぶ。選ばなければ起動を中止する。
   - `false`: 実機 ASI カメラ。`zwoasi` と `sun_find_west_v2/camera/bin/ASICamera2.dll` が必要。
4. `Camera` セクションの値をカメラへ適用し、動画キャプチャを開始して ROI(幅・高さ・画像形式)を取得する。
5. `Visualizer` を ROI の大きさで生成し、メインループに入る。メインループは1フレームごとに次を行う。

| 手順 | 内容 |
| --- | --- |
| 1 | フレームを取得する(タイムアウトの既定は 500ms)。失敗したら警告を出し、`dropped_frames` を加算して次のフレームへ |
| 2 | バイト列を画像配列に変換する(RAW8/Y8=uint8、RAW16=uint16、RGB24=uint8×3) |
| 3 | `MIN2_ignore_sunspots` で太陽の中心 `(cx, cy)` と半径 `r` を求める。例外時は警告を出して次のフレームへ |
| 4 | 中心座標と撮影時刻(UNIX 秒)をバッファ(最大 500 件)に追加し、直近 `buf_lookback` 件を取り出す |
| 5 | 直近の点が 3 点以上あれば `calculate_west_angle_robust` で角度 `robust_angle` と速度ベクトルを求める。失敗時は警告を出して `None` |
| 6 | ゲイン・露出・温度を読み出す。失敗時は `None` |
| 7 | 1行を CSV に追記して flush する |
| 8 | `Visualizer.update` で画面を更新する(例外は警告ログのみで継続) |
| 9 | Capture ボタンが押されていれば現フレームを PNG 保存する |
| 10 | ウィンドウが閉じられていれば終了する |

終了は Quit ボタン、ウィンドウを閉じる、Ctrl+C のいずれか。終了時にカメラ停止・解放と描画リソースの解放を行う。

## 4. 解析仕様

### 4.1 太陽の検出(MIN2ver2)

設定ファイルの `MIN2ver2` セクション(`n`、`light_threshod`、`limb_wigth`、`iter_cycles`)が、そのまま検出処理に渡される。

- 画像を `n` 本の格子線で走査して太陽の縁の点を集め、最小二乗法で円を当てはめる。
- 一度近似した円の外側の点だけから再度円を近似し、その縁から `limb_wigth × 2/3` より内側に離れた点を黒点とみなして除外する。これを最大 `iter_cycles` 回繰り返す(黒点が無くなれば早期終了、0 なら除外なし)。
- 16bit 画像では `light_threshod` を自動で 256 倍して扱う。
- 戻り値は `((cx, cy), r)`(画素単位)。

### 4.2 角度の推定(RANSAC)

- 入力は直近 `buf_lookback` 点の `(x, y)` と各点の撮影時刻。時刻の個数が点数と一致しないときは 0, 1, 2… の等間隔として扱う。
- x と y のそれぞれを時刻に対する直線として RANSAC(`sklearn.linear_model.RANSACRegressor`、`random_state=42`)で当てはめ、傾き `vx`, `vy` を得る。外れ値(雲・誤検出など)に強い。
- `robust_angle = -atan2(vy, vx)` を度で返す。画像座標は y が下向きのため符号を反転している。戻り値は `(robust_angle, (vy, vx))`。
- 2 点未満では `ValueError` を送出する。メインループは 3 点以上のときだけ呼ぶ。

### 4.3 ずれの判定

表示用の角度 `west_angle = ((180 − robust_angle) + 180) mod 360 − 180`(範囲 −180〜180)。

- 画像上で太陽が水平に左へ動く(`robust_angle = ±180°`)とき `west_angle = 0°`。
- `|west_angle| < acceptable` なら **ALIGNED**、それ以外は **ADJUST**、角度が求まらない間は **INSUFFICIENT DATA** と表示する。

## 5. 画面仕様(Visualizer)

PyQt6 のウィンドウ。左にカメラ映像、右に操作・数値パネルがある。

### 5.1 カメラ映像

- フレーム上に次を重ねて描画する。
  - 格子線(`grid_nx` × `grid_ny`)と中心円(半径 `grid_r`)
  - 検出した太陽の円
  - 西向きの方向ベクトル(許容内=緑、許容外=紫)
  - 軌跡。**撮影時刻で色分け**(古い=紫 → 新しい=黄の Viridis 風)。始点は小円、終点は大円で示す。時刻が使えないときは点の順序で代用する
- 映像の下に「EARLIER → NOW」の色凡例を表示する。

### 5.2 ズームと移動

| 操作 | 動作 |
| --- | --- |
| マウスホイール | ポインタ位置を基準にズーム(1.0〜12.0 倍、1回あたり 1.2 倍) |
| 左ドラッグ | ズーム中に表示範囲を移動 |
| ダブルクリック | ズームと表示位置をリセット |
| オーバービューマップをクリック | その位置を表示範囲の中心にする |

- 映像の左下にオーバービューマップ(全体像と現在の表示範囲の枠)を重ねて表示する。
- ズーム中はヘッダーに `ZOOM n.n×` を表示する。

### 5.3 パネル・操作

| 項目 | 内容 |
| --- | --- |
| 角度表示 | `west_angle`(符号付き、小数 2 桁)、許容角度と判定 |
| 状態表示 | ALIGNED / ADJUST / INSUFFICIENT DATA |
| 数値 | 太陽中心、半径、フレーム数、解析点数、FPS |
| Reset | 軌跡バッファとフレーム数を初期化 |
| Capture | 現在のフレームを PNG で保存 |
| Quit | メインループを終了 |
| Gain スライダー | 0〜400。初期値は設定ファイルの `gain`。実行中にカメラへ反映 |
| Exposure スライダー | 32〜20000 µs。初期値は設定ファイルの `exposure`。実行中にカメラへ反映 |

## 6. 入出力仕様

### 6.1 入力

- 設定ファイル `sun_find_west_v2/config/config.yaml`(§7)
- カメラ映像(実機 ASI カメラ、またはダミー動画)
- ダミー動画の対応形式: `.mp4 .avi .mov .mkv .wmv .ser`。`.ser` は専用リーダー、それ以外は OpenCV で読む。カラー動画はグレースケールに変換する。終端まで再生すると先頭に戻ってループする。

### 6.2 出力

ログはソース実行時はリポジトリ直下、Windows 配布物では `SUN_watching.exe` と同じフォルダの `log/` に保存する。データとレポートの出力先ルートはソース実行時はリポジトリ直下、Windows 配布物では `%LOCALAPPDATA%\SUN_watching`(環境変数 `SUN_WATCHING_HOME` で上書き可能)である。レポートの親ディレクトリは既定で `data/report/` で、`Run.output.report_dir` で変更できる。起動時に `<app_root>/log/`、`data/`、既定の `data/report/` が作成される。`YYYYMMDD` は起動日。

| 出力 | パス | 内容 |
| --- | --- | --- |
| ログ | `<app_root>/log/sunfindwestV2_YYYYMMDD_HHMMSS.log` | DEBUG レベル以上。コンソールにも出力 |
| 解析 CSV | `<report_dir>/YYYYMMDD/sun_data_YYYYMMDD_HHMMSS_BYsunfindwestV2.csv` | 1フレーム1行(下表) |
| キャプチャ画像 | `<report_dir>/YYYYMMDD/captures/raw_YYYYMMDD_HHMMSS_mmm_f<フレーム番号>.png` | Capture ボタンで保存したフレーム(オーバーレイ無しの生画像) |

`<app_root>` はソース実行時はリポジトリルート、配布物では exe のあるフォルダ。`SUN_WATCHING_HOME` はログには影響しない。
`<report_dir>` は既定で出力先ルート基準の `data/report`。`Run.output.report_dir` に相対パスを書くと出力先ルート基準、絶対パスを書くとその場所になる。

CSV の列:

| 列 | 内容 |
| --- | --- |
| `timestamp_iso` | 撮影時刻(ISO 8601) |
| `timestamp_unix` | 撮影時刻(UNIX 秒) |
| `frame_count` | フレーム番号(Reset で 0 に戻る) |
| `temperature_c` | センサー温度(℃)。取得できなければ空 |
| `gain` | ゲイン |
| `exposure_us` | 露出時間(µs) |
| `cx`, `cy`, `r` | 太陽の中心座標と半径(画素) |
| `robust_angle` | RANSAC の角度(度)。未算出なら空 |

## 7. 設定仕様(config.yaml)

不足・未知の項目・範囲外の値はすべて起動時エラーになる。

### Camera

| 項目 | 型 / 範囲 | 内容 |
| --- | --- | --- |
| `basic_parameters.exposure` | 整数 32〜20000 | 露出時間(µs) |
| `basic_parameters.gain` | 整数 0〜400 | ゲイン |
| `basic_parameters.offset` | 整数 0〜100 | オフセット(黒レベル) |
| `basic_parameters.gamma` | 整数 1〜100 | ガンマ(50=補正なし) |
| `transfer_settings.band_width` | 整数 40〜100 | USB 帯域の制限(%) |
| `transfer_settings.high_speed_mode` | 真偽 | ハイスピードモード |
| `transfer_settings.hardware_bin` | 整数 1〜4 | ハードウェアビニング |
| `transfer_settings.flip` | 整数 0〜3 | 反転(0:なし 1:水平 2:垂直 3:両方) |
| `auto_control.auto_max_gain` | 整数 0〜400 | 自動ゲイン上限 |
| `auto_control.auto_max_exp` | 整数 1〜10000 | 自動露出上限(ms) |
| `auto_control.auto_target_brightness` | 整数 0〜255 | 自動露出の目標明るさ |
| `image_format.img_type` | `RAW8` / `RAW16` / `Y8` | 画像形式 |

### Run

| 項目 | 型 | 内容 |
| --- | --- | --- |
| `camera_source.dummy_camera` | 真偽 | `true`=ダミー動画、`false`=実機 ASI カメラ |
| `output.report_dir` | 文字列 | レポートの出力先。空なら `data/report`。相対パスは出力先ルート基準、絶対パスはそのまま |

### sun_find_west_v2

| 項目 | 型 / 範囲 | 内容 |
| --- | --- | --- |
| `Analyzer.acceptable` | 数値 0〜180 | 許容角度(度) |
| `Analyzer.buf_lookback` | 整数 2 以上 | 軌道推定に使うフレーム数。バッファは最大 500 件なので、それ以上にしても効果は 500 件までになる |
| `MIN2ver2.n` | 整数 2〜200 | 画像格子の分割数 |
| `MIN2ver2.light_threshod` | 整数 0 以上 | 太陽の明るさのしきい値 |
| `MIN2ver2.limb_wigth` | 整数 0 以上 | 太陽の縁の幅の基準値(画素) |
| `MIN2ver2.iter_cycles` | 整数 0 以上 | 黒点除外の最大反復回数(0=除外なし) |
| `Visualizer.grid_color` | `#RRGGBB` または `#RGB` | 格子色。YAML では `#` がコメントになるため引用符で囲む |
| `Visualizer.grid_ny` / `grid_nx` | 整数 0 以上 | 格子の縦・横の分割数 |
| `Visualizer.grid_r` | 数値 0 以上 | 中心円の半径(画素)。0 で非表示 |
| `Visualizer.grid_alpha` | 数値 0〜1 | 格子の透明度 |

`light_threshod`・`limb_wigth` は、スキーマ上のキー名がこの綴りのため、そのまま記述する。

### 7.1 設定エディタ

`python run.py --edit-config [--config PATH]` または環境変数 `SUN_WATCHING_EDIT_CONFIG=1` で起動する。tkinter 製で、PyQt6 は不要。

- `config_schema.json` の `properties` を走査し、`Camera` / `Run` / `sun_find_west_v2` をタブ、その下の object をグループとして入力欄を自動生成する。integer は範囲付き数値入力、number は小数入力、boolean はチェックボックス、enum は選択肢、`pattern` が色形式なら色選択ボタンになる。
- 「検証」は現在の入力から設定 dict を組み立て、Draft 7 で検証して違反を一覧表示する。
- 「保存」は検証に成功した場合だけ、一時ファイルへ書いてから `replace` する。コメントはスキーマの `description` から再生成する。
- 入力ファイルが不正な YAML、または存在しない場合は、空の設定として編集を続けられる。保存時には必ず検証する。
- スキーマに無いキーは読み込み時に警告し、保存時に取り除かれる。

| 項目 | 内容 |
| --- | --- |
| Python | 3.13 以上 |
| OS | ダミーカメラ(動画再生): PyQt6 が動く OS。実機カメラ: 同梱の `ASICamera2.dll` が Windows 用のため Windows 64bit |
| 実機カメラ | ZWO ASI(設定コメントは ASI432MM を想定)。`zwoasi` と `ASICamera2.dll` が必要 |

## 9. エラー処理と既知の制約

| 状況 | 挙動 |
| --- | --- |
| 設定が不正 | 起動せずにエラー終了 |
| ダミー動画を選択しなかった / 開けない | エラーログを出して終了 |
| 実機モードで `zwoasi` 未導入 | エラーログを出して終了 |
| `ASICamera2.dll` が無い | エラーを記録し、Enter 待ちの後にカメラ未接続として終了 |
| フレーム取得失敗 / 太陽検出失敗 | 警告を記録してそのフレームを飛ばす(`dropped_frames` に加算) |
| 角度計算失敗 | 警告を記録し、その回は角度なしで続行 |
| 描画更新失敗 | 警告を記録して続行 |

既知の制約:

- `main.py` は単体では起動できない。必ず `run.py` から起動する。
