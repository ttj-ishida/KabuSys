# KabuSys

日本株向け自動売買基盤ライブラリ（パッケージ）  
本リポジトリはデータ収集・ETL・品質チェック・監査ログ・カレンダー管理・ニュース収集など、量的運用・システム化に必要な基盤コンポーネントを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システム向けの内部基盤ライブラリです。主に以下を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの取得（レート制御・リトライ・トークン自動リフレッシュ対応）
- DuckDB ベースのスキーマ定義と初期化ユーティリティ（Raw / Processed / Feature / Execution レイヤー）
- 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュース（RSS）収集器：URL 正規化・SSRF 対策・XML セーフパーサ・冪等保存
- マーケットカレンダー管理（営業日判定、前後営業日探索、夜間更新ジョブ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル → 発注要求 → 約定）用スキーマと初期化機能

設計方針としては冪等性（ON CONFLICT / RETURNING）、トレーサビリティ（fetched_at / created_at 等のタイムスタンプ）、外部 API の堅牢な呼び出し（レート制限・指数バックオフ）を重視しています。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定のプロパティアクセス（settings）
  - 自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- データ取得（kabusys.data.jquants_client）
  - 日次株価（OHLCV）取得（ページネーション対応）
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミッタ、リトライ（408/429/5xx、指数バックオフ）、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・解析（defusedxml）
  - URL 正規化（トラッキングパラメータ除去）・記事 ID の SHA-256 ベース生成
  - SSRF 防止（スキーム検証・プライベート IP チェック・リダイレクト検査）
  - レスポンスサイズ制限、gzip 解凍の安全性チェック
  - DuckDB への冪等保存（INSERT ... RETURNING / ON CONFLICT DO NOTHING）
  - テキスト前処理・銘柄コード抽出
- データスキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義（raw / processed / feature / execution）
  - init_schema(), get_connection()
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新ロジック（最終取得日の取得・バックフィル）
  - run_prices_etl, run_financials_etl, run_calendar_etl
  - run_daily_etl（まとめて実行し品質チェックを実行）
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job（夜間バッチでの差分更新）
- 品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比）、重複、日付不整合を SQL ベースで検出
  - QualityIssue 型で問題を集約
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions を含む監査スキーマ
  - init_audit_db / init_audit_schema による初期化

---

## 前提 / 依存関係

- Python 3.10 以上（`|` 型注釈等を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# または開発用:
pip install -e .
```

（リポジトリに requirements.txt があればそれを利用してください。）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに入る
   ```bash
   git clone <this-repo-url>
   cd <repo>
   ```

2. 仮想環境作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # ある場合
   # または個別インストール
   pip install duckdb defusedxml
   ```

3. 環境変数設定 (.env をプロジェクトルートに作成)
   必須となる環境変数（例）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動読み込みはプロジェクトルートの `.env` と `.env.local` を順に読み込みます。自動ロードを無効にするには
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

4. DuckDB スキーマ初期化（例）
   Python REPL またはスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

5. （任意）監査ログ DB 初期化:
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（サンプル）

- 日次 ETL 実行
  ```python
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）
  ```python
  from datetime import date
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl

  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

- ニュース収集（RSS）
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "8306"}  # 例: 有効な銘柄コードセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- 品質チェックのみ実行
  ```python
  from kabusys.data.quality import run_all_checks
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  issues = run_all_checks(conn)
  for i in issues:
      print(i)
  ```

- マーケットカレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from kabusys.data.schema import get_connection

  conn = get_connection("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

注意:
- J-Quants API 呼び出しはレート制限（120 req/min）を厳守します。大量取得の際は時間が掛かります。
- get_id_token は自動でリフレッシュされる実装ですが、refresh token は settings に必須で設定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py              -- RSS ニュース収集器（前処理・SSRF対策・DB保存）
    - schema.py                      -- DuckDB スキーマ定義・初期化
    - pipeline.py                    -- ETL パイプライン（差分更新・run_daily_etl 等）
    - calendar_management.py         -- カレンダー管理・営業日ロジック
    - audit.py                       -- 監査ログスキーマ / 初期化
    - quality.py                     -- データ品質チェック
  - strategy/                        -- 戦略モジュール（拡張用）
    - __init__.py
  - execution/                       -- 発注・実行管理モジュール（拡張用）
    - __init__.py
  - monitoring/                      -- 監視用モジュール（拡張用）
    - __init__.py

---

## 開発者向けメモ

- 型・互換性: コードは Python 3.10+ の構文（型合併演算子 | など）を使用しています。
- テスト: 環境変数自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してテスト環境を汚染しないようにできます。
- セキュリティ:
  - RSS の XML パースに defusedxml を使用しています（XML Bomb 対策）。
  - RSS 取得時は最大受信バイト数を制限し、gzip 解凍後もサイズチェックします。
  - リダイレクトや最終 URL のホストがプライベート IP の場合はブロックします（SSRF 対策）。
- DB トランザクション: ニュースや symbols の保存はトランザクションでまとめられ、失敗時はロールバックします。

---

## ライセンス / 貢献

この README はコードベースの機能説明用の簡易ドキュメントです。実プロジェクトでの利用・配布時はライセンス表記や貢献ガイドラインを追記してください。

---

必要であれば、README に以下を追加できます:
- API 使用例（より具体的なコードサンプル）
- CI / テスト実行手順
- デバッグ / ログレベル設定例
- .env.example の具体的なテンプレート

追記希望があれば教えてください。