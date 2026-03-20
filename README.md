# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants API から市場データ・財務データ・カレンダーを取得し、DuckDB に保存、特徴量作成・シグナル生成・ETL パイプライン・ニュース収集などを行うモジュール群を提供します。

バージョン: 0.1.0

---

## 主要な特徴

- J-Quants API クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）
- DuckDB を用いたデータスキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
- ETL パイプライン（差分取得・バックフィル・品質チェック呼び出し）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- 特徴量エンジニアリング（Zスコア正規化・ユニバースフィルタ・features テーブルへの保存）
- シグナル生成（ファクター + AI スコア統合、BUY/SELL ロジック、冪等な signals 書き込み）
- RSS ベースのニュース収集（SSRF対策・トラッキングパラメータ除去・記事と銘柄の紐付け）
- マーケットカレンダー管理（営業日判定・next/prev トレーディングデイ、夜間更新ジョブ）
- 監査ログ / 発注トレーサビリティスキーマ（order_request → execution の連鎖追跡を想定）

---

## 必要条件

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - defusedxml

（インストールはプロジェクトの setup / requirements に依存します。上記は動作に必要な主要パッケージの例です。）

---

## 環境変数

このプロジェクトは環境変数（または .env ファイル）を利用して設定を読み込みます。自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。必要な主要環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite ファイルパス（省略時 data/monitoring.db）
- KABUSYS_ENV: 環境 ("development", "paper_trading", "live")（省略時 development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（省略時 INFO）

自動 env ロードを無効にする:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

サンプル .env:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   - git clone ...

2. Python 環境の準備（推奨: 仮想環境）
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   - pip install "duckdb" "defusedxml"
   - （プロジェクトに requirements.txt / pyproject があればそちらを利用してください）
   - 開発インストール: pip install -e .

4. 環境変数を設定
   - 上記の .env をプロジェクトルートに作成するか、環境に直接設定します。

5. DuckDB スキーマ初期化
   - Python REPL / スクリプトから:
     ```
     from kabusys.data.schema import init_schema
     from kabusys.config import settings

     conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は .env の DUCKDB_PATH から取得
     ```

---

## 使い方（主要なユースケース）

以下は代表的な操作例です。Python スクリプトから直接呼ぶ想定です。

- ETL（日次データ取得）
  ```
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.schema import init_schema, get_connection
  from kabusys.data.pipeline import run_daily_etl

  # DB 初期化（既に初期化済みなら init_schema しても安全）
  conn = init_schema(settings.duckdb_path)

  # 日次 ETL 実行（デフォルトで当日）
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- 特徴量（features）作成
  ```
  from datetime import date
  from kabusys.strategy import build_features
  from kabusys.config import settings
  from kabusys.data.schema import get_connection

  conn = get_connection(settings.duckdb_path)
  count = build_features(conn, target_date=date.today())
  print(f"features upserted: {count}")
  ```

- シグナル生成
  ```
  from datetime import date
  from kabusys.strategy import generate_signals
  from kabusys.config import settings
  from kabusys.data.schema import get_connection

  conn = get_connection(settings.duckdb_path)
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")
  ```

- ニュース収集ジョブ（RSS -> raw_news）
  ```
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import get_connection
  from kabusys.config import settings

  conn = get_connection(settings.duckdb_path)
  known_codes = {"7203", "6758", ...}  # 銘柄コードセット（存在する銘柄）
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)  # {source_name: saved_count}
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```
  from kabusys.data.calendar_management import calendar_update_job
  conn = get_connection(settings.duckdb_path)
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

- J-Quants からのデータ取得（低レベル）
  ```
  from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  ```

注意:
- 上記の多くの関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取ります。
- 多くの操作は冪等（idempotent）設計で、既存データに対する安全な上書きをサポートします（ON CONFLICT など）。

---

## 開発向けヒント

- settings は kabusys.config.settings として利用できます。必須 env が未設定の場合は ValueError を投げます。
- 自動的に .env / .env.local をロードします（プロジェクトルート検出）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログは logging モジュールに従います。LOG_LEVEL 環境変数で設定します。
- DuckDB を直接操作しているため、SQL を確認すると処理の挙動が把握しやすいです。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
  - 環境変数管理（.env 自動ロード・Settings クラス）
- data/
  - __init__.py
  - jquants_client.py          — J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py         — RSS ニュース取得・保存・銘柄抽出
  - schema.py                 — DuckDB スキーマ定義と init_schema
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - pipeline.py               — ETL パイプライン（run_daily_etl 等）
  - features.py               — data.stats の公開ラッパー
  - calendar_management.py    — market_calendar 管理・営業日判定
  - audit.py                  — 監査ログ / 発注トレーサビリティ用 DDL
  - (その他: quality モジュール等想定)
- research/
  - __init__.py
  - factor_research.py        — モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration.py    — 将来リターン計算・IC・統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py    — ファクター正規化・ユニバースフィルタ・features への保存
  - signal_generator.py       — final_score 計算と BUY/SELL シグナル出力
- execution/
  - __init__.py               — 発注層（将来的な実装想定）
- monitoring/                 — 監視用モジュール（実装ファイル想定）

各ファイルは docstring と関数レベルのコメントで設計方針・処理フローが詳述されています。

---

## よくある質問 / 注意点

- Python バージョンは 3.10 以上を想定（型注釈で | 演算子を使用しているため）。
- DuckDB のファイルはデフォルトで data/kabusys.duckdb に作成されます。別パスを使う場合は DUCKDB_PATH を設定してください。
- ETL では market_calendar を先に更新し、営業日調整を行った後に prices / financials を取得します（営業日での欠損対策）。
- ニュース収集は外部 RSS を取得するためネットワーク・セキュリティ面に配慮（SSRF 防止・ヘッダ検査・gzip サイズ制限など）していますが、本番で使う際はソースリストやタイムアウトの調整を行ってください。
- 本ライブラリは発注API（証券会社）への実送信部分は分離されており、strategy 層は発注層に直接依存しない設計です。

---

以上が README の概要です。必要であれば以下の追加ドキュメントを作成できます：
- API リファレンス（関数一覧・引数説明）
- 運用手順（cron / CI での ETL 実行例）
- テスト手順とモックの使い方

どれを追加しますか？