# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（小規模プロジェクト向け）。  
J-Quants や RSS 等から市場データ・ニュースを取得し、DuckDB に保存して ETL／品質チェック、監査ログを提供します。

---

## プロジェクト概要

KabuSys は以下を主な目的とする Python パッケージです。

- J-Quants API から株価日足・財務・マーケットカレンダーを取得し DuckDB に保存
- RSS フィードからニュースを収集して前処理・保存・銘柄紐付け
- ETL パイプライン（差分取得、バックフィル、品質チェック）を実装
- マーケットカレンダー管理（営業日判定、次/前営業日取得など）
- 監査ログ（シグナル → 発注 → 約定 をトレースするテーブル群）を初期化
- 実行時の環境変数管理（.env 自動読み込み、必須チェック）

設計上の注力点：冪等性（ON CONFLICT）、Look-ahead bias 回避（fetched_at 記録）、API レート制御、リトライ、SSRF・XML 攻撃対策。

---

## 機能一覧

- jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等）
  - レートリミット（120 req/min）、リトライ（指数バックオフ）、401 自動リフレッシュ対応
- data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl：日次 ETL の統合エントリポイント（品質チェック含む）
- data.news_collector
  - RSS 取得（gzip 対応、サイズ制限）、記事正規化、ID 生成、DuckDB への保存、銘柄抽出
  - SSRF 防止、defusedxml による安全な XML 解析
- data.schema / data.audit
  - DuckDB のスキーマ初期化（Raw / Processed / Feature / Execution 層）
  - 監査ログテーブルの初期化（トレーサビリティ）
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック群と QualityIssue 型
- calendar_management
  - 営業日判定、next/prev/get_trading_days、calendar_update_job
- 環境変数管理（kabusys.config）
  - .env 自動ロード（.git または pyproject.toml を基準）、自動無効化フラグあり

---

## 前提条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（パッケージ管理は任意の方法で。簡易的には requirements.txt／pyproject.toml を用意して pip install してください）

---

## セットアップ手順 (ローカル開発向け)

1. リポジトリをクローン、仮想環境作成・有効化

   ```
   git clone <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（例）

   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトで pyproject.toml / requirements.txt があればそれに従ってください）

3. 環境変数を設定
   - プロジェクトルートに `.env` として保存するか、OS 環境変数として設定します。
   - 自動ロードはデフォルトで有効。無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   主要な環境変数（必須/任意）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - KABUSYS_ENV (任意, default: development) — 値: development / paper_trading / live
   - LOG_LEVEL (任意, default: INFO) — DEBUG/INFO/WARNING/ERROR/CRITICAL

   例 .env（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 初期化と使い方（簡易ガイド）

以下は Python REPL やスクリプト内で実行する例です。

1. DuckDB スキーマ初期化

   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイル作成＆テーブル作成
   ```

   - ":memory:" を渡すとインメモリ DB を使用できます。
   - init_schema は冪等（既存テーブルがあればスキップ）です。

2. 監査ログテーブルの初期化（監査専用 DB または同一 DB）

   ```python
   from kabusys.data.audit import init_audit_db, init_audit_schema

   # 監査専用 DB を作る場合
   audit_conn = init_audit_db("data/audit.duckdb")

   # 既存 conn に監査スキーマを追加する場合
   init_audit_schema(conn, transactional=True)
   ```

3. 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）

   ```python
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.data.schema import get_connection

   conn = get_connection("data/kabusys.duckdb")
   result = run_daily_etl(conn)  # target_date を省略すると今日
   print(result.to_dict())
   ```

   - run_daily_etl は各ステップを個別にエラーハンドリングし、ETLResult を返します。
   - id_token を注入してテスト可能（run_daily_etl(..., id_token="...")）。

4. News Collector（RSS 取得・保存・銘柄紐付け）

   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

   conn = get_connection("data/kabusys.duckdb")
   known_codes = {"7203", "6758", ...}  # 既知銘柄セット
   results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(results)  # {source_name: saved_count, ...}
   ```

   - URL スキーム検証、SSRF 防止、gzip/サイズ上限などの安全対策が入っています。
   - テスト時には内部の _urlopen をモックして外部ネットワークを切り離せます。

5. J-Quants からの直接取得（例: 日足取得）

   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes

   quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,1))
   ```

   - ライブラリは 120 req/min のレート制御、リトライ、401 時のトークン自動リフレッシュを内蔵しています。

---

## ログ・挙動設定

- LOG_LEVEL 環境変数でログレベルを制御（INFO がデフォルト）。
- KABUSYS_ENV で実行モードを指定（development / paper_trading / live）。
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` と `.env.local` を読み込みます。
  - OS 環境変数 > .env.local > .env の順で優先されます。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## セキュリティ・運用上の注意

- J-Quants API: レート制限（120 req/min）とリトライ戦略を守っていますが、運用時は API 利用規約を遵守してください。
- news_collector:
  - defusedxml を利用して XML 攻撃（XML Bomb 等）を防止しています。
  - SSRF 対策として URL スキーム検証、ホストがプライベート IP でないか検査、リダイレクト先の検査を行います。
  - レスポンスサイズに上限（10 MB）を設けています。
- DuckDB の接続は同時書き込みやバックアップの運用に注意してください（本ライブラリは単一プロセス想定の設計部分があります）。

---

## ディレクトリ構成

主なファイル・モジュール（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理（.env 自動ロード、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py            — RSS 取得・前処理・DuckDB 保存・銘柄抽出
    - schema.py                    — DuckDB スキーマ定義・init_schema
    - pipeline.py                  — ETL パイプライン（差分取得 / run_daily_etl 等）
    - calendar_management.py       — マーケットカレンダー管理 / 夜間更新ジョブ
    - audit.py                     — 監査ログスキーマ（signal/events/order_requests/executions）
    - quality.py                   — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py                  — 戦略層（拡張ポイント）
  - execution/
    - __init__.py                  — 発注/ブローカー連携（拡張ポイント）
  - monitoring/
    - __init__.py                  — 監視用ユーティリティ（未実装の雛形）

---

## 開発・拡張ポイント

- strategy / execution / monitoring パッケージは拡張用の空モジュールとして用意されています。具体的な戦略ロジックやブローカー API 連携はここに実装してください。
- テスト容易性のため、jquants_client の id_token 注入、news_collector の _urlopen モックが可能です。
- DuckDB を用いることでローカル環境で簡単にデータ保存・クエリができますが、本番ではファイル管理・バックアップを検討してください。

---

## サンプルコードまとめ

- スキーマ初期化と日次 ETL 実行

  ```python
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- RSS 収集と銘柄紐付け

  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758"}
  print(run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes))
  ```

---

README に書かれている手順はライブラリの主要機能をすばやく利用するためのものです。実運用ではログ設定、例外監視、バックアップ・リカバリ、認証情報管理（安全なシークレットストア利用）などの追加対策が必要です。必要があれば、README をベースに運用手順書（Runbook）やデプロイ手順も作成できます。