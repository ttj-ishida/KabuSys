# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ集です。  
J-Quants API や RSS を取り込み、DuckDB に保存・整備して戦略や実行モジュールへデータを提供します。  
（内部的に ETL、品質チェック、監査ログ、ニュース収集、マーケットカレンダー管理などの機能を提供します）

バージョン: 0.1.0

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - リクエストレート制限（120 req/min）の遵守、再試行（指数バックオフ）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）の記録による Look-ahead Bias 回避
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードを収集して raw_news に冪等保存
  - URL 正規化・トラッキングパラメータ除去・SHA-256 による記事ID生成
  - SSRF 防止、受信サイズ制限、gzip 解凍の安全対策
  - 銘柄コード抽出と news_symbols への紐付け機能

- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル対応
  - 市場カレンダーの先読み、株価・財務データの差分取得と保存
  - 品質チェック（欠損、スパイク、重複、日付整合性）

- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、期間内営業日の列挙
  - JPX カレンダーの夜間差分更新ジョブ

- 監査ログ（Audit）
  - シグナル→発注→約定までを UUID 連鎖でトレースするテーブル群の初期化
  - order_request_id による冪等化、すべて UTC タイムスタンプで保存

- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付不整合の検出と報告

---

## 必要要件

- Python 3.9+
- 主要依存: duckdb, defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

（プロジェクトのセットアップ時に必要パッケージを requirements.txt / pyproject.toml で管理してください）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン／取得
2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージのインストール（例）
   - pip install duckdb defusedxml
   - またはプロジェクトが poetry / pip-tools を使用している場合は該当手順に従う
4. 開発用にローカルパッケージをインストール（任意）
   - pip install -e .

注意: テストや CI で自動的に `.env` をロードしたくない場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数（.env）

パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。既存の OS 環境変数は保護され、`.env.local` は `.env` を上書きできます。

主な必須/推奨環境変数（例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (監視用) のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

サンプル `.env`:

JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 初期化（DuckDB スキーマ）

DuckDB のスキーマは冪等に作成できます。アプリ動作前に一度初期化してください。

例: Python REPL / スクリプトで実行

- 全スキーマ（データ層／機能層／実行層）を初期化:
  from kabusys.data import schema
  conn = schema.init_schema("data/kabusys.duckdb")  # ":memory:" も使用可能

- 監査ログ専用スキーマを初期化:
  from kabusys.data import audit
  conn = audit.init_audit_db("data/kabusys_audit.duckdb")

init_schema は親ディレクトリを自動作成します（ファイルパスが ":memory:" でない場合）。

---

## 使い方（主要な API サンプル）

以下は最小限の利用例です。実運用ではエラーハンドリングやログ、認証トークン管理を適切に行ってください。

- 日次 ETL を実行して DuckDB にデータを保存する（市場カレンダー、株価、財務、品質チェック）:

  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)
  print(result.to_dict())

- ニュース収集ジョブを実行（RSS 取得 → raw_news 保存 → 銘柄紐付け）:

  from kabusys.data import schema, news_collector
  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コード集合
  res = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(res)  # {source_name: new_count, ...}

- 市場カレンダー差分更新バッチ:

  from kabusys.data import schema, calendar_management
  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved={saved}")

- J-Quants API から手動でデータ取得する例:

  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  print(len(records))

備考:
- jquants_client は内部でレート制限・リトライ・トークン自動リフレッシュを行います。
- news_collector.fetch_rss は SSRF 防止・XML の安全パース・受信サイズ制限などの対策が施されています。

---

## ログ・デバッグ

- LOG_LEVEL 環境変数でログレベルを制御します（デフォルト: INFO）。
- デバッグ時は LOG_LEVEL=DEBUG を指定して詳細ログを確認してください。

---

## テスト・開発ヒント

- 自動 .env ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- テストでインメモリ DB を使う場合: db_path に ":memory:" を渡す
- news_collector._urlopen などのネットワーク部分はモックしてテスト可能に設計されています

---

## ディレクトリ構成

概略:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント、保存ロジック
    - news_collector.py      # RSS ニュース収集・保存・銘柄抽出
    - pipeline.py            # ETL パイプライン（run_daily_etl 等）
    - schema.py              # DuckDB スキーマ定義と初期化
    - calendar_management.py # マーケットカレンダー管理
    - audit.py               # 監査ログスキーマの初期化
    - quality.py             # データ品質チェック
  - strategy/
    - __init__.py            # 戦略モジュール（拡張点）
  - execution/
    - __init__.py            # 発注・実行層（拡張点）
  - monitoring/
    - __init__.py            # 監視・アラート（拡張点）

---

## 拡張ポイント

- strategy/ と execution/ は拡張可能（カスタム戦略やブローカー連携を実装）
- Slack 通知や監視周りは monitoring/ に追加して運用アラートを統合可能
- DuckDB のテーブル・インデックス定義は schema.py を編集して拡張してください

---

補足・注意
- 本 README はコードベース（src/kabusys 以下）に基づく概要・利用手順のまとめです。実運用時は API トークン管理（安全な保管）、適切なバックアップ、監査ログの運用方針を検討してください。