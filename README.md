# KabuSys

KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
J-Quants や kabuステーション 等の外部 API と連携してデータ取得・ETL・品質チェック・ニュース収集・監査ログなどを提供します。  
このリポジトリは主にデータ基盤（Data Platform）周りの実装に重点を置いています。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API から株価（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを安全に取得する
- 取得データを DuckDB に冪等（idempotent）に保存する（ON CONFLICT / DO UPDATE）
- 日次 ETL パイプラインの提供（差分取得、バックフィル、品質チェック）
- RSS フィードからニュースを安全に収集し DB に保存、銘柄コードの紐付け
- カレンダー管理、営業日判定、監査ログテーブルの初期化など運用に必要なユーティリティ

設計上のポイント：

- API レート制御（J-Quants: 120 req/min）とリトライ（指数バックオフ、401 時のトークン自動リフレッシュ）を内蔵
- Look-ahead Bias 対策として fetched_at を UTC で記録
- ニュース収集は SSRF / XML Bomb / メモリ DoS 等に配慮した実装
- データ品質チェック（欠損、スパイク、重複、日付不整合）を提供

---

## 機能一覧

- データ取得（kabusys.data.jquants_client）
  - 日次株価（OHLCV）、財務データ、マーケットカレンダーのページネーション対応取得
  - レートリミット、リトライ、トークン自動リフレッシュをサポート
  - DuckDB へ idempotent に保存する save_* 関数

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィル対応

- スキーマ管理（kabusys.data.schema）
  - DuckDB スキーマの定義と初期化（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、URL 正規化・トラッキング除去、記事ID の作成（SHA-256 先頭32文字）
  - SSRF 対策、読み込みサイズ制限、gzip 解凍、XML パースの安全化（defusedxml）
  - raw_news 保存・news_symbols への紐付け機能

- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後の営業日の検索、期間の営業日リスト取得、夜間カレンダー更新ジョブ

- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付整合性チェック
  - QualityIssue オブジェクトで結果を返す

- 監査ログ（kabusys.data.audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティ用テーブルと初期化ユーティリティ

---

## セットアップ手順

前提：

- Python 3.10 以上（PEP 604 の union 型表記を使用）
- DuckDB と defusedxml 等の依存ライブラリ

1. リポジトリをクローン／チェックアウト

   ```
   git clone <this-repo-url>
   cd <this-repo>
   ```

2. 仮想環境を作成して有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   （このリポジトリに requirements ファイルがある想定です。ない場合は主要依存を手動でインストール）

   例:
   ```
   pip install duckdb defusedxml
   # 他に requests 等を使う場合は追加でインストール
   ```

4. パッケージを開発モードでインストール（任意）

   ```
   pip install -e .
   ```

5. 環境変数を設定

   必須環境変数（主なもの）：
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID

   任意／デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると自動 .env ロードを無効化

   デフォルトの DB パス（設定からの参照）：
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

   .env ファイルをプロジェクトルートに置くと自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを探索）。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（簡単な例）

※ 以下は Python REPL やスクリプトで実行する例です。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

# デフォルト: data/kabusys.duckdb にファイルを作成
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())

print(result.to_dict())  # ETL の統計／品質問題などを確認
```

主な引数（run_daily_etl）：
- conn: DuckDB 接続
- target_date: ETL 対象日（省略時は today）
- id_token: テスト等で固定トークンを注入可能
- run_quality_checks: 品質チェックの実行可否（デフォルト True）
- backfill_days: 株価・財務のバックフィル日数（デフォルト 3）
- calendar_lookahead_days: カレンダー先読み（デフォルト 90）

3) ニュース収集を実行

```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# sources を省略するとデフォルトの RSS ソースを使用
# known_codes: 銘柄抽出に使う有効な銘柄コードセット（例: {'7203','6758',...}）
result = run_news_collection(conn, known_codes={"7203", "6758"})
print(result)  # {source_name: saved_count}
```

4) J-Quants の ID トークン取得（直接）

```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
```

5) 監査ログ用スキーマ初期化（監査専用 DB を別途作る場合）

```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/kabusys_audit.duckdb")
```

---

## .env 自動読み込みについて

- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 に設定してください（テスト用途等）。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイル・モジュール構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数管理（J-Quants トークンや DB パス、Slack 設定等）
    - 自動 .env 読み込みロジック
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・リトライ・レート制御・保存関数）
      - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - news_collector.py
      - RSS フィード取得、記事正規化、DuckDB 保存、銘柄抽出
      - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
    - schema.py
      - DuckDB スキーマ定義／初期化（Raw / Processed / Feature / Execution 層）
      - init_schema, get_connection
    - pipeline.py
      - ETL の実装（差分取得・バックフィル・品質チェック）
      - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
    - calendar_management.py
      - 市場カレンダー管理、営業日判定、next/prev_trading_day など
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）テーブルと初期化
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - strategy/
    - __init__.py
    - （戦略モジュールを配置するためのパッケージ）
  - execution/
    - __init__.py
    - （発注／ブローカー連携用モジュールを配置するためのパッケージ）
  - monitoring/
    - __init__.py
    - （監視・メトリクス関連モジュール用パッケージ）

---

## 設計上の注意点 / 運用メモ

- DuckDB の初期化は一度行えばよく、スキーマは冪等に作成されます。
- J-Quants の API 呼び出しはレート制御とリトライを内部でやってくれますが、運用側でも適切なスケジューリングを行ってください。
- ニュース収集では URL のトラッキングパラメータを除去して ID を生成します（同一記事の重複保存を防止）。
- 品質チェックは Fail-Fast ではなく、問題を収集して呼び出し側が判断できるようにしています。ETL 実行結果（ETLResult）で quality_issues を確認してください。
- 環境ごと（development / paper_trading / live）で挙動を切り替えられるため、本番（live）環境では十分な監視と安全弁（最大注文サイズ、リスク制限など）を併用してください。

---

## サポート / 貢献

バグ報告や機能要望は issue を立ててください。プルリクエスト歓迎です。

---

以上です。必要であれば README に含めるサンプルコードや、CI / デプロイ手順、より詳細な環境変数一覧（.env.example の内容）を追加します。どの情報を追加しますか？