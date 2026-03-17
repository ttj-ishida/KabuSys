# KabuSys

日本株自動売買プラットフォームのコアライブラリ（プロトタイプ実装）。  
J-Quants、kabuステーション、RSS フィードなどからデータを取得・保存し、ETL・品質チェック・監査ログ・ニュース収集などの基盤機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対応のスロットリング
  - 冪等保存（DuckDB への INSERT ... ON CONFLICT）
  - リトライ（指数バックオフ、401 の自動トークンリフレッシュ対応）
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を低減

- ETL（差分更新）パイプライン
  - 市場カレンダー先読み、株価・財務データの差分取得と保存
  - バックフィル機能で API の後出し修正に対応
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - テーブル作成、インデックス作成、監査テーブルの初期化ユーティリティ

- ニュース収集
  - RSS フィードから記事収集（URL 正規化、トラッキングパラメータ除去）
  - SSRF 対策・サイズ上限・gzip 対応
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性保証
  - raw_news / news_symbols への安全な一括保存

- マーケットカレンダー管理
  - 営業日判定（DBデータ優先、未登録は曜日フォールバック）
  - next/prev_trading_day などの補助関数
  - 夜間バッチ更新ジョブ

- 監査ログ（Audit）
  - signal_events / order_requests / executions で発注〜約定までをトレース
  - UUID ベースの冪等キーとタイムスタンプ（UTC）

---

## 必要環境 / 依存

- Python 3.10+
- 主要依存（例）
  - duckdb
  - defusedxml
- （任意）kabuステーション連携や Slack 通知などはそれぞれのクレデンシャルが必要

インストール例:
```bash
pip install duckdb defusedxml
# または開発中はパッケージを編集可能インストール
pip install -e .
```

---

## 環境変数 / 設定

本パッケージは環境変数から設定を読み込みます（`kabusys.config.settings` 経由）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作環境: `development` | `paper_trading` | `live`（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

自動で .env ファイルを読み込む挙動:
- 読み込み順: OS 環境変数 > .env.local > .env
- プロジェクトルートは `.git` または `pyproject.toml` の所在から自動検出
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンして依存をインストール
   ```bash
   git clone <this-repo>
   cd <this-repo>
   pip install -e .
   pip install duckdb defusedxml
   ```

2. 環境変数を用意（.env または OS 環境）
   - 上記の必須キーをセットしてください。

3. DuckDB スキーマの初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```
   - `":memory:"` を渡すとインメモリ DB が利用可能です。
   - 親ディレクトリが存在しない場合は自動で作成されます。

4. 監査ログ用スキーマ（必要に応じて）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)  # conn は init_schema の戻り値
   ```

---

## 使い方（主な API 例）

- 設定（設定値の参照）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.env, settings.log_level)
  ```

- Schema 初期化（再掲）
  ```python
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定することも可
  print(result.to_dict())
  ```

- 個別 ETL ジョブの実行
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes は銘柄コードの集合（例: DB から読み取る）
  known_codes = {"7203", "6758", "9984"}
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存数}
  ```

- J-Quants トークン取得（通常は内部で管理される）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用
  ```

- カレンダー判定ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")
  print(is_trading_day(conn, date.today()))
  ```

---

## 運用上の注意 / セキュリティ

- J-Quants のリフレッシュトークンや kabu API のパスワードは厳重に管理してください（.env をリポジトリに含めない、アクセス権制限など）。
- ニュース収集モジュールには SSRF 対策、XML パース保護、レスポンスサイズ上限などの防御が組み込まれていますが、運用環境のセキュリティポリシーに従ってください。
- ETL や発注処理を本番（live）で動かす場合は、まず paper_trading モードで十分に検証してください（KABUSYS_ENV=paper_trading）。
- J-Quants API のレート制御（120 req/min）を厳守していますが、外部バッチや複数インスタンスを起動する場合は全体の呼び出し量に注意してください。

---

## ディレクトリ構成

リポジトリ内の主要なファイル・モジュール（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py     -- RSS ニュース収集・保存
    - schema.py             -- DuckDB スキーマ定義・初期化
    - pipeline.py           -- ETL パイプライン（差分更新・品質チェック含む）
    - calendar_management.py-- 市場カレンダー管理・ユーティリティ
    - audit.py              -- 監査ログ（order/signals/executions）
    - quality.py            -- 品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

補足:
- パッケージは src 配下に構成されているため、開発時は `pip install -e .` を推奨します。
- 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、トランザクションの開始/終了は各関数の仕様に従います（例：save_raw_news は内部でトランザクションを管理）。

---

## 開発 / テストメモ

- テストを行う際は環境変数の自動ロードを無効化できます:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- J-Quants の実 API 呼び出しを避けたい場合は、`get_id_token` や `jquants_client._urlopen` 等をモックしてください（news_collector では `_urlopen` を差し替えてテストしやすく設計されています）。

---

必要であれば、README にサンプル .env.example、Docker/Compose の起動例、CI 設定例、または各モジュールごとの詳細ドキュメント（API 仕様・SQL スキーマの説明）を追加します。どの追加情報が必要か教えてください。