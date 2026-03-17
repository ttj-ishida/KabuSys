# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
J-Quants / RSS 等から市場データ・ニュースを収集し、DuckDB に保存して ETL・品質チェック・監査ログを行うためのモジュール群を提供します。将来的に戦略（strategy）・発注（execution）・モニタリング（monitoring）を統合する設計になっています。

## 特徴（概要）
- J-Quants API クライアント
  - 株価（日足 OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）とリトライ（指数バックオフ、401 時の自動トークンリフレッシュ）に対応
  - 取得時刻（fetched_at）を記録して Look-ahead bias を防止
- DuckDB ベースのデータスキーマ
  - Raw / Processed / Feature / Execution 層を想定したスキーマ定義（冪等性のある INSERT 処理）
  - 監査ログ（signal / order_request / execution）の専用スキーマも含む
- ETL パイプライン
  - 差分更新・バックフィル対応（バックフィル日数で API 後出しを吸収）
  - 品質チェック（欠損、スパイク、重複、日付不整合）を実行
- ニュース収集（RSS）
  - RSS フィード収集 → 前処理（URL除去・空白正規化） → DuckDB 保存（冪等）
  - SSRF・XML 爆弾対策（defusedxml、ホスト/リダイレクト検査、最大受信サイズ制限）
  - 記事ID は正規化 URL の SHA-256 に基づく冪等キー
- カレンダー管理
  - JPX カレンダーを差分更新し、営業日判定 / next/prev_trading_day / get_trading_days 等を提供

## 主な機能一覧
- kabusys.config: 環境変数管理（.env/.env.local の自動ロード、必須変数検査）
- kabusys.data.jquants_client: J-Quants API クライアント（fetch_* / save_*）
- kabusys.data.news_collector: RSS 収集・正規化・DuckDB 保存 / 銘柄抽出
- kabusys.data.schema: DuckDB スキーマ定義と初期化（init_schema）
- kabusys.data.pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL
- kabusys.data.calendar_management: 市場カレンダーの更新・営業日ロジック
- kabusys.data.audit: 監査ログ用スキーマの初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality: データ品質チェック（missing / spike / duplicates / date consistency）
- strategy / execution / monitoring 用のプレースホルダモジュール

## 前提
- Python 3.10 以上（型注釈に `X | Y` を使用しているため）
- 必要なライブラリ（最低限）:
  - duckdb
  - defusedxml

実際のプロジェクトでは追加で Slack SDK や HTTP クライアント、テストライブラリ等を使う場合があります。

## セットアップ手順

1. リポジトリをクローン／取得
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - まず最低限:
     ```
     pip install duckdb defusedxml
     ```
   - プロジェクトで requirements.txt / pyproject.toml があればそちらからインストールしてください:
     ```
     pip install -r requirements.txt
     # または
     pip install -e .
     ```

4. 環境変数の設定
   - ルートに `.env` または `.env.local` を置くと自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。
   - 必須環境変数（Settings クラス参照）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu API（kabuステーション）パスワード
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack 投稿先チャンネル ID
   - 任意／デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動ロードを無効化
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 使い方（簡単な例）

- DuckDB スキーマを初期化する:
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")  # ディレクトリを自動作成
  ```

- 日次 ETL を実行する（最小例）:
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する:
  ```python
  from kabusys.data.schema import get_connection, init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # 既定ソース（DEFAULT_RSS_SOURCES）で収集
  res = run_news_collection(conn)
  print(res)  # {source_name: saved_count}
  ```

- J-Quants から株価を直接取得する:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  quotes = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 監査ログスキーマを初期化する（audit 用 DB を別に作る場合）:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 環境設定の参照:
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  print(settings.env, settings.is_live)
  ```

## 推奨ワークフロー（運用例）
1. nightly cron や CI で:
   - DuckDB スキーマ初期化（初回のみ）
   - run_daily_etl を実行して市場データ／財務データ／カレンダーを更新
   - run_news_collection を実行してニュースを収集・銘柄紐付け
2. 品質チェック結果を Slack に通知（Slack 投稿は別モジュールで実装）
3. strategy モジュールでシグナル生成 → execution モジュールで発注 → audit テーブルへ保存
4. monitoring モジュールで稼働状況とパフォーマンスを監視

## 主要 API（要点）
- data.schema
  - init_schema(db_path) -> DuckDB 接続（テーブル作成）
  - get_connection(db_path) -> 既存 DB への接続
- data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- data.quality
  - run_all_checks(conn, target_date=None, reference_date=None, spike_threshold=...)

## ディレクトリ構成
（主要ファイルを抜粋）
```
src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      schema.py
      pipeline.py
      calendar_management.py
      audit.py
      quality.py
    strategy/
      __init__.py
      (戦略実装ファイルを配置)
    execution/
      __init__.py
      (発注関連実装を配置)
    monitoring/
      __init__.py
      (監視関連を配置)
```

## 注意点 / 実運用上のポイント
- J-Quants のレート制限（120 req/min）に注意。jquants_client は固定間隔レートリミッタを実装していますが、並列実行や複数プロセスでの同時リクエストに注意してください。
- 環境変数は .env/.env.local から自動ロードされますが、CI やテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境を注入してください。
- DuckDB のトランザクションと DDL 実行の性質に留意してください（audit.init_audit_schema は transactional オプションあり）。
- ニュース収集は外部 RSS を読み込むため、ネットワーク・セキュリティ（SSRF）対策が組み込まれていますが、社内環境での接続制限やプロキシ設定が必要な場合は適宜ラッパーを作ってください。
- 本ライブラリは戦略ロジックや実際の発注コネクタ（証券会社 API）を含みません。execution 層に接続する際は、二重発注や冪等性（order_request_id など）を必ず考慮してください。

---

ご要望があれば、README に以下を追加できます：
- requirements.txt / pyproject.toml に合わせたインストール手順
- よく使う CLI のサンプルスクリプト
- 実運用チェックリスト（デプロイ、監査、バックアップ等）
- 各モジュールの詳細な API リファレンス（関数一覧と引数説明）