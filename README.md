# KabuSys

日本株自動売買システムのコアライブラリ（ライブラリ層・データ基盤・ETL・監査ログ等）

## プロジェクト概要

KabuSys は日本株の自動売買基盤向けに設計された Python モジュール群です。J-Quants API から市場データや財務情報、JPX カレンダーを取得して DuckDB に蓄積し、データ品質チェック、ニュース収集、監査ログ（トレーサビリティ）などを提供します。将来的には戦略／発注（execution）や監視（monitoring）との統合を想定しています。

主な設計方針
- API レート制御・リトライ・トークン自動リフレッシュを備えた堅牢なデータ取得
- DuckDB を用いた冪等なデータ保存（ON CONFLICT / トランザクション）
- News RSS の安全な取得（SSRF対策やXML脆弱性対策）
- データ品質チェックで ETL 品質を可視化
- 監査ログでシグナル→約定までの完全なトレーサビリティ

## 機能一覧

- 環境設定の自動読み込み（.env / .env.local / OS 環境変数）
- J-Quants クライアント
  - 日足（OHLCV）取得（ページネーション対応、fetched_at 記録）
  - 財務（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミット / リトライ / トークンリフレッシュ対応
- DuckDB スキーマ定義・初期化（raw / processed / feature / execution 層）
- ETL パイプライン（差分更新、バックフィル、品質チェック）
- ニュース収集（RSS → raw_news、URL 正規化、SSRF/サイズ制限、銘柄抽出）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal_events / order_requests / executions テーブル等）
- カレンダー管理ユーティリティ（営業日判定、next/prev_trading_day 等）

## 必要条件

- Python 3.10 以上（PEP 604 の `|` 型ヒント等を使用）
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してください）

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール

   最低限は duckdb と defusedxml が必要です。プロジェクトに requirements / pyproject があればそれを使ってください。

   ```
   pip install duckdb defusedxml
   # またはプロジェクトの依存を一括インストール
   # pip install -e .
   ```

4. 環境変数を設定

   ルートに `.env` を置くと自動的に読み込まれます（.env.local もサポート）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（必須）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN : Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID : 通知先の Slack チャンネル ID（必須）

   推奨 / 既定値あり
   - KABUSYS_ENV : development / paper_trading / live（既定: development）
   - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
   - KABU_API_BASE_URL : kabu API のベース URL（既定: http://localhost:18080/kabusapi）
   - DUCKDB_PATH : DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite パス（既定: data/monitoring.db）

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 使い方（基本的な例）

以下は代表的な利用例です。実行は Python スクリプトや CLI から行えます。

- DuckDB スキーマ初期化

  ```python
  from kabusys.data import schema

  # ファイル DB を初期化
  conn = schema.init_schema("data/kabusys.duckdb")
  # またはインメモリ
  # conn = schema.init_schema(":memory:")
  ```

- 監査ログ DB を初期化（別ファイルで運用したい場合）

  ```python
  from kabusys.data import audit

  audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー、株価、財務の差分取得 + 品質チェック）

  ```python
  from kabusys.data import schema, pipeline
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema している前提
  result = pipeline.run_daily_etl(conn)  # target_date を渡さなければ今日
  print(result.to_dict())
  ```

- 単体ジョブ（株価のみ、バックフィル指定など）

  ```python
  from kabusys.data import pipeline
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today(), backfill_days=5)
  print(f"fetched={fetched}, saved={saved}")
  ```

- RSS ニュース収集ジョブ

  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes があれば銘柄抽出に利用（例: 既知銘柄リスト）
  known_codes = {"7203", "6758", "9432"}  # 例
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存数}
  ```

- J-Quants トークン取得（内部では自動使用されるが直接呼べる）

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
  ```

## 設定 / ロギング

- 設定は環境変数経由で Settings クラス（kabusys.config.settings）から取得します。
- LOG_LEVEL 環境変数でログレベルを制御できます。
- 自動 .env 読み込みはルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読みます。テスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

## 推奨ワークフロー（日次バッチの例）

1. スキーマ初期化（初回）
2. cron / scheduler で毎晩 run_daily_etl を実行
3. 異常検出時は Slack 通知（Slack トークンを設定済みの場合）などを行う（通知機能は別モジュールで実装を想定）
4. 発注・監視は execution / monitoring モジュールで扱う（本リポジトリではモジュールの骨格が存在）

## ディレクトリ構成

リポジトリ（主要ファイル）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py       — J-Quants API クライアント（取得・保存）
      - news_collector.py       — RSS ニュース収集・保存・銘柄抽出
      - schema.py               — DuckDB スキーマ定義・初期化
      - pipeline.py             — ETL パイプライン（差分更新・品質チェック）
      - calendar_management.py  — マーケットカレンダー管理ユーティリティ
      - audit.py                — 監査ログ用スキーマと初期化
      - quality.py              — データ品質チェック
    - strategy/
      - __init__.py             — 戦略モジュールの名前空間（拡張想定）
    - execution/
      - __init__.py             — 発注／約定モジュールの名前空間（拡張想定）
    - monitoring/
      - __init__.py             — 監視モジュール（拡張想定）

各ファイルの詳細はソースコード内の docstring に記載されています。

## 注意点 / 実運用上のヒント

- J-Quants のレート制限（120 req/min）を守るため RateLimiter を内蔵していますが、運用側でも連続呼び出しの設計には注意してください。
- DuckDB のファイルは NFS や複数プロセス同時書き込みのシナリオで注意が必要です（排他やバックアップ方針を検討してください）。
- news_collector は外部 URL を取得するため SSRF 対策・受信サイズ制限・XML 脆弱性対策を実装していますが、さらに厳密な環境（プロキシやネットワーク制限）がある場合は適宜調整してください。
- audit.init_audit_schema はデフォルトで UTC タイムゾーンを設定します。全ての TIMESTAMP は UTC を想定しています。

---

追加の説明や CLI / systemd / scheduler 用のサンプル構成（cron / Airflow / Prefect など）や、既存 DB から known_codes を取得する方法、Slack 通知の実装例などのドキュメントが必要であれば、用途に合わせて追記します。どの部分を詳しく書き足しましょうか？