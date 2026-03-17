# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ群）。  
データ取得・ETL・品質チェック・ニュース収集・監査ログ等の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は、J-Quants 等の外部データソースから日本株のデータを取得し、DuckDB に保存・整備することで、自動売買アルゴリズム（strategy）や発注実行（execution）モジュールにデータを供給することを目的とした基盤ライブラリです。

主な設計方針:
- API レート制限・リトライ・トークン自動更新対応
- 取得データの冪等保存（ON CONFLICT ...）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集での SSRF/ZIP/サイズ攻撃対策
- 監査ログ（signal → order → execution のトレース）

---

## 機能一覧

- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日足（OHLCV）、財務データ、マーケットカレンダーの取得
  - 固定間隔のレート制御、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - ページネーション対応
  - DuckDB への冪等保存ユーティリティ（save_*）

- DuckDB スキーマ定義・初期化（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス・外部キー設定
  - 初期化ユーティリティ `init_schema` / `get_connection`

- ETL パイプライン（`kabusys.data.pipeline`）
  - 差分更新（最終取得日から未取得分を取得）
  - バックフィル（後出し修正の吸収）
  - 市場カレンダー、価格、財務の一括 ETL（`run_daily_etl`）

- マーケットカレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定、前後営業日取得、レンジ内営業日の取得
  - 夜間バッチ更新ジョブ `calendar_update_job`

- ニュース収集（`kabusys.data.news_collector`）
  - RSS フィード取得、前処理（URL 除去・空白正規化）
  - トラッキングパラメータ除去・URL 正規化・記事 ID 生成（SHA-256）
  - SSRF / gzip bomb / XML 攻撃対策
  - DuckDB への冪等保存（`save_raw_news`, `save_news_symbols`）
  - テキストから銘柄コード抽出（4桁コード、`extract_stock_codes`）

- データ品質チェック（`kabusys.data.quality`）
  - 欠損、スパイク（前日比）、重複、日付不整合の検出
  - 問題は QualityIssue オブジェクトとして収集（エラー/警告区別）
  - `run_all_checks` による一括実行

- 監査ログ（`kabusys.data.audit`）
  - signal / order_request / executions の監査テーブル
  - 発注の冪等性（order_request_id）やトレーサビリティ保存
  - `init_audit_schema` / `init_audit_db`

- 設定管理（`kabusys.config`）
  - .env 自動ロード（プロジェクトルート基準）と環境変数読み取りラッパ
  - 必須パラメータの取得、環境種別（development/paper_trading/live）管理

---

## 必要条件（推奨）

- Python 3.10 以上（typing の | 演算子を使用）
- パッケージ:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）

インストール例:
- 仮想環境作成・有効化（例）
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

- 必要パッケージのインストール:
  - pip install duckdb defusedxml

（プロジェクトに requirements ファイルがあればそれに従ってください）

---

## 環境変数

KabuSys は .env（プロジェクトルート）から自動で環境変数を読み込みます（無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

必須環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意/デフォルト:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等に使用（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（"1" 等）

.env.example を参考に .env を作成してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（任意）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
4. プロジェクトルートに `.env` を作成し必須環境変数を設定
5. DuckDB スキーマを初期化（下記参照）

---

## 使い方（コード例）

以下は簡単な実行例です。スクリプトにして運用バッチや Airflow 等から呼び出す想定です。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.init_schema(settings.duckdb_path)
  ```

- 日次 ETL を実行（市場カレンダー・価格・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.data import schema
  from kabusys.config import settings

  conn = schema.get_connection(settings.duckdb_path)  # すでに init_schema 済みの場合
  result = run_daily_etl(conn)  # target_date 等は省略可（デフォルトは today）
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes を用意（抽出で有効な銘柄の集合）
  known_codes = {"7203", "6758"}  # 例: 手元の銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"saved calendar rows: {saved}")
  ```

- 監査ログ用スキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_schema
  from kabusys.data import schema

  conn = schema.get_connection("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

注意:
- J-Quants API は 120 req/min のレート制限を守る必要があります。クライアントは固定間隔でスロットリングを行いますが、運用側でも過剰な並列化を避けてください。
- ETL 実行時はログ（LOG_LEVEL）を適切に設定してモニタリングしてください。

---

## ディレクトリ構成

主要ファイル／モジュール（省略可能なファイル群は割愛）:

- src/
  - kabusys/
    - __init__.py             (パッケージ初期化 / バージョン管理)
    - config.py               (環境変数・設定管理)
    - data/
      - __init__.py
      - jquants_client.py     (J-Quants API クライアント)
      - news_collector.py     (RSS ニュース収集)
      - schema.py             (DuckDB スキーマ定義・初期化)
      - pipeline.py           (ETL パイプライン)
      - calendar_management.py (マーケットカレンダー管理)
      - audit.py              (監査ログ初期化・DDL)
      - quality.py            (データ品質チェック)
    - strategy/
      - __init__.py           (戦略モジュール用プレースホルダ)
    - execution/
      - __init__.py           (発注実行モジュール用プレースホルダ)
    - monitoring/
      - __init__.py           (監視関連用プレースホルダ)

上記のモジュールはそれぞれ責務ごとに分割されています。strategy / execution / monitoring は本コードベースでは空のパッケージ置き場として用意されています。

---

## 運用上の注意 / 実装上のポイント

- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行います。テスト等で無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ニュース収集は外部 URL を扱うため、SSRF 対策やレスポンスサイズ上限（10MB）などの安全策が組み込まれていますが、運用時はクロール先リストの管理に注意してください。
- DuckDB のファイルはデフォルトで `data/kabusys.duckdb` に保存されます。運用環境では永続化とバックアップを検討してください。
- 監査テーブルは削除しない設計を想定しています（FK は ON DELETE RESTRICT）。監査データの保管ポリシーを決めておくことを推奨します。

---

## 開発・貢献

- 新しいデータソースの追加、戦略・実行APIの接続実装、モニタリング/アラート機能の追加などを歓迎します。PR 時はユニットテストと動作確認手順を添えてください。

---

README は以上です。運用スクリプトや CI/CD、外部サービス連携（kabuステーションの発注 API など）を追加することで、実際の自動売買システムへと拡張できます。必要であれば、運用用の例スクリプトや systemd / cron の設定例も作成します。どの内容を優先して欲しいか教えてください。