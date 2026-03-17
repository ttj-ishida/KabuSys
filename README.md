# KabuSys

日本株自動売買基盤ライブラリ KabuSys の README（日本語）

概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォーム／自動売買基盤のライブラリ群です。  
J-Quants API から市場データ（株価・財務・マーケットカレンダー）を取得して DuckDB に格納する ETL、RSS からニュースを収集して保存・銘柄紐付けするモジュール、データ品質チェック、監査ログ（発注→約定のトレース）などを提供します。

主な設計方針：
- API レート制御、リトライ、トークン自動更新などの堅牢な API クライアント設計
- DuckDB を用いた冪等性のあるデータ保存（ON CONFLICT / トランザクション）
- SSRF / XML Bomb 等を考慮した安全なニュース収集
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログでの完全なトレーサビリティ

---

## 機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダーの取得
  - レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークン更新
  - 取得時刻（fetched_at）を UTC 記録し look-ahead bias を防止

- DuckDB スキーマ管理 / 初期化
  - Raw / Processed / Feature / Execution / Audit 各レイヤーのテーブル定義
  - インデックス、外部キー、制約付き DDL を提供
  - 冪等的な初期化（既存テーブルはスキップ）

- ETL パイプライン
  - 差分更新（最終取得日をベースに新規分のみ取得）
  - backfill 設定で直近の再取得（API 後出し修正の吸収）
  - 品質チェック実行（quality モジュール）

- ニュース収集
  - RSS フィードの取得・パース（defusedxml を使用）
  - URL 正規化・トラッキングパラメータ除去・記事ID を SHA-256 で生成（先頭32文字）
  - SSRF / 受信サイズ / gzip 解凍上限など安全対策
  - raw_news と news_symbols テーブルへの冪等保存

- マーケットカレンダー管理
  - 営業日判定、前後の営業日取得、期間内営業日の列挙
  - カレンダーの夜間差分更新ジョブ

- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合（未来日・非営業日データ）

- 監査ログ（Audit）
  - signal → order_request → execution の階層的トレース用テーブル群
  - 発注の冪等キー（order_request_id）等を含む

---

## セットアップ手順

前提：Python 3.9+（type hints に Union | など使用）、pip が利用できる環境

1. リポジトリをクローン（既にソースがある想定なら不要）
   - git clone ...

2. 仮想環境を作成・アクティベート（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がない場合は主要な依存を個別インストール：
     - pip install duckdb defusedxml
   - パッケージ化されている場合：
     - pip install -e .

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（runtime で参照）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション等の API パスワード（必須）
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - 任意 / デフォルト
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development|paper_trading|live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

   - サンプル `.env`（プロジェクトルートに配置）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. データベース初期化（DuckDB）
   - Python REPL またはスクリプトで schema を初期化：
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     ```
   - 監査ログのみ別 DB にしたい場合は `init_audit_db()` を使用

---

## 使い方（主要 API とサンプル）

以下は簡単な例です。実運用ではログ設定や例外処理、ID トークンの管理を適宜追加してください。

- DuckDB スキーマ初期化
  ```python
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
  ```

- 日次 ETL 実行（株価・財務・カレンダー取得 + 品質チェック）
  ```python
  from kabusys.data import pipeline
  from kabusys.data import schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")  # 既存接続を取得
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 市場カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print("saved:", saved)
  ```

- RSS ニュース収集
  ```python
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  # 既知銘柄コードセット（抽出に利用）
  known_codes = {"7203", "6758", "9984"}  # 実運用では一覧取得
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants の単体呼び出し例（トークンは Settings から自動取得）
  ```python
  from kabusys.data import jquants_client as jq
  # ある銘柄の期間を取得
  records = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,3,31))
  ```

- 品質チェックの個別実行
  ```python
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点：
- J-Quants の rate-limit（120 req/min）やリトライ挙動はクライアント側で制御されていますが、実行環境の並列度に注意してください。
- get_id_token() は内部で settings.jquants_refresh_token を参照します。環境変数が未設定だと例外になります。
- 自動 .env ロードは、モジュール import 時にプロジェクトルート（.git または pyproject.toml）を基に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用して抑止できます。

---

## ディレクトリ構成

主要なファイル・モジュール一覧（src/kabusys 以下）：

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数と Settings クラスの定義（自動 .env ロード機能、必須チェック）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、レートリミット・リトライ・トークン管理、DuckDB への保存関数
    - news_collector.py
      - RSS 収集・正規化・DB 保存・銘柄抽出ロジック
    - schema.py
      - DuckDB の DDL 定義と init_schema/get_connection
    - pipeline.py
      - ETL（差分更新、backfill、品質チェック）をまとめたパイプライン
    - calendar_management.py
      - マーケットカレンダー管理、営業日判定、更新ジョブ
    - audit.py
      - 監査ログ（signal / order_request / executions）テーブルの初期化
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - strategy/
    - __init__.py  （戦略関連のエントリプレースホルダ）
  - execution/
    - __init__.py  （発注実行関連のエントリプレースホルダ）
  - monitoring/
    - __init__.py  （監視 / メトリクス関連のエントリプレースホルダ）

各モジュールは docstring に設計方針と処理フローが記載されており、個別の API（関数・クラス）を通じて利用できます。

---

## 運用上の注意点 / ヒント

- バックフィル日数や calendar の lookahead などは pipeline.run_daily_etl の引数で調整できます（実運用では過取得・API 負荷と相談して最適化してください）。
- DuckDB ファイルはローカルでの高速分析に向きますが、複数プロセスで同時書き込みが発生する運用には注意してください（排他制御）。
- ニュース収集での銘柄抽出は単純な正規表現による 4 桁数字抽出です。必要に応じて名称マッチングや NLP 処理を追加してください。
- 監査ログは削除しない前提です。ディスク容量管理や古いデータのアーカイブ方針を策定してください。

---

もし README に追加してほしい内容（例：CI / テスト手順、サンプル .env.example ファイル、より詳しい API リファレンス、デプロイ手順など）があれば教えてください。