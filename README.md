# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants や RSS などから市場データを収集し、DuckDB に格納して ETL・品質チェック・監査（オーダー／約定追跡）を行うためのモジュール群を提供します。

主な目的は「データ取得→保存→品質チェック→特徴量生成→戦略→発注・監査」というワークフローを支援することです。

---

## 機能一覧

- 設定管理
  - .env ファイルまたは環境変数からの設定読み込み（自動ロード、`.env.local` 優先など）
  - 必須項目の取得とバリデーション

- データ取得（J-Quants API クライアント）
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応、リトライ（指数バックオフ）、トークン自動リフレッシュ
  - 取得時刻（fetched_at）を含めた Look-ahead バイアス対策

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - 冪等なテーブル作成（CREATE IF NOT EXISTS）とインデックス作成
  - 初期化ユーティリティ（init_schema / get_connection）

- ETL パイプライン
  - 差分更新（最終取得日を参照して未取得分を取得）
  - バックフィル機能（直近 N 日を再取得して API の後出し修正を吸収）
  - 日次 ETL エントリ（run_daily_etl）：カレンダー→価格→財務→品質チェック

- データ品質チェック
  - 欠損、重複、スパイク（前日比変動）、日付不整合（未来日付／非営業日のデータ）検出
  - QualityIssue オブジェクトで問題を集約（エラー／警告）

- ニュース収集
  - RSS フィードからのニュース記事収集（fetch_rss / run_news_collection）
  - URL 正規化・トラッキングパラメータ除去・記事IDは SHA-256 の先頭 32 文字
  - SSRF 対策、Gzip/サイズ上限、XML パースに defusedxml を使用
  - raw_news, news_symbols への冪等保存

- カレンダー管理
  - JPX カレンダー差分更新ジョブ（calendar_update_job）
  - 営業日判定・前後営業日の取得・期間内営業日リスト取得

- 監査（Audit）
  - signal_events / order_requests / executions などの監査ログ定義
  - 発注の冪等キー（order_request_id）やタイムゾーンの統一（UTC）

---

## 前提・依存関係

- Python 3.10 以上（Union 型表記 Path | None 等を使用）
- 必要なパッケージ（一例）
  - duckdb
  - defusedxml
  - （標準ライブラリ: urllib, json, logging, datetime など）

pip でのインストール例（プロジェクト配布方法により調整してください）:
```
pip install "duckdb" "defusedxml"
# またはプロジェクトの setup/pyproject 経由で依存を管理
```

---

## セットアップ手順

1. リポジトリをクローンして、Python 仮想環境を用意
   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb defusedxml
   ```

2. 環境変数ファイルを作成
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` と/または `.env.local` を設置します。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

   代表的な環境変数（必須とデフォルト）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャネル ID
   - KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
   - DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
   - SQLITE_PATH (任意) — デフォルト: data/monitoring.db
   - KABUSYS_ENV (任意) — 有効値: development / paper_trading / live （デフォルト: development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_pass
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

3. DuckDB スキーマの初期化
   Python シェルやスクリプトで接続・初期化します:
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

4. （必要なら）監査 DB の初期化（別 DB に分けたい場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（主要な API と実行例）

以下は代表的な利用シーンのサンプルコードです。

- J-Quants の ID トークンを取得する:
  ```python
  from kabusys.data.jquants_client import get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集を実行する（RSS → raw_news / news_symbols への保存）:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema(settings.duckdb_path)
  known_codes = {"7203", "6758", "9984"}  # 例: 有効銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: inserted_count}
  ```

- 市場カレンダーの夜間更新ジョブ:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"saved {saved} records")
  ```

- 品質チェックを個別に実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

---

## 設計上のポイント・注意事項

- 自動環境設定読み込み:
  - パッケージロード時に、プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動ロードします。
  - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- API レート制限・リトライ:
  - J-Quants クライアントは 120 req/min を守るための固定間隔レートリミッタを備え、408/429/5xx 系に対して指数バックオフでリトライします。
  - 401 受信時はリフレッシュトークンを使って自動で ID トークンを更新し、1 回だけリトライします。

- DuckDB 保存は可能な限り冪等（ON CONFLICT / DO UPDATE / DO NOTHING）になります。ETL はバックフィルを行い、API 側の後出し修正を吸収する設計です。

- NewsCollector はセキュリティを重視:
  - SSRF 対策（リダイレクトごとの検証、プライベート IP のブロック）
  - defusedxml による XML 脆弱性対策
  - レスポンスサイズ制限と gzip 解凍後の検査

- 時刻は監査テーブルなどで UTC に統一することを前提としています（init_audit_schema では TimeZone を UTC に設定します）。

---

## ディレクトリ構成

プロジェクトの主なファイル / モジュール構成は以下の通りです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py      -- J-Quants API クライアント（取得・保存）
      - news_collector.py      -- RSS ニュース収集と保存
      - schema.py              -- DuckDB スキーマ定義・初期化
      - pipeline.py            -- ETL パイプライン（差分更新・日次 ETL）
      - calendar_management.py -- 市場カレンダー管理（営業日判定等）
      - quality.py             -- データ品質チェック
      - audit.py               -- 監査ログ（order_requests / executions 等）
      - pipeline.py
    - strategy/                 -- 戦略関連モジュール（抽象化）
    - execution/                -- 発注 / 約定管理（抽象化）
    - monitoring/               -- 監視 / モニタリング（空プレースホルダ）

（実装済みのファイルは上記の通り。strategy／execution／monitoring は将来の実装領域です。）

---

## よくある質問 / トラブルシューティング

- Q: .env が読み込まれない
  - A: パッケージは __file__（モジュール位置）を基点にプロジェクトルート（.git または pyproject.toml）を探索します。テストなどで自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Q: J-Quants のリクエストで 401 が返る
  - A: jquants_client はリフレッシュトークンから id_token を自動取得し、401 を受けた場合は 1 回だけトークンを更新してリトライします。リフレッシュトークン自体が無効な場合は `get_id_token()` が例外を投げます。環境変数 JQUANTS_REFRESH_TOKEN を確認してください。

- Q: DuckDB にテーブルが作られない
  - A: init_schema を通して DB を初期化してください。パスの親ディレクトリが無い場合は自動作成されます。":memory:" を指定するとインメモリ DB になります。

---

この README は開発中の実装に基づく概要書です。詳細な設計（DataPlatform.md 等）や API の振る舞いについては、リポジトリ内のドキュメントやソースコードの docstring を参照してください。問題報告や機能要望は issue を作成してください。