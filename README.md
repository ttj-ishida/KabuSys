# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ群（KabuSys）。  
Data（ETL / ニュース収集 / DuckDB スキーマ）、Research（ファクター計算・探索）、Strategy（特徴量作成・シグナル生成）、Execution（発注周り）、Monitoring 等の機能を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（各処理は target_date 時点のデータのみを使用）
- DuckDB を中心としたローカル DB で冪等（idempotent）にデータを保持
- 外部 API（J-Quants 等）クライアントはレート制限・リトライ・トークンリフレッシュを備える
- ETL / バッチ処理は差分更新と品質チェックを重視

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー）
  - RSS ニュース収集と銘柄紐付け
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - ETL パイプライン（差分取得、backfill、品質チェック）

- Research（研究用）
  - ファクター計算: モメンタム、ボラティリティ、バリュー等（prices_daily / raw_financials を参照）
  - 特徴量探索: 将来リターン計算、IC（Spearman）計算、統計サマリー

- Strategy（戦略層）
  - 特徴量エンジニアリング（Zスコア正規化、ユニバースフィルタ、features テーブルへの UPSERT）
  - シグナル生成（features と AI スコアの統合、BUY/SELL シグナル生成、売買ロジックの実装）

- Calendar / Management
  - JPX マーケットカレンダー管理（営業日判定、前後営業日・期間内営業日リスト取得）
  - 夜間カレンダー更新ジョブ

- その他
  - 統計ユーティリティ（Zスコア正規化）
  - 監査ログ（signal -> order -> execution のトレース用スキーマ）
  - セットアップ用の設定/環境変数読み込みユーティリティ

---

## 要件

- Python 3.10 以上（コード内での型演算子 `|` を使用）
- 推奨ライブラリ（プロジェクトに含める／インストールしてください）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants / RSS フィード）を行う場合は適切な API トークンやネットワーク環境が必要

---

## 環境変数（必須 / 主要）

以下はコード内で参照される主な環境変数です。`.env` をプロジェクトルートに置くことで自動読み込みされます（ただし自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV — 実行環境: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（デフォルト: INFO）
- DUCKDB_PATH — DuckDB の保存先（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動で .env をロードしない場合は `1`

.env の書き方は shell 形式（KEY=VALUE）で、export 形式やクォートもサポートします。

---

## セットアップ手順

1. リポジトリをクローン（既にコードがある前提）
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要ライブラリをインストール（例）
   - pip install duckdb defusedxml
   - 追加でrequests等を使う場合は適宜インストールしてください
4. 環境変数を用意
   - プロジェクトルートに `.env` を作成し、必須キーを記載
     例:
       JQUANTS_REFRESH_TOKEN="xxxx"
       KABU_API_PASSWORD="password"
       SLACK_BOT_TOKEN="xoxb-..."
       SLACK_CHANNEL_ID="C01234567"
5. DuckDB スキーマ初期化（下記「データベース初期化」の例を参照）

備考: パッケージ化されていない場合、ローカルで開発するならプロジェクトルートに PATH を通すか `pip install -e .` 等を検討してください（setup 配置次第）。

---

## データベース初期化（DuckDB）

Python REPL やスクリプトから DuckDB スキーマを初期化できます。

例（対話/スクリプト）:
- Python コマンド一行で :memory: を使う例
  python - <<'PY'
  from kabusys.data.schema import init_schema
  conn = init_schema(":memory:")
  print("initialized", conn)
  PY

- ファイルに保存する例（デフォルトパスは .env の DUCKDB_PATH あるいは data/kabusys.duckdb）
  python - <<'PY'
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  print("initialized", conn)
  PY

init_schema はテーブル作成を冪等に行います（既存テーブルはスキップ）。

---

## 使い方（代表的な操作）

以下は主要な API の使用例です。すべて DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得＋品質チェック）
  from datetime import date
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")  # 初回は init_schema を使う
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- 特徴量作成（features テーブルへ保存）
  from datetime import date
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import build_features

  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2025, 1, 31))
  print(f"features upserted: {n}")

- シグナル生成（features / ai_scores / positions を参照して signals へ書込）
  from datetime import date
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.strategy import generate_signals

  conn = init_schema("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2025, 1, 31))
  print(f"signals written: {total}")

- ニュース収集ジョブ（RSS 取得 -> raw_news 保存 -> news_symbols 紐付け）
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)

- カレンダー更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved calendar records:", saved)

注意:
- 各関数は内部でトランザクションを利用しており、失敗時はロールバックする設計です。
- ETL / API 呼び出しはネットワークを伴います。J-Quants トークンの設定が必要です。

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境変数からの設定一元管理
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.schema.get_connection(db_path) — 既存 DB への接続
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar — J-Quants データ取得
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar — DuckDB への保存（冪等）
- kabusys.data.pipeline.run_daily_etl — 日次 ETL の統合エントリポイント
- kabusys.research.calc_momentum / calc_volatility / calc_value — ファクター計算
- kabusys.strategy.build_features — features 作成（正規化・ユニバースフィルタ等）
- kabusys.strategy.generate_signals — signals 作成（BUY / SELL 判定）

---

## ディレクトリ構成（抜粋）

以下はコードベースに含まれる主要ファイルと役割の一覧です（与えられたソースを元に整理）。

- src/
  - kabusys/
    - __init__.py  — パッケージのエクスポート定義（version 等）
    - config.py    — 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py  — J-Quants API クライアント（取得・保存ロジック）
      - news_collector.py  — RSS ニュース取得・正規化・DB保存
      - schema.py          — DuckDB スキーマ定義と init_schema
      - stats.py           — 統計ユーティリティ（zscore_normalize）
      - pipeline.py        — ETL パイプライン（差分更新・品質チェック）
      - calendar_management.py — マーケットカレンダー管理
      - features.py        — data.stats の公開ラッパ
      - audit.py           — 監査ログ（signal/order/execution トレーサビリティ）スキーマ
      - (その他: quality 等が想定)
    - research/
      - __init__.py
      - factor_research.py — ファクター計算（momentum / volatility / value）
      - feature_exploration.py — IC / forward returns / 統計サマリー
    - strategy/
      - __init__.py
      - feature_engineering.py — features 作成ロジック（正規化・フィルタ）
      - signal_generator.py    — シグナル生成ロジック（BUY/SELL 判定）
    - execution/            — 発注周りの実装（空ファイルや実装想定）
    - monitoring/           — 監視・メトリクス周り（将来的なモジュール）

---

## 開発メモ / 注意点

- 型注釈や最新の構文（PEP 604 の | 型）を利用しているため Python 3.10 以上を想定しています。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）に基づくため、テスト/CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して明示的に環境を注入してください。
- J-Quants API はレート制限があるため jquants_client 内の RateLimiter を尊重してください（デフォルト 120 req/min）。
- RSS 収集では SSRF 対策や Gzip Bomb 対策、XML の安全なパースを組み込んでいます（defusedxml 使用）。
- DuckDB スキーマには外部キーやインデックス、CHECK 制約を多用しているため、DB のバージョン互換などに注意してください（コメントに DuckDB バージョン依存の注意があります）。

---

必要に応じて、README に追加したい具体的な実行コマンドや CI 設定、開発用スクリプト（Makefile / CLI）などのテンプレートを作成できます。どの部分を詳細に書き足しますか？