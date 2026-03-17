# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（KabuSys）。  
J-Quants / kabuステーション と連携してデータ取得、ETL、品質チェック、ニュース収集、監査ログ等の基盤機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つ Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを取得し DuckDB に保存する
- ニュース RSS を収集し前処理のうえ DB に格納、銘柄コードと紐付ける
- ETL パイプライン（差分取得・バックフィル・品質チェック）を実装
- マーケットカレンダー（JPX）の営業日判定・探索ユーティリティ
- 監査ログ（シグナル → 発注 → 約定）のスキーマを提供
- 設定を環境変数/.env で管理（自動読み込み機能あり）

設計上の特徴:
- API レート制御・リトライ・トークン自動リフレッシュを実装
- DuckDB を用いた冪等保存（ON CONFLICT や INSERT ... RETURNING を活用）
- セキュリティ考慮（RSS の SSRF 防止・XML の defusedxml 利用・レスポンスサイズ制限 等）
- 品質チェックを集約して ETL 後にレポート可能

---

## 機能一覧

- 環境設定管理
  - .env/.env.local 自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ラッパー（settings オブジェクト）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 日足 (OHLCV) / 財務 (四半期) / マーケットカレンダー取得
  - レートリミット（120 req/min）とリトライ、401 時のトークン自動更新
  - DuckDB への冪等保存関数（save_*）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL除去・空白正規化）
  - 記事ID を正規化URL の SHA-256 で生成（先頭32文字）
  - SSRF 対策（スキーム/プライベートIP 検査、リダイレクト検査）
  - DuckDB へのバルク挿入（INSERT ... RETURNING）と銘柄紐付け
- データスキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - 初期化 helper（init_schema, get_connection）
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得（最終取得日ベース）・バックフィル対応
  - 日次 ETL の統合（run_daily_etl）
  - 各種個別 ETL ジョブ（prices, financials, calendar）
  - 品質チェックの統合実行
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等
  - 夜間バッチの calendar_update_job
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions 等を定義
  - init_audit_schema / init_audit_db
- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク、重複、日付不整合の検出
  - QualityIssue 型のリストで問題を返す

---

## 前提・依存関係

- Python 3.10 以上（型注釈に PEP 604 などを使用）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
```

プロジェクト配布パッケージがある場合は requirements.txt / setup.cfg 等に従ってください。

---

## 環境変数 / .env

自動で .env / .env.local をプロジェクトルートから読み込みます（ルート判定: .git または pyproject.toml）。  
自動読み込みを無効化するには環境変数を設定:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な必須環境変数:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID      : Slack チャネルID（必須）

任意 / デフォルト値あり:
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（デフォルト: data/monitoring.db）

注意: settings オブジェクト経由でこれらを取得します（kabusys.config.settings）。

---

## セットアップ手順（開発／実行用）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install duckdb defusedxml
   - （その他プロジェクト固有の依存があればインストール）

3. 環境変数設定
   - プロジェクトルートに `.env` を作成（.env.example があれば参照）
   - 必須変数を設定する（上記参照）

4. DuckDB スキーマ初期化（Python REPL もしくはスクリプトで）
   - 例:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - 監査ログ専用 DB 初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")
     ```

---

## 使い方（簡単な例）

- 日次 ETL を実行する（J-Quants トークンは settings で取得されます）:
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
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- 市場カレンダー更新（夜間バッチ）:
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックの単独実行:
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  issues = run_all_checks(conn, target_date=None, reference_date=date.today())
  for i in issues:
      print(i)
  ```

---

## ディレクトリ構成

リポジトリ中の主要なファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理・自動 .env 読み込み・settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API との連携（取得・保存・認証・レート制御）
    - news_collector.py
      - RSS フィード取得・前処理・DB 保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py
      - ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py
      - JPX カレンダー管理・営業日ユーティリティ・calendar_update_job
    - audit.py
      - 監査ログ用スキーマ（signal_events / order_requests / executions）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - strategy/
    - __init__.py (戦略関連モジュール置き場)
  - execution/
    - __init__.py (発注/ブローカー連携置き場)
  - monitoring/
    - __init__.py (監視 / メトリクス関連置き場)

各モジュールは単一責任を重視して設計されており、戦略（strategy）や発注実装（execution）はプロジェクト固有の実装に合わせて拡張することを想定しています。

---

## 運用上の注意

- J-Quants の API レート制限（120 req/min）を尊重してください。jquants_client はモジュール内で簡易レートリミッタを実装していますが、追加のスケジューリングや並列化には注意が必要です。
- DuckDB ファイルは共有/バックアップポリシーを検討してください（大容量化する可能性あり）。
- ニュース RSS の取得時は外部コンテンツを取り込むため、セキュリティ上の懸念（SSRF等）に配慮していますが、内部環境での運用時はネットワークポリシーも確認してください。
- 本ライブラリは戦略層・実行層の提供は行わず、あくまでデータ基盤・監査・ETL を提供します。実際の発注を行う場合は万全の検証・リスク管理を行ってください。

---

README の内容やサンプルを拡張したい場合は、どの部分（運用手順、CI/CD、docker化、追加サンプル等）を詳しくしたいか教えてください。