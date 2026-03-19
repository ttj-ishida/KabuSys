# KabuSys

日本株向け自動売買 / データ基盤ライブラリ

---

## プロジェクト概要

KabuSys は日本株のデータ収集・前処理・特徴量作成・シグナル生成・監査ログを想定した内部ライブラリ群です。  
主に以下の役割を担います。

- J-Quants API からの株価・財務・カレンダー取得（差分取得・ページネーション・リトライ・レート制御）
- DuckDB を使ったデータスキーマ定義と永続化（Raw → Processed → Feature → Execution 層）
- ファクター（Momentum / Volatility / Value 等）の計算、Z スコア正規化、特徴量テーブルへの永続化
- 特徴量と AI スコアを統合したシグナル（BUY/SELL）の生成（冪等処理）
- RSS からのニュース収集と銘柄紐付け（SSRF 対策・トラッキング除去・安全な XML パース）
- ETL パイプライン（差分更新・品質チェック）とカレンダー管理
- 発注・実行・監査ログ用のスキーマ（監査トレーサビリティを重視）

設計ではルックアヘッドバイアスの排除、冪等性、外部 API の差分取得・リトライやレート制御、セキュリティ（SSRF、XML 脆弱性）に配慮しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルートを探索）
  - 必須環境変数の検証（例: JQUANTS_REFRESH_TOKEN 等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・保存ユーティリティ）
  - schema: DuckDB のテーブル定義と初期化（init_schema）
  - pipeline: 日次 ETL（差分取得・backfill・品質チェック）
  - news_collector: RSS 取得と raw_news 保存、銘柄抽出
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - stats / features: Z スコア正規化などの統計ユーティリティ
  - audit: 発注〜約定をトレースする監査テーブル定義
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等ファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman ρ）やファクター統計サマリー
- kabusys.strategy
  - feature_engineering: raw ファクターを組み合わせて features テーブルへ保存
  - signal_generator: features と ai_scores を統合して BUY/SELL を生成し signals テーブルへ保存
- kabusys.execution
  - 発注・実行ロジックのためのパッケージプレースホルダ（実装は別途）

---

## 要件

- Python 3.10 以上（PEP 604 の型合字 "A | B" を使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, datetime, logging, math など）を多用

（実際のパッケージ依存はプロジェクト配布時の requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール

   例（最低限）:

   ```bash
   pip install duckdb defusedxml
   ```

   開発用やテスト用の依存がある場合は `requirements.txt` / `pyproject.toml` を参照してインストールしてください。

4. 環境変数（.env）を設定

   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   例 `.env`（必須項目はプロジェクトで使う機能に応じて）:

   ```
   # J-Quants 認証
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabuステーション API（発注を行う場合）
   KABU_API_PASSWORD=your_kabu_password
   # KABU_API_BASE_URL optional (デフォルト: http://localhost:18080/kabusapi)

   # Slack 通知（必要なら）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C1234567890

   # DB パス (DuckDB)
   DUCKDB_PATH=data/kabusys.duckdb

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な例）

以下は基本的な操作例です。すべて DuckDB の接続オブジェクト（kabusys.data.schema.init_schema 等で取得）を渡して動作します。

1. DuckDB スキーマの初期化

   ```python
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   ```

   - `db_path` に `":memory:"` を渡すとインメモリ DB になります。
   - 初回実行で親ディレクトリがなければ自動作成します。

2. 日次 ETL を実行（J-Quants から差分取得して保存）

   ```python
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn)  # target_date を省略すると今日
   print(result.to_dict())
   ```

   - 市場カレンダー → 株価 → 財務の順に差分取得します。
   - 品質チェック（quality モジュール）も実行され、問題を集約して返します。

3. 研究モジュールでファクター計算（例: calc_momentum）

   ```python
   from kabusys.research import calc_momentum
   from datetime import date

   rows = calc_momentum(conn, date(2024, 1, 31))
   ```

4. 特徴量作成（features テーブルへ保存）

   ```python
   from kabusys.strategy import build_features
   from datetime import date

   count = build_features(conn, date(2024, 1, 31))
   print(f"features upserted: {count}")
   ```

5. シグナル生成（signals テーブルへ保存）

   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total_signals = generate_signals(conn, date(2024, 1, 31))
   print(f"signals saved: {total_signals}")
   ```

6. RSS ニュース収集

   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   known_codes = {"7203", "6758", ...}  # 事前に銘柄コード一覧を準備
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)
   ```

7. カレンダー更新ジョブ（夜間バッチ）

   ```python
   from kabusys.data.calendar_management import calendar_update_job

   saved = calendar_update_job(conn)
   print("calendar saved:", saved)
   ```

注意点:
- 各関数は冪等に設計されています（同じ日付の再実行で重複を発生させない）。
- エラーは適切にロギングされ、ETL の場合は処理を継続する設計です（呼び出し側で結果を確認してください）。

---

## 環境変数一覧（代表）

必須・主要な環境変数（settings を参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (発注を行う場合は必須)
- KABU_API_BASE_URL (省略可、デフォルト http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (通知機能を使う場合)
- SLACK_CHANNEL_ID (通知機能を使う場合)
- DUCKDB_PATH (省略可、デフォルト data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB 等)
- KABUSYS_ENV (development | paper_trading | live) — 動作モード
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化（テスト用）

settings オブジェクトから安全に取得できます（kabusys.config.settings）。

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数管理・自動 .env ロード
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得・保存）
    - schema.py                       — DuckDB スキーマ定義 & init_schema
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - news_collector.py               — RSS 収集、raw_news / news_symbols 保存
    - calendar_management.py          — JPX カレンダー操作ユーティリティ
    - features.py                     — 統計ユーティリティの公開インターフェース
    - stats.py                        — zscore_normalize 等
    - audit.py                        — 監査ログスキーマ（signal_events / order_requests / executions）
    - audit.py                        — 監査ログ定義
    - (その他 data.*)
  - research/
    - __init__.py
    - factor_research.py              — mom/vol/val の計算
    - feature_exploration.py          — 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py          — features 作成処理
    - signal_generator.py             — final_score 計算・BUY/SELL 生成
  - execution/
    - __init__.py                     — 発注層（プレースホルダ）
  - monitoring/                       — 監視/メトリクス（プレースホルダ）

（README はプロジェクトの実際のトップレベル構成に合わせて調整してください）

---

## 開発・運用上の補足

- ロギング: settings.log_level に従ってログレベルが設定されます。運用では INFO/WARNING、デバッグ時は DEBUG を推奨。
- 冪等性: ETL や保存関数は ON CONFLICT や INSERT ... RETURNING を用いて冪等に設計されています。
- セキュリティ: RSS 取得は SSRF 対策・gzip サイズチェック・defusedxml を使った安全な XML パースを行っています。
- テスト: 自動 .env ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 本番切替: KABUSYS_ENV を `paper_trading` または `live` に切り替えて運用モードを区別してください。live モードでは実際の発注処理の実行に注意が必要です。

---

この README はコードベースの現状（主要モジュールのサマリ）に基づく利用手引きです。詳細な仕様（StrategyModel.md / DataPlatform.md 等）や運用手順、CI/CD、テストケースは別途ドキュメントにまとめてください。