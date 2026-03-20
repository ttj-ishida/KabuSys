# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームと自動売買（シグナル生成）ライブラリです。J-Quants からの市場データ取得、DuckDB によるデータ永続化、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、実行（発注）レイヤーのためのスキーマ/ユーティリティを提供します。

---

## 主要な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、JPX カレンダーのページネーション対応取得
  - レート制限・リトライ・トークン自動リフレッシュ実装
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）

- データレイヤ（DuckDB）
  - Raw / Processed / Feature / Execution の多層スキーマ定義と初期化
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - マーケットカレンダー管理（営業日判定 / next/prev_trading_day 等）

- 研究・戦略
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量エンジニアリング（Z-score 正規化・ユニバースフィルタ）
  - シグナル生成（コンポーネントスコア統合、Bear レジーム抑制、BUY/SELL の算出）
  - 研究支援関数（将来リターン計算、IC 計算、ファクターサマリ等）

- ニュース収集
  - RSS 収集、前処理、記事ID生成、銘柄コード抽出、DB への冪等保存
  - SSRF 対策、受信サイズ制限、XML 安全パーサ使用

- 監査・実行ログ
  - signal_events / order_requests / executions 等の監査用スキーマ（トレーサビリティ確保）

---

## 必要条件（Prerequisites）

- Python 3.9+
- duckdb
- defusedxml
- （必要に応じて）J-Quants API アカウントとリフレッシュトークン

パッケージ依存は pyproject.toml / requirements に従ってください（本リポジトリに含まれる想定）。

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動ロードは、パッケージ内の検出ロジックがプロジェクトルート（`.git` または `pyproject.toml`）を見つけた場合に行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）

任意（デフォルトあり）:
- KABUSYS_ENV — 環境（development / paper_trading / live）デフォルト `development`
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）デフォルト `INFO`
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH — SQLite 用パス（監視等、デフォルト `data/monitoring.db`）

設定はコード上で `from kabusys.config import settings` 経由で参照できます（必須変数が無い場合は例外を送出します）。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install -r requirements.txt
   - または pyproject.toml を使う場合: pip install -e .
4. 環境変数を設定（またはプロジェクトルートに `.env` を作成）
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 使い方（代表的な API）

以下は Python スクリプト / REPL 上での例です。

- DuckDB の初期化（スキーマ作成）
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL（J-Quants からの差分取得・保存・品質チェック）
  ```
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を与えればその日を処理
  print(result.to_dict())
  ```

- 市場カレンダー更新（夜間バッチ等）
  ```
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- ニュース収集ジョブ
  ```
  from kabusys.data.news_collector import run_news_collection
  # known_codes を与えるとテキスト内の4桁銘柄コードのみ紐付けを行う
  res = run_news_collection(conn, known_codes={"7203","6758"})
  print(res)
  ```

- ファクター計算 / 特徴量作成
  ```
  from kabusys.strategy import build_features
  from datetime import date
  cnt = build_features(conn, date(2025, 1, 14))
  print("features upserted:", cnt)
  ```

- シグナル生成
  ```
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, date.today())
  print("signals written:", total)
  ```

- J-Quants から直接データ取得（低レベル）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings から自動取得
  recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意:
- これらの関数は DuckDB の接続（duckdb.DuckDBPyConnection）を直接受け取ります。
- ETL / 保存処理は冪等設計（ON CONFLICT）なので再実行が可能です。
- run_daily_etl は内部で市場カレンダーを参照して営業日に調整を行います。

---

## 主要モジュールと API の概要

（抜粋）

- kabusys.config
  - settings: 環境変数からの設定取得（JQUANTS_REFRESH_TOKEN 等）

- kabusys.data
  - jquants_client: fetch_* / save_* / get_id_token（API クライアント + 保存ロジック）
  - schema: init_schema, get_connection（DuckDB スキーマ初期化）
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - news_collector: fetch_rss, save_raw_news, run_news_collection
  - calendar_management: is_trading_day, next_trading_day, calendar_update_job
  - stats: zscore_normalize

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)

- kabusys.execution / monitoring
  - 実行・監視関連のレイヤ（スキーマ・構造は用意済み、実装は拡張可能）

---

## ディレクトリ構成

以下は主要ファイルのツリー（src/kabusys 以下を抜粋）:

- src/kabusys/
  - __init__.py          (バージョン、公開 API)
  - config.py            (環境変数・設定管理)
  - data/
    - __init__.py
    - jquants_client.py  (J-Quants API クライアント & 保存)
    - news_collector.py  (RSS 収集・保存・銘柄抽出)
    - schema.py          (DuckDB スキーマ定義・初期化)
    - stats.py           (zscore_normalize 等)
    - pipeline.py        (ETL パイプライン)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py           (監査ログスキーマ)
    - features.py        (公開インターフェース)
  - research/
    - __init__.py
    - factor_research.py (Momentum / Volatility / Value)
    - feature_exploration.py (IC / forward returns / summary)
  - strategy/
    - __init__.py
    - feature_engineering.py (feature 作成)
    - signal_generator.py    (シグナル生成)
  - execution/
    - __init__.py
  - monitoring/
    - (監視・運用用モジュール)
  - その他: README やドキュメント（DataPlatform.md, StrategyModel.md 等）を想定

---

## 運用上の注意

- 環境: `KABUSYS_ENV` により挙動（paper_trading / live）を切り替え可能です。実際の発注や資金管理を行う際は `live` 設定であることを確認してください。
- API レート制限: J-Quants はレートリミット（デフォルト 120 req/min）があるため、fetch は内部でスロットリングされます。
- ETL の再実行: 各保存処理は冪等性を保つよう設計されていますが、スキーマやデータモデルを変更した場合は注意してください。
- セキュリティ: RSS の取得時に SSRF 対策、XML の安全パーサ（defusedxml）を使用しているものの、運用環境ではネットワーク制御や機密情報の管理を徹底してください。
- ロギング: LOG_LEVEL を環境変数で指定可能。開発時は DEBUG、運用では INFO/WARNING 推奨。

---

## 貢献

- バグ修正、機能追加、ドキュメント改善歓迎です。Pull Request 前に issue を作成して議論してください。
- テスト、CI、コードスタイル（Black / Flake 等）の導入を推奨します。

---

必要であれば、README にサンプル .env.example、より詳細なデータベーススキーマ図、典型的な運用フロー（cron/airflow ジョブ例）や、kabuステーションとの発注連携方法（実装例）を追加できます。どの情報を優先して追記しますか？