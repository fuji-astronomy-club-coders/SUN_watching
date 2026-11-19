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
```

設定は `sun_find_west_v2/config/config.yaml` に書きます。`run.py` が起動時に `config_schema.json` で検証し、項目の欠落・未知の項目・範囲外の値があるとエラーで停止します。

| 項目 | 内容 |
| --- | --- |
| `Camera` | 露出・ゲイン・転送設定など ASI カメラのパラメータ |
| `Run.camera_source.dummy_camera` | `true` でダミーカメラ(動画再生)、`false` で実機 ASI カメラ |
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
  config/               config.yaml、スキーマ、ローダー
  core/                 MIN2ver2(太陽検出)、RANSAC(角度推定)
tests/                  pytest
materials/              調整マニュアルなどの資料
report/                 観測ログ
```

## 開発

```bash
python generate_dependencies.py --check   # 依存関係と import の整合性チェック
ruff check .                              # Lint
basedpyright                              # 型チェック
QT_QPA_PLATFORM=offscreen python -m pytest   # テスト(ヘッドレス環境)
```

CI(`.github/workflows/ci.yml`)では依存関係チェック、Ruff、basedpyright が実行されます。

## ライセンス

`LICENSE` を参照してください。
