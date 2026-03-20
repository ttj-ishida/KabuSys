# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ミニマル実装）。  
データ取り込み（J-Quants）、DuckDB ベースのスキーマ、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理など、研究→運用までの主要機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成する以下の機能群をモジュール化したライブラリです。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB によるデータスキーマと冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- 研究用ファクター計算（Momentum / Volatility / Value 等）
- 特徴量エンジニアリング（Z スコア正規化、ユニバースフィルタ）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL 判定）
- ニュース収集（RSS → raw_news、銘柄抽出）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 発注・監査（スキーマ・テーブル定義） — Execution 層用スキーマを含む

設計方針は「ルックアヘッドバイアス回避」「冪等性」「外部依存の最小化」「運用でのトレーサビリティ確保」です。

---

## 主な機能一覧

- data/jquants_client
  - J-Quants API クライアント（レート制限・リトライ・トークン自動更新）
  - データ保存用の冪等 `save_*` 関数（raw_prices, raw_financials, market_calendar など）
- data/schema
  - DuckDB 用スキーマ定義と初期化（init_schema）
- data/pipeline
  - 日次 ETL（差分取得、保存、品質チェック）: `run_daily_etl`
  - 個別 ETL: `run_prices_etl`, `run_financials_etl`, `run_calendar_etl`
- data/news_collector
  - RSS 取得、前処理、raw_news 保存、記事⇆銘柄紐付け
- data/calendar_management
  - 営業日判定、next/prev_trading_day、calendar_update_job
- research
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 解析ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- strategy
  - 特徴量構築（build_features）
  - シグナル生成（generate_signals）
- config
  - .env/環境変数読み込み・設定管理（自動読み込み機能あり）

---

## セットアップ手順

前提:
- Python 3.9+ （typing の union 型等を使用）
- ネットワーク経由の外部 API（J-Quants）にアクセス可能な環境

1. レポジトリをクローン / パッケージをプロジェクトに追加

2. 依存パッケージをインストール（例: pip）
   - 本コードで明示されている外部依存は最小限です。主に duckdb と defusedxml が必要です。
   - 例:
     ```
     pip install duckdb defusedxml
     ```
   - 実際は pyproject.toml / requirements.txt に基づいてインストールしてください。

3. 環境変数を準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード（実装は参照用）
     - SLACK_BOT_TOKEN : Slack 通知用の Bot トークン（必要に応じて）
     - SLACK_CHANNEL_ID : Slack チャンネル ID
   - 任意:
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH : SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. DuckDB スキーマ初期化
   - Python REPL かスクリプトで実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")  # :memory: も可
     conn.close()
     ```

---

## 使い方（基本的なフロー例）

1. DuckDB 初期化（先述）

2. 日次 ETL の実行（市場カレンダー → 株価 → 財務 → 品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.schema import get_connection, init_schema
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   conn.close()
   ```

3. 研究モジュールでファクターを計算し、特徴量を構築
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   n = build_features(conn, target_date=date.today())
   print(f"features upserted: {n}")
   ```

4. シグナル生成（features と ai_scores を元に BUY/SELL を signals テーブルへ書き込む）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"total signals: {total_signals}")
   ```

5. ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄抽出）
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   results = run_news_collection(conn, sources=None, known_codes={"7203", "6758"})
   print(results)
   ```

6. マーケットカレンダー更新（夜間バッチ）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意:
- 各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema はスキーマ作成済み接続を返します。get_connection は既存 DB への接続を返します（初回は init_schema を推奨）。
- サンプルコードは最小実行例です。実運用ではエラーハンドリングやリトライ、ロギング設定を行ってください。

---

## 環境変数と自動読み込み

- config モジュールはプロジェクトルート（.git または pyproject.toml を上位ディレクトリで探索）を検出し、自動で `.env` → `.env.local` の順に読み込みます。
- 自動読み込みを無効にする: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
- 必須環境変数を参照するプロパティは値が無いと `ValueError` を投げます（例: settings.jquants_refresh_token）。

主要な設定プロパティ:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path)
- settings.sqlite_path (Path)
- settings.env (development / paper_trading / live)
- settings.log_level

---

## ディレクトリ構成 (主要ファイル)

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント + 保存ロジック
    - news_collector.py         — RSS 取得・記事処理・保存
    - schema.py                 — DuckDB スキーマ定義と init_schema / get_connection
    - stats.py                  — zscore_normalize 等の統計ユーティリティ
    - features.py               — data.stats の再エクスポート
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー管理
    - audit.py                  — 監査ログ / 発注トレース用スキーマ
    - execution/                — (発注実行用モジュール; 空の __init__ がある)
  - research/
    - __init__.py
    - factor_research.py        — calc_momentum, calc_volatility, calc_value
    - feature_exploration.py    — IC, forward returns, factor_summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py    — build_features
    - signal_generator.py       — generate_signals
  - monitoring/                 — 監視用 DB/ロジック（ディレクトリ存在想定）
- README.md (本ファイル)

---

## 運用上の注意

- DuckDB のファイルパスはデフォルト `data/kabusys.duckdb`。ディスクパスのバックアップ・権限管理を検討してください。
- J-Quants の API レート制限（120 req/min）を守るため内部でスロットリングを実装していますが、運用スケジュール次第ではジョブを分散してください。
- AI スコアや外部シグナルを組み込む場合、特徴量生成／シグナル生成は「target_date 時点で利用可能な情報のみ」を利用する設計を守ってください（ルックアヘッドバイアス回避）。
- raw データは ON CONFLICT DO UPDATE 等で冪等保存を行います。重複挿入や再取得を安心して実行できます。
- ニュース収集は SSRF や XML Bomb 等のリスク対策を組み込んでいますが、外部 RSS の多用には注意してください。

---

## 貢献 / テスト

- 現状はライブラリ本体の実装ベースです。ユニットテスト・CI 設定は別途追加すると良いでしょう。
- 環境依存の機能（J-Quants、kabu API、Slack など）はモック化してテストを作成してください。

---

質問や README の追記要望があれば教えてください。具体的に使いたいユースケース（例: ETL スケジュール cron、バックテストフロー）をいただければ、サンプルスクリプトも用意します。