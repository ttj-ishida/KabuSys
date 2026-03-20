# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、DuckDB スキーマ・監査ログ等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された内部ライブラリ群です。主な役割は以下のとおりです。

- J-Quants API から株価・財務・市場カレンダーを取得して DuckDB に保存（差分取得・ページネーション・リトライ対応）
- ETL パイプライン（run_daily_etl）による日次データ更新と品質チェック
- 研究用に設計されたファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ）と features テーブルへの保存
- シグナル生成（final_score 計算、BUY/SELL 判定）と signals テーブルへの書き込み
- RSS ベースのニュース収集・記事保存・銘柄抽出
- DuckDB スキーマ定義、監査ログテーブル、実行層（orders / trades / positions 等）

設計方針として「ルックアヘッドバイアスの除去」「冪等性」「API レート制御」「トレーサビリティ」を重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants クライアント（jquants_client）
    - 株価日足（fetch_daily_quotes / save_daily_quotes）
    - 財務データ（fetch_financial_statements / save_financial_statements）
    - 市場カレンダー（fetch_market_calendar / save_market_calendar）
  - 差分ETL（data.pipeline）
    - run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl
- スキーマ管理
  - DuckDB のテーブル定義および初期化（data.schema:init_schema）
- 研究・特徴量
  - ファクター計算（research.factor_research: calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（research.feature_exploration: calc_forward_returns, calc_ic, factor_summary 等）
  - Zスコア正規化ユーティリティ（data.stats:zscore_normalize）
- 戦略
  - 特徴量構築（strategy.feature_engineering: build_features）
  - シグナル生成（strategy.signal_generator: generate_signals）
- ニュース収集
  - RSS 取得 / 前処理 / raw_news 保存 / 銘柄抽出（data.news_collector）
- カレンダー管理
  - 営業日判定、前後営業日取得、カレンダー更新ジョブ（data.calendar_management）
- 監査 / トレーサビリティ
  - signal_events / order_requests / executions など監査テーブル定義（data.audit）

---

## セットアップ手順

※ 下記は開発環境での例。環境に合わせて調整してください。

前提:
- Python 3.9+（型注釈の Union 演算子などが使われているため）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全対策）

1. リポジトリをクローン（既にコードがある場合は不要）:
   - git clone <リポジトリ>

2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール:
   - pip install duckdb defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください。必要に応じて追加パッケージをインストールしてください。）

4. 環境変数の設定:
   - .env ファイルをプロジェクトルートに置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みは無効化されます）。
   - 必須環境変数（Settings にて必須とされるもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト:
     - KABUSYS_ENV (development | paper_trading | live)  — デフォルト "development"
     - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL) — デフォルト "INFO"
     - DUCKDB_PATH — デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH — デフォルト "data/monitoring.db"

5. データベース初期化（DuckDB スキーマ作成）:
   - Python から init_schema を呼ぶ（例は次節の「使い方」を参照ください）。

---

## 使い方（簡単なコード例）

以下は代表的な操作のサンプルです。日付は datetime.date オブジェクトを使用します。

1) DuckDB スキーマ初期化:
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")

2) 日次 ETL 実行（J-Quants から差分取得して保存・品質チェック）:
   - from kabusys.data.pipeline import run_daily_etl
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")
   - result = run_daily_etl(conn)  # target_date は省略で今日

   ETLResult オブジェクトに取得/保存件数や品質チェック結果が含まれます。

3) 特徴量構築（features テーブルへ書き込む）:
   - from kabusys.strategy import build_features
   - from datetime import date
   - count = build_features(conn, date(2024, 1, 5))

4) シグナル生成（signals テーブルへ書き込む）:
   - from kabusys.strategy import generate_signals
   - from datetime import date
   - total = generate_signals(conn, date(2024, 1, 5))
   - 生成時に weights や閾値をカスタム指定可能:
     generate_signals(conn, date(2024,1,5), threshold=0.65, weights={"momentum":0.5, "value":0.2, "volatility":0.15, "liquidity":0.1, "news":0.05})

5) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）:
   - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   - saved_map = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})  # known_codes を渡すと銘柄抽出して news_symbols に保存

6) J-Quants データ取得を直接使う（テストやバッチ用）:
   - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   - records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,5))
   - saved = save_daily_quotes(conn, records)

7) カレンダー/営業日ユーティリティ:
   - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
   - is_trading_day(conn, date(2024,1,1))
   - next_trading_day(conn, date(2024,1,1))
   - get_trading_days(conn, date(2024,1,1), date(2024,1,31))

注意:
- すべての DB 操作は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。初回は init_schema() でスキーマを作成してください。
- J-Quants API 呼び出しはレート制御とリトライロジックが実装されています。認証トークン管理は jquants_client が行います（settings.jquants_refresh_token を使用）。

---

## 環境変数（Settings）

config.Settings で読み取る主な環境変数は次の通りです。必須となるものは _require により未設定時に例外が発生します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env ファイルの自動ロードを無効化

.env のパースは独自実装があり、コメントや export 形式、クォートを考慮して読み込みます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
- src/kabusys/data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント & 保存ロジック
  - news_collector.py        — RSS ニュース収集 / 前処理 / 保存
  - schema.py                — DuckDB スキーマ定義・初期化（init_schema）
  - stats.py                 — zscore_normalize 等の統計ユーティリティ
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py   — 市場カレンダー管理 / 営業日ユーティリティ
  - audit.py                 — 監査ログ用テーブル定義
  - features.py              — features 関連の公開ユーティリティ
- src/kabusys/research/
  - __init__.py
  - factor_research.py       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py   — IC / forward returns / summary
- src/kabusys/strategy/
  - __init__.py
  - feature_engineering.py   — features 構築（正規化・ユニバースフィルタ）
  - signal_generator.py      — final_score 計算・BUY/SELL 判定
- src/kabusys/execution/       — 発注 / execution 関連のプレースホルダ（初期構成で空）

（上記はソース内に実装されたモジュールの要約です。細かな補助関数やユーティリティは各ファイル内にあります。）

---

## 運用上の注意点

- ルックアヘッドバイアスに注意: 特徴量・シグナル生成は target_date 時点の情報のみを使用する方針で実装されています。ETL の順序・時刻管理に注意してください。
- 冪等性: 多くの保存関数は ON CONFLICT を使って冪等動作を担保しています。バルク挿入やトランザクションにより原子性が考慮されていますが、運用ではトランザクション境界に注意してください。
- レート制限: J-Quants API はレート制限（120 req/min）があります。jquants_client は固定間隔スロットリングを実装していますが、大規模バッチ運用時はスロットリングの影響を考慮してください。
- セキュリティ: news_collector は SSRF 対策や XML の安全パース（defusedxml）を実装しています。外部 URL の取り扱いには注意してください。
- テスト: モジュールは依存注入（id_token を渡す等）や小さなユーティリティ単位でテストしやすい設計になっています。

---

必要に応じて README を拡張（例: より詳細な API リファレンス、CI / デプロイ手順、運用 runbook）できます。追加でドキュメント化したい箇所があれば教えてください。