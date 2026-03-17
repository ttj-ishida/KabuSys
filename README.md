# KabuSys

日本株向け自動売買/データ基盤ライブラリ。J-Quants API や RSS を用いたデータ収集、DuckDB によるスキーマ管理、ETL パイプライン、品質チェック、監査ログ機能などを備えたモジュール群です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムの基盤的機能を提供する Python パッケージです。主に以下の用途を想定しています。

- J-Quants API からの市場データ（株価日足、財務データ、JPX カレンダー）取得
- RSS フィードからニュース記事を収集し、銘柄との紐付けを行う
- DuckDB を用いたスキーマ定義・データ永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- カレンダー管理（営業日判定、next/prev 営業日取得）
- 監査ログ（signal → order → execution のトレーサビリティ）
- 各種運用上の安全策（API レート制限、リトライ、SSRF 対策、XML パースの安全化 等）

設計上、ETL・保存操作は冪等性を考慮しており、DuckDB 側では ON CONFLICT / RETURNING を活用します。

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - 株価日足、財務データ、カレンダー取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_* 系）

- data/news_collector.py
  - RSS フィード取得・パース・前処理
  - トラッキングパラメータ除去、URL 正規化から SHA-256 ベースの記事 ID 生成
  - defusedxml による安全な XML パース、SSRF 対策、受信サイズ制限
  - raw_news / news_symbols への保存（チャンク挿入・トランザクション）

- data/schema.py
  - DuckDB スキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) による初期化と接続取得
  - インデックス定義

- data/pipeline.py
  - 日次 ETL パイプライン（run_daily_etl）
  - 差分更新・バックフィル・品質チェック（quality モジュール連携）
  - run_prices_etl / run_financials_etl / run_calendar_etl の個別実行も可能

- data/calendar_management.py
  - market_calendar を用いた営業日判定（is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days）
  - calendar_update_job による夜間更新（バックフィル・健全性チェック）

- data/audit.py
  - 監査ログ用テーブル定義（signal_events / order_requests / executions）
  - init_audit_schema / init_audit_db による監査 DB 初期化
  - UTC 固定などトレーサビリティ向けの設計

- data/quality.py
  - 欠損、スパイク（前日比）・重複・日付不整合のチェック
  - QualityIssue を返す（重大度に応じて呼び出し元が処理を決定）

- config.py
  - .env ファイルまたは環境変数から設定読み込み（自動ロード機能）
  - 必須値の取得・検証（J-Quants トークン等）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化

- strategy, execution, monitoring
  - パッケージ構造としてプレースホルダ。戦略・発注・監視ロジックを配置する想定領域

---

## 前提・依存関係

- Python 3.10 以上（PEP 604 の | 型注釈等を使用）
- 必要なライブラリ（少なくとも以下をインストールしてください）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install duckdb defusedxml
```

（実際のアプリケーションでは追加の依存（HTTP クライアントや Slack SDK 等）が必要になる可能性があります）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. 必要ライブラリをインストール
   ```bash
   python -m pip install --upgrade pip
   python -m pip install duckdb defusedxml
   ```
4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を用意できます。自動ロードの優先順位は:
     OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注機能使用時）
     - SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
     - SLACK_CHANNEL_ID      : Slack チャンネル ID
   - 任意:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB のパス。デフォルト data/monitoring.db)

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB スキーマ作成）
   Python REPL やスクリプトで以下を実行:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")  # ファイル DB。":memory:" も可
   conn.close()
   ```

6. 監査ログ用 DB 初期化（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   audit_conn.close()
   ```

---

## 使い方（基本例）

以下は主要機能の簡単な呼び出し例です。実運用ではログ設定・例外ハンドリング・スケジューラ等を組み合わせてください。

- 日次 ETL を実行する（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")  # 初期化済みであれば get_connection でも可

result = run_daily_etl(conn)  # 引数で target_date, id_token, run_quality_checks などを指定可
print(result.to_dict())
conn.close()
```

- ニュース収集ジョブを実行する
```python
from kabusys.data.schema import get_connection, init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 事前に取得しておく有効銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
conn.close()
```

- J-Quants から株価を直接取得して保存する（テスト・デバッグ用）
```python
from kabusys.data.schema import init_schema
from kabusys.data import jquants_client as jq

conn = init_schema("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"fetched={len(records)} saved={saved}")
conn.close()
```

- 市場カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("calendar saved:", saved)
conn.close()
```

- 品質チェックのみ実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
conn.close()
```

---

## 設計上の注意点 / 運用メモ

- J-Quants API のレートは 120 req/min に制限されています。本ライブラリでは固定間隔の RateLimiter を実装しており、リクエスト送出の間隔を自動調整します。
- HTTP エラー（408, 429, 5xx 等）はリトライ（指数バックオフ）します。401 を受けた場合はリフレッシュトークンで ID トークンを更新して 1 回だけリトライします。
- ニュース収集は SSRF 対策（リダイレクト検査、プライベート IP 拒否）、defusedxml による安全な XML パース、受信サイズ制限などの防護を備えています。
- DuckDB に保存する際は多くの箇所で ON CONFLICT（冪等性）や INSERT ... RETURNING（実挿入件数の把握）を使用しており、再実行耐性を高めています。
- audit テーブルは削除を想定しない設計（監査ログ）です。UTC 固定のタイムゾーンを使用します。
- 環境変数自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を読み込みます。テスト時に自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

以下はパッケージ内部の主なファイル構成（src/kabusys 配下）です。

- src/kabusys/
  - __init__.py
  - config.py                        -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（取得・保存）
    - news_collector.py              -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py         -- カレンダー管理・営業日判定
    - audit.py                       -- 監査ログスキーマ初期化
    - quality.py                     -- データ品質チェック
  - strategy/
    - __init__.py                    -- 戦略モジュール用プレースホルダ
  - execution/
    - __init__.py                    -- 発注／ブローカ連携プレースホルダ
  - monitoring/
    - __init__.py                    -- 監視・メトリクス関係のプレースホルダ

---

## 今後の拡張ポイント（例）

- 発注レイヤ（kabu ステーション連携）の実装（安全な送信・ACK/約定処理）
- Slack / 通知パイプラインの実装（settings を利用した通知）
- strategy 層（特徴量 → シグナル生成 → ポートフォリオ最適化）
- CI / テストカバレッジ（mock を使った外部 API のユニットテスト）
- 運用ダッシュボード（監視、品質チェック結果の可視化）

---

## ライセンス / 連絡

この README はリポジトリ内のコードを基に作成しています。実運用に移す際は各 API の利用規約やセキュリティ要件に従ってください。質問や改善提案があればソース管理システムの Issue を作成してください。

--- 

README の内容や各モジュールの使い方をプロジェクトの実情に合わせてカスタマイズしたい場合は、知りたい箇所（例: 特定の API 呼び出し例、.env の完全なテンプレート、デプロイ手順 等）を教えてください。