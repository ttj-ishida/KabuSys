# KabuSys

日本株自動売買システムのコアライブラリ（軽量プロトタイプ）

本リポジトリは、J-Quants や kabu ステーション等の外部APIから市場データを取得し、DuckDB に保存・整備し、ETL（差分更新・品質チェック）や監査ログの仕組みを提供するためのモジュール群を含みます。実際の発注や戦略は別モジュール（strategy / execution）で実装する想定です。

## 主な機能

- J-Quants API クライアント
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX カレンダー取得
  - API レート制御（120 req/min）とリトライ（指数バックオフ、401 時トークン自動リフレッシュ）
  - 取得時刻（fetched_at）を UTC で記録し look-ahead bias を防止
  - DuckDB へ冪等的（ON CONFLICT DO UPDATE）に保存

- DuckDB スキーマ管理
  - 3 層（Raw / Processed / Feature）＋Execution / Audit 用テーブル群の DDL を定義
  - インデックス生成・外部キー・制約を含む初期化 API（init_schema, init_audit_schema）

- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）＋バックフィル（デフォルト 3 日）による後出し修正吸収
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行して検出結果を収集

- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、主キー重複、将来日付／非営業日データ検出
  - QualityIssue オブジェクトで問題を集約（error / warning）

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを UUID 連鎖で記録
  - 冪等キー（order_request_id）やステータス管理、UTC タイムスタンプ運用

- 設定管理
  - .env（および .env.local）自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - quote や export 形式、コメント処理等に対応する堅牢なパーサー
  - 必須環境変数は Settings により要求（例: JQUANTS_REFRESH_TOKEN 等）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能

## 必要条件（概略）

- Python 3.10+
- パッケージ依存（代表例）
  - duckdb
- ネットワークアクセス（J-Quants API 等）
- J-Quants / kabu ステーション / Slack の各種認証情報

（実プロジェクトでは pyproject.toml / requirements.txt を用意してください）

## セットアップ手順（開発用 / ローカル）

1. リポジトリをクローンしてワークディレクトリへ移動

2. 仮想環境を作成して有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb

   （実プロジェクトでは `pip install -e .` 等を用意してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数で設定します。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン
     - SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID
   - オプション（デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL （デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - 自動 .env 読み込みを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   .env パーサの注意点:
   - export KEY=val 形式を許容
   - シングル/ダブルクォート内でのバックスラッシュエスケープに対応
   - クォートなしの場合はスペース/タブの直前にある # をコメントとして扱う

## 使い方（サンプル）

Python スクリプトや REPL から主要機能を呼び出す例を示します。

- DuckDB スキーマを初期化する
  - from kabusys.data import schema
  - conn = schema.init_schema(settings.duckdb_path)  # :memory: でも可

- 監査ログスキーマを追加する
  - from kabusys.data import audit
  - audit.init_audit_schema(conn)

- 日次 ETL を実行する
  - from kabusys.data import pipeline
  - result = pipeline.run_daily_etl(conn)  # target_date を指定可能
  - print(result.to_dict())

- J-Quants の手動トークン取得
  - from kabusys.data import jquants_client as jq
  - id_token = jq.get_id_token()  # settings.jquants_refresh_token を使用

- ETL の個別ジョブ
  - pipeline.run_prices_etl(conn, target_date)
  - pipeline.run_financials_etl(conn, target_date)
  - pipeline.run_calendar_etl(conn, target_date)

注意点:
- J-Quants クライアントは内部で 120 req/min のレートを守る設計です。大量取得する場合は時間を考慮してください。
- API エラー時は自動リトライ（最大 3 回）や 401 時の自動リフレッシュなどを行いますが、API の利用規約やレート制限を遵守してください。

## API の挙動（設計メモ）

- fetch_*/save_* 系関数はページネーション対応かつ冪等保存（ON CONFLICT DO UPDATE）です。
- ETL は差分更新を基本とし、backfill_days（デフォルト 3 日）で直近データをやり直します（API の後出し修正対策）。
- 品質チェックは Fail-Fast ではなく、全チェックを実行して問題リスト（QualityIssue）を返します。呼び出し元で重大度に応じた対応を行います。
- Audit モジュールはすべてのタイムスタンプを UTC に固定することを想定しています（init_audit_schema で SET TimeZone='UTC' を実行）。

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py  -- パッケージ定義（version 等）
  - config.py    -- 環境変数・設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント（取得・保存）
    - schema.py         -- DuckDB スキーマ定義・初期化
    - pipeline.py       -- ETL パイプライン（差分取得・品質チェック）
    - quality.py        -- データ品質チェック
    - audit.py          -- 監査ログ（signal / order_request / executions）
    - pipeline.py
  - strategy/
    - __init__.py       -- 戦略モジュールのプレースホルダ
  - execution/
    - __init__.py       -- 発注/約定関連プレースホルダ
  - monitoring/
    - __init__.py       -- 監視用プレースホルダ

各ファイルの責務はソース内ドキュメントに詳述しています。特に data/* は ETL / schema / audit / quality を横断するコア部分です。

## 開発・運用上の注意

- データベースは DuckDB を採用しているため、オンディスクファイルでもインメモリでも利用可能です。運用時は適切にバックアップ・アクセス制御を行ってください。
- 実戦運用（live 環境）では KABUSYS_ENV を `live` に設定してください。設定により一部ロジック（例: 発注実行の分岐など）を切り替えることを想定しています。
- 発注（execution）や戦略（strategy）は本パッケージ外で実装することが想定されています。監査テーブルに対応するよう、発注処理は order_request_id 等を使用して冪等制御を行ってください。

---

ご不明点や README に追加したい内容（例: CI / テスト手順、具体的な SQL 例、.env.example のテンプレート等）があれば教えてください。必要に応じて README を拡張します。