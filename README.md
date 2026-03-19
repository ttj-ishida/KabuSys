# KabuSys

日本株向け自動売買システムのライブラリ群です。データ取得（J-Quants）、ETL、特徴量計算、戦略シグナル生成、ニュース収集、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買基盤（研究→データプラットフォーム→戦略→発注／監視）を構築するための共通ライブラリです。主な設計方針は以下のとおりです。

- DuckDB を用いたローカルデータベースにデータを永続化（冪等性を確保した保存処理）
- J-Quants API からのデータ取得（レートリミット、リトライ、トークン自動リフレッシュを実装）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 特徴量生成 → シグナル生成（重み付け合算、Bear レジーム抑制、エグジット判定）
- ニュース収集（RSS、SSRF対策、記事ID正規化、銘柄抽出）
- 監査ログ / 発注トレーサビリティ用スキーマ

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理（.env / 環境変数の自動読み込みと検証）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを抑止可能
- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミット制御（120 req/min）
  - 再試行（指数バックオフ）、401 時のトークン自動リフレッシュ
  - データ取得（株価、財務、マーケットカレンダー）と DuckDB への冪等保存
- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - init_schema() による初期化
- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（カレンダー / 株価 / 財務 の差分取得と保存）
  - 差分再取得（backfill）・トレーディングデイ補正・品質チェック呼び出し
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML デフュージョン対策、SSRF 対策、ID 正規化、銘柄抽出
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev_trading_day、カレンダー差分更新
- 統計ユーティリティ（kabusys.data.stats）
  - クロスセクション Z スコア正規化（zscore_normalize）
- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタム、ボラティリティ（ATR）、バリュー（PER/ROE）など
  - feature_exploration: 将来リターン計算、IC（Spearman）や統計サマリ
- 特徴量生成（kabusys.strategy.feature_engineering）
  - research で算出した raw factor を統合・フィルタ（株価・流動性）・正規化して features テーブルへ保存
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を組み合わせ、コンポーネントスコアを重み合算して final_score を算出
  - Bear レジームで BUY を抑制、エグジット判定（ストップロス／スコア低下）で SELL を生成
  - signals テーブルへ冪等書き込み
- 監査ログ（kabusys.data.audit）
  - signal → order_request → executions のトレースを保持するスキーマ

（補足）execution モジュールはルートに存在し、発注実装を接続する想定です。

---

## セットアップ手順

前提:
- Python 3.9+（typing の一部記法を利用）
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローン／コピーしてプロジェクトルートへ移動。

2. 仮想環境を作成して有効化（任意）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール:
   - 必須: duckdb, defusedxml
   - 例:
   ```bash
   pip install duckdb defusedxml
   ```
   プロジェクトに requirements ファイルがある場合はそれを使用してください。

4. 環境変数（.env）を用意:
   - 必須（Settings.require で必須化されているもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - オプション（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. データベーススキーマの初期化:
   Python REPL やスクリプトで次を実行します。
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

---

## 使い方（簡易ガイド）

以下は典型的なワークフロー例です。実運用用のラッパースクリプトを作成して cron / scheduler で呼び出してください。

1. DuckDB の初期化（上記のとおり）:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

2. 日次 ETL 実行（市場カレンダー・株価・財務の差分取得と品質チェック）:
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

3. 特徴量の構築（research の raw factor を取り込んで features テーブルへ保存）:
   ```python
   from kabusys.strategy import build_features
   from datetime import date

   n = build_features(conn, date.today())
   print(f"features built: {n}")
   ```

4. シグナル生成（features + ai_scores → signals）:
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date

   total = generate_signals(conn, date.today(), threshold=0.6)
   print(f"signals generated: {total}")
   ```

5. ニュース収集ジョブ（RSS から raw_news を収集）:
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758', ...})
   print(results)
   ```

注意点:
- ETL / データ取得では settings.jquants_refresh_token を使用して J-Quants の id_token を取得します。環境変数の設定を忘れないでください。
- 自動ロードされる .env はプロジェクトルート（.git または pyproject.toml を基準）を探索して読み込みます。
- 各データ保存関数は ON CONFLICT / トランザクションにより冪等性・原子性を担保します。

---

## 主要モジュールの使いどころ（サマリ）

- kabusys.config
  - settings: 環境変数経由の設定管理（必須キーは例外を投げる）
- kabusys.data.jquants_client
  - fetch_* / save_* 関数で取得→保存を行う
- kabusys.data.schema
  - init_schema(db_path) でテーブルを作成
- kabusys.data.pipeline
  - run_daily_etl() / run_prices_etl() / run_financials_etl() / run_calendar_etl()
- kabusys.data.news_collector
  - fetch_rss(), save_raw_news(), run_news_collection()
- kabusys.research
  - calc_momentum(), calc_volatility(), calc_value(), calc_forward_returns(), calc_ic(), factor_summary()
- kabusys.strategy
  - build_features(), generate_signals()

---

## ディレクトリ構成

リポジトリ内の主要ファイル・ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - features.py
      - stats.py
      - audit.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - strategy/
      - __init__.py
      - feature_engineering.py
      - signal_generator.py
    - execution/
      - __init__.py
    - monitoring/  (パッケージ名は __all__ にあるが実装ファイルはプロジェクトで管理)

各モジュールはドキュメントストリング（docstring）で設計意図や処理フローを詳細に説明しています。実装は DuckDB を中心に SQL と Python を組み合わせた構成で、運用面（トランザクション、冪等性、ログ）に配慮されています。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携で使用）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意・デフォルトあり:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live) — default: development
- LOG_LEVEL — default: INFO

.env の書式は Bourne 互換でクォートやコメント処理に柔軟に対応します（config._parse_env_line を参照）。

---

## 開発・テスト時のヒント

- 自動で .env を読み込ませたくない場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで環境分離する際に便利です）。
- DuckDB の一時 DB を使う場合:
  init_schema(":memory:") を指定してインメモリ DB を利用可能です。
- ログや例外は各モジュールで詳細に出力するため、問題解析はログレベルを DEBUG に上げると良いです。

---

## 貢献・拡張

- execution 層に各ブローカーのコネクタ（kabuステーションなど）を実装して発注フローを接続してください。
- quality モジュール（データ品質チェック）は pipeline から呼ばれます。カスタムチェックを追加して品質基準を強化できます。
- AI スコア生成・外部 NLP モデルは ai_scores テーブルへ結果を保存すれば戦略で使用できます。

---

以上がこのコードベースの概要と基本的な使い方です。詳細は各モジュールの docstring（該当ファイル先頭）を参照してください。追加で README に含めたい実行例や運用手順があれば教えてください。