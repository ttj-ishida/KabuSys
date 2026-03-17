# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ／モジュール群です。  
データ取得（J-Quants）、ETL パイプライン、データ品質チェック、ニュース収集、DuckDB スキーマ定義、監査ログ（発注→約定のトレーサビリティ）等の基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）に基づくスロットリング、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution の多層スキーマ定義
  - インデックス定義、冪等性を考慮した DDL
  - `init_schema()` による初期化と既存 DB への接続補助

- ETL パイプライン
  - 差分取得（最終取得日ベース）、バックフィル（後出し修正吸収）
  - 市場カレンダー先読み（lookahead）、品質チェック（欠損・スパイク・重複・日付不整合）
  - 実行結果を持った `ETLResult` の返却

- ニュース収集（RSS）
  - RSS から記事取得・前処理・記事ID生成（正規化URL→SHA-256 一部）
  - SSRF 防止・gzip 限度・XML パースの安全化（defusedxml）
  - raw_news 保存と銘柄コード抽出・紐付け（news_symbols）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを確保するテーブル群
  - 発注要求に冪等キー（order_request_id）を含む設計

- データ品質チェック
  - 欠損（OHLC）、主キー重複、スパイク（前日比閾値）、日付不整合を検出

---

## セットアップ手順

前提:
- Python 3.9+（コードは型注釈や pathlib を使用）
- DuckDB ライブラリ
- defusedxml

1. リポジトリをクローン／配置し、パッケージをインストール
   - 開発環境例（pip / editable install）:
     ```
     pip install -e .
     pip install duckdb defusedxml
     ```
   - 実プロジェクトでは requirements.txt / pyproject.toml を参照してください。

2. 環境変数の設定
   - 環境変数は OS 環境変数、`.env.local`、`.env` の順で読み込まれます（OS > .env.local > .env）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で利用）。

   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD：kabuステーション API 用パスワード
   - SLACK_BOT_TOKEN：Slack 通知用トークン
   - SLACK_CHANNEL_ID：通知先のチャンネル ID

   任意（デフォルトあり）:
   - KABUSYS_ENV：`development` / `paper_trading` / `live`（デフォルト: development）
   - LOG_LEVEL：`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（デフォルト: INFO）
   - DUCKDB_PATH：DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
   - SQLITE_PATH：監視用 SQLite パス（デフォルト: `data/monitoring.db`）
   
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトで初期化します。
     ```python
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # ファイルを作成して全テーブル作成
     ```
   - 監査ログを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn)
     ```

---

## 使い方（主要な利用例）

- 設定値取得
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- J-Quants トークン取得・API 呼び出し
  ```python
  from kabusys.data import jquants_client as jq

  id_token = jq.get_id_token()  # settings.jquants_refresh_token を使って idToken を取得
  quotes = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

  - save 関数で DuckDB に保存:
    ```python
    saved = jq.save_daily_quotes(conn, quotes)
    ```

- ETL の実行（日次）
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # 今日の ETL を実行
  print(result.to_dict())
  ```

  オプション:
  - `run_daily_etl(conn, target_date=..., run_quality_checks=True, backfill_days=3, calendar_lookahead_days=90)`

- ニュース収集ジョブ
  ```python
  from kabusys.data.news_collector import run_news_collection
  # known_codes に有効な銘柄コードセットを渡すと紐付けを行う
  stats = run_news_collection(conn, known_codes={"7203","6758"})
  print(stats)  # {source_name: new_saved_count, ...}
  ```

- 品質チェック単体実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

- 監査ログ（発注 → 約定）初期化
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn)
  ```

---

## 設計上のポイント（簡潔）

- 冪等性: DB への保存は ON CONFLICT を利用し重複を上書き／排除する実装が多く含まれます。
- セキュリティ:
  - RSS パーシングに defusedxml を使用し XML Bomb を回避。
  - ニュース収集では URL 正規化・トラッキングパラメータ除去・SSRF 対策（スキーム検査、プライベート IP チェック、リダイレクト検査）を実装。
- ネットワーク耐性: J-Quants クライアントはリトライ（408/429/5xx）と指数バックオフ、429 の Retry-After サポートを実装。
- 監査: 発注要求に冪等キー（order_request_id）を持たせ、全フローのトレーサビリティを保証するテーブルを提供。

---

## ディレクトリ構成

リポジトリ内の主なファイル／ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得 / 保存）
    - news_collector.py      — RSS ニュース取得・保存・銘柄抽出
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義／初期化（init_schema, get_connection）
    - audit.py               — 監査ログ（signal, order_request, executions の DDL / 初期化）
    - quality.py             — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py            — 戦略層（拡張用）
  - execution/
    - __init__.py            — 発注・ブローカー連携（拡張用）
  - monitoring/
    - __init__.py            — モニタリング関連（拡張用）

---

## 補足／運用ヒント

- テストや CI 環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると `.env` 自動ロードを抑制できます。
- DuckDB のパスはデフォルト `data/kabusys.duckdb`。複数環境（dev/paper/live）で分けることを推奨します。
- `KABUSYS_ENV` によって運用モードを明示できます（例: paper_trading で実運用前の試験）。
- ETL の `backfill_days` を小さくすると API コール回数を抑制できますが、後出し修正の吸収幅が狭くなります。
- ニュースの銘柄抽出は単純な 4 桁数字マッチ（known_codes でフィルタ）です。精度向上は独自ロジック追加を推奨します。

---

必要があれば、インストール手順の詳細（pyproject.toml / requirements.txt の例）、より具体的なスニペット集、CI 用の DB 初期化スクリプトなどの README への追加を作成します。どの部分を詳細化したいか教えてください。