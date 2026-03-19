# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に用い、J-Quants API からのデータ取得、ETL、品質チェック、ファクター計算、ニュース収集、監査ログ等の基盤機能を提供します。

---

## 概要

KabuSys は以下の責務を持つモジュール群から構成されるライブラリです。

- data: データ取得（J-Quants クライアント）、ETL パイプライン、DuckDB スキーマ・初期化、品質チェック、ニュース収集
- research: ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- strategy: 戦略ロジック（拡張ポイント）
- execution: 発注・ブローカー連携（拡張ポイント）
- monitoring: 監視・可観測性（拡張ポイント）
- config: 環境変数 / 設定管理

設計方針として、DuckDB への SQL ベースの処理を多用し、外部ライブラリへは依存を最小化しています（ただし実行には `duckdb` / `defusedxml` 等が必要です）。

---

## 主な機能一覧

- J-Quants API クライアント
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - レート制限・リトライ・トークン自動リフレッシュ対応
  - DuckDB への冪等保存 (save_daily_quotes, save_financial_statements, save_market_calendar)
- DuckDB スキーマ定義・初期化
  - raw / processed / feature / execution / audit 層のテーブル DDL とインデックス
  - init_schema(), init_audit_db()
- ETL パイプライン
  - 差分取得（最終取得日基準の差分更新）・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（run_all_checks）
- ニュース収集
  - RSS 取得・前処理・記事保存・銘柄抽出・紐付け（run_news_collection）
  - SSRF 対策・サイズ制限・トラッキングパラメータ除去等の安全対策
- 研究用ユーティリティ
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（クロスセクション正規化）
- 監査（Audit）
  - signal / order_request / execution の監査テーブルと初期化ユーティリティ

---

## セットアップ手順

前提:
- Python 3.10 以上（ソースで `X | Y` 型注釈を使用）
- git が使える環境

1. リポジトリをクローン（既にプロジェクト配備済みであれば省略）
   ```bash
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   最小限の依存は `duckdb` と `defusedxml` です。パッケージ化されていれば `pip install -e .` を推奨します。

   例（最小インストール）:
   ```bash
   pip install duckdb defusedxml
   ```

   例（開発インストール）:
   ```bash
   pip install -e .
   ```

4. 環境変数 (.env) を用意する  
   プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただしテスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   必須の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API パスワード（発注連携で使用）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

   任意:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   .env の一例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

以下は Python REPL やスクリプトからの代表的な呼び出し例です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  from kabusys.config import settings

  # settings.duckdb_path は環境変数 DUCKDB_PATH を参照
  conn = schema.init_schema(settings.duckdb_path)
  ```

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # conn は init_schema の戻り値
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection

  # known_codes は銘柄コードセット（例: {'7203', '6758', ...}）
  stats = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(stats)
  ```

- J-Quants からデータ取得（単独利用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, zscore_normalize
  from datetime import date

  momentum = calc_momentum(conn, date(2024, 2, 1))
  volatility = calc_volatility(conn, date(2024, 2, 1))

  # 複数ファクターを Z スコア正規化
  normed = zscore_normalize(momentum, columns=["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査ログスキーマ初期化（監査専用 DB を別に用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

---

## 環境 / 実行モード

- KABUSYS_ENV（settings.env）により実行モードを切替できます:
  - development
  - paper_trading
  - live

- ログレベルは LOG_LEVEL 環境変数で調整します（デフォルト: INFO）。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（settings）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py      — RSS ニュース収集 / 保存 / 銘柄抽出
    - schema.py              — DuckDB スキーマ定義・init_schema
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - features.py            — 特徴量ユーティリティ公開 (再エクスポート)
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログスキーマ / 初期化
    - quality.py             — データ品質チェック
    - etl.py                 — ETL 公開インターフェース
  - research/
    - __init__.py            — 研究用 API 再エクスポート
    - feature_exploration.py — 将来リターン・IC・summary 等
    - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - strategy/
    - __init__.py            — 戦略層（拡張ポイント）
  - execution/
    - __init__.py            — 発注層（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視（拡張ポイント）

---

## 注意事項 / ベストプラクティス

- .env の取り扱い:
  - プロジェクトルートにある `.env` / `.env.local` が自動読み込みされます（config._find_project_root により .git または pyproject.toml を探索）。
  - テストや特殊な状況で自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB:
  - 初回は schema.init_schema() を呼んでテーブルを作成してください。既存 DB に対しては init_schema は冪等です。
  - 監査ログは必要に応じて init_audit_db() または init_audit_schema() で追加してください。

- セキュリティ:
  - news_collector は SSRF・XML 脆弱性対策（defusedxml、URL 検査、受信サイズ制限等）を実装していますが、運用時は監視とテストを怠らないでください。

- 実運用:
  - 発注・接続周り（kabu API や証券会社連携）は production（live）モードでの取り扱いに注意してください。paper_trading モード等で十分に検証した上で切り替えてください。

---

README にない詳細（API のパラメータ仕様や内部ロジックの補足）は、各モジュールの docstring を参照してください。必要であれば、具体的な利用例やデプロイ手順、CI/CD・監視連携のテンプレートを追加で用意します。