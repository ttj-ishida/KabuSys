# KabuSys

日本株自動売買基盤（ライブラリ） — データ取得、ETL、ニュース収集、マーケットカレンダー・監査ログ、実行/戦略レイヤの基礎機能を提供します。

本リポジトリは主に下記を目的としたモジュール群で構成されています：
- J-Quants からの市場データ（株価・財務・カレンダー）取得と DuckDB への保存
- RSS ベースのニュース収集と銘柄紐付け
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- マーケットカレンダー管理（営業日判定・更新ジョブ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマ定義

バージョン: 0.1.0

---

## 主な機能

- データ取得（kabu/sys/data/jquants_client.py）
  - 日次株価（OHLCV）、四半期財務、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）対応・指数バックオフによるリトライ・401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）の UTC 記録、DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（kabusys/data/news_collector.py）
  - RSS フィード取得、テキスト前処理、記事ID の冪等生成（URL 正規化→SHA256）
  - SSRF 対策、gzip サイズチェック、defusedxml による安全な XML パース
  - raw_news / news_symbols への冪等保存（トランザクション・チャンク挿入）

- ETL パイプライン（kabusys/data/pipeline.py）
  - 差分更新・バックフィル（既存データの数日前から再取得）・カレンダー先読み
  - 品質チェック連携（欠損、スパイク、重複、日付不整合）
  - 日次 ETL の統合実行（run_daily_etl）

- マーケットカレンダー管理（kabusys/data/calendar_management.py）
  - market_calendar の差分更新ジョブと営業日判定ユーティリティ（next/prev/is_trading_day 等）
  - DB が未取得の部分は曜日ベースでフォールバック

- データ品質チェック（kabusys/data/quality.py）
  - 欠損データ、スパイク検出（前日比）、重複、日付不整合の検出と QualityIssue レポート

- スキーマ初期化・監査ログ（kabusys/data/schema.py / audit.py）
  - DuckDB の全層スキーマ定義（Raw / Processed / Feature / Execution）
  - 監査テーブル（signal_events / order_requests / executions）初期化関数

---

## セットアップ

前提
- Python 3.9+（型注釈に | などを使用）
- Git（継続的な開発・.git によるルート検出が有用）

依存パッケージ（主なもの）
- duckdb
- defusedxml

インストール例（仮に pyproject.toml / pip を利用する場合）:

1. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. パッケージと依存をインストール
   - pyproject / setup が用意されている場合:
     ```
     pip install -e .
     ```
   - あるいは最小限の依存を手動インストール:
     ```
     pip install duckdb defusedxml
     ```

環境変数（必須・推奨）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用
- SLACK_CHANNEL_ID (必須) — Slack チャンネルID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — 値: development / paper_trading / live （デフォルト development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を基に自動で `.env` および `.env.local` を読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - OS 環境変数は保護され、.env によって上書きされません（.env.local は上書き可能）。
- 自動読み込みを無効化するには環境変数を設定:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

注意: .env.example を用意してある想定のため、これを参考に `.env` を作成してください（JQUANTS_REFRESH_TOKEN などを設定）。

---

## 使い方（簡単な例）

- DuckDB スキーマ初期化
  Python 簡易スクリプトから:
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（run_daily_etl）
  ```python
  from kabusys.data import pipeline, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # あるいは init_schema
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())
  ```

- RSS ニュース収集と保存
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # 既知銘柄コードセットを渡して銘柄紐付けする例
  known_codes = {"7203", "6758", "9432"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: saved_count, ...}
  ```

- カレンダー更新ジョブ（夜間バッチ向け）
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved={saved}")
  ```

- 監査ログスキーマを追加で初期化
  ```python
  from kabusys.data import audit, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  audit.init_audit_schema(conn)
  ```

- J-Quants API 直接呼び出し例（トークン取得）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
  ```

ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## よくある操作／注意点

- 差分取得・バックフィル
  - pipeline.run_prices_etl / run_financials_etl は DB の最終取得日を参照し、自動で差分を決定します。backfill_days（デフォルト 3）で直近数日の再取得を行い、API の後出し修正を吸収します。

- Idempotency（冪等性）
  - DuckDB への挿入は ON CONFLICT DO UPDATE / DO NOTHING を利用して重複や再実行に安全です。

- ニュース記事 ID
  - 記事 ID は URL 正規化（トラッキングパラメータ除去）したものの SHA-256（先頭32文字）を用いて冪等性を確保します。

- セキュリティ対策
  - news_collector は SSRF 対策（ホストのプライベートチェック、リダイレクト検査）、defusedxml を使用した安全な XML パース、レスポンスサイズの上限チェックを行っています。

- 自動 .env 読み込みの挙動
  - プロジェクトルートを見つけられない場合や KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると自動読み込みはスキップされます（ユニットテスト等で便利）。

---

## ディレクトリ構成

リポジトリ内の主なファイル／ディレクトリ（src 以下を抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py              — RSS ニュース収集・保存
    - schema.py                      — DuckDB スキーマ定義・初期化
    - pipeline.py                    — ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py         — マーケットカレンダー管理（営業日ロジック）
    - audit.py                       — 監査ログスキーマ（signal/order/execution）
    - quality.py                     — データ品質チェック
  - strategy/
    - __init__.py                    — 戦略層用エントリ（未詳細実装）
  - execution/
    - __init__.py                    — 実行（発注）層用エントリ（未詳細実装）
  - monitoring/
    - __init__.py                    — 監視／アラート層（未詳細実装）

---

## 開発・デバッグのヒント

- unit test 用に .env 自動ロードを無効化:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- news_collector._urlopen はテストで差し替え（モック）可能に設計されています。
- jquants_client の rate limiter とトークンキャッシュはモジュールレベルなので、テスト用に状態リセットが必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD 等と組み合わせて工夫してください。

---

## 連絡／貢献

- バグ・提案は issue を立ててください。
- コードスタイルは型注釈・ドキュメンテーション文字列を重視しています。PR ではテスト追加・説明追記を歓迎します。

---

この README は現行コード（src/kabusys 以下）に基づいて作成しています。実運用時は .env.example の作成、依存関係の明示（requirements.txt / pyproject.toml への記載）、および展開用スクリプトの整備を推奨します。