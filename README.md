# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）。  
データ収集（J-Quants）、前処理（DuckDB）、リサーチ（ファクター計算）、特徴量作成、シグナル生成、ニュース収集、カレンダー管理、ETL パイプラインなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下のレイヤーを備えた設計になっています。

- Data Layer（DuckDB）: 生データ（raw） → 加工済み → 特徴量 → 発注・監査。
- Data ingestion: J-Quants API クライアント（レート制限・リトライ・トークン自動刷新対応）。
- News collection: RSS フィード収集、前処理、銘柄抽出。
- Research: ファクター計算（モメンタム / ボラティリティ / バリュー）や将来リターン・IC 計算。
- Strategy: 特徴量正規化（Z スコア）とシグナル生成（BUY / SELL 判定）。
- ETL pipeline: 差分取得、保存、品質チェックを含む日次 ETL。
- Schema / Audit: DuckDB のスキーマ定義、監査ログ用テーブル。

設計方針としては「ルックアヘッドバイアスの排除」「冪等性（ON CONFLICT など）」「外部依存の最小化（標準ライブラリ中心）」が重視されています。

---

## 主な機能一覧

- J-Quants からのデータ取得（株価 / 財務 / 市場カレンダー）
  - レート制限遵守、リトライ、トークン自動更新
- DuckDB スキーマ定義・初期化（init_schema）
- 差分 ETL / 日次 ETL（run_daily_etl）
- ファクター計算
  - モメンタム（1M/3M/6M、MA200乖離）
  - ボラティリティ（ATR20、出来高比、平均売買代金）
  - バリュー（PER、ROE）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（重み付け合成・Bear 抑制・エグジット条件）
- RSS ベースのニュース収集と銘柄抽出
- マーケットカレンダー管理（営業日判定 / next/prev）
- 監査ログ（signal_events / order_requests / executions など）
- 小規模な統計ユーティリティ（zscore_normalize 等）

---

## 必要環境 / 前提

- Python 3.9 以上（typing の記述に合わせる）
- DuckDB（Python パッケージ: duckdb）
- defusedxml（RSS パース安全化）
- ネットワークアクセス（J-Quants API、RSS）

実際のプロジェクトでは追加でログライブラリや Slack 通知用パッケージ、kabu API との接続ライブラリなどが必要になる場合があります。

---

## 環境変数（必須 / 任意）

Settings クラスで参照される主要環境変数：

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- SLACK_BOT_TOKEN — Slack Bot トークン（通知用途）
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` および `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトの requirements.txt がある場合はそれを利用してください）
   - 開発インストール: pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、シェルでエクスポートしてください。

5. DuckDB スキーマ初期化
   - Python REPL / スクリプト例:
     ```
     from kabusys.config import settings
     from kabusys.data.schema import init_schema

     conn = init_schema(settings.duckdb_path)
     ```
   - またはメモリ DB でテスト:
     ```
     conn = init_schema(":memory:")
     ```

---

## 使い方（主要な API と例）

以下は典型的な利用フロー例です。詳細はコード内ドキュメントをご参照ください。

- 日次 ETL を実行（市場カレンダー・株価・財務の差分取得・保存・品質チェック）
  ```
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を渡すことも可能
  print(result.to_dict())
  ```

- 特徴量ビルド（features テーブルへ書き込む）
  ```
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成（signals テーブルへ書き込む）
  ```
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, date.today())
  print(f"signals written: {total}")
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(results)
  ```

- カレンダーの夜間更新（calendar_update_job）
  ```
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からの直接データ取得（テストやバックフィル）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  token = get_id_token()  # refresh token は settings から取られる
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,3,31))
  saved = save_daily_quotes(conn, rows)
  ```

注意:
- ほとんどの関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取ります。
- 多くの処理は日付単位で冪等（既存 date のレコードを削除して再挿入）を保証する実装です。

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 配下）:

- __init__.py
- config.py — 環境変数 / 設定読み込みロジック
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py — RSS 収集・前処理・DB 保存
  - schema.py — DuckDB スキーマ定義・初期化
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - features.py — data.stats の再エクスポート
  - calendar_management.py — マーケットカレンダー管理と更新ジョブ
  - audit.py — 監査ログ DDL と初期化
  - (その他：quality モジュール想定)
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー
- strategy/
  - __init__.py
  - feature_engineering.py — ファクター正規化・ユニバースフィルタ → features テーブル
  - signal_generator.py — final_score 計算、BUY/SELL 生成 → signals テーブル
- execution/ — 発注・約定・ポジション管理レイヤ（パッケージ化済み）
- monitoring/ — 監視用コード（存在が __all__ に示されているが個別ファイル未示）

（各モジュール内に詳細な docstring と設計メモが記載されています。実装に則った呼び出し方や戻り値の仕様はソース内ドキュメントを参照してください）

---

## 開発 / テストに関する注意点

- DuckDB の SQL は日付型やウィンドウ関数を多用します。大きなデータセットでの実行はメモリと I/O に注意してください。
- J-Quants API へのアクセスはレート制限があります（120 req/min）。jquants_client は固定間隔のスロットリングで制御します。
- RSS パースは defusedxml を利用し安全に行いますが、公開フィードの多様性に伴うパース例外に注意してください（fetch_rss は失敗時に空リストでフォールバックします）。
- 本ライブラリは「発注を直接行う」層（ブローカー送信）を内包しません。execution 層との連携は別途実装・統合してください。
- production で稼働させる際は、KABUSYS_ENV を適切に設定し（paper_trading / live）、ログレベルと通知（Slack）を整備してください。

---

## 参考 / 連絡先

- ソースの各モジュールに設計ノート（例: StrategyModel.md, DataPlatform.md など）への参照があります。実運用時はそれらのドキュメントも合わせて参照してください。
- バグ報告・機能提案はリポジトリの Issue にお願いします。

---

この README はコードの現状（src/kabusys 以下）をもとに作成しています。実際の運用向けには追加の環境設定、監視、テスト、セキュリティレビューを推奨します。