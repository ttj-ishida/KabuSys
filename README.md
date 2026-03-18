# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、DuckDBスキーマ定義、監査ログ（発注・約定トレース）などの基盤機能を提供します。

現在のバージョン: 0.1.0

## 概要
KabuSys は以下の機能群を持つライブラリ群です。

- J-Quants API からの株価・財務・市場カレンダー取得（レート制御・リトライ・トークン自動更新付き）
- DuckDB を用いた階層化スキーマ（Raw / Processed / Feature / Execution）と初期化ユーティリティ
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- RSS ベースのニュース収集・前処理・銘柄抽出・DB保存（SSRF対策、XML脆弱性対策）
- マーケットカレンダー管理（営業日判定、次営業日/前営業日探索、夜間更新ジョブ）
- 監査ログ（signal → order_request → executions のトレース用スキーマ）
- データ品質チェック（欠損・重複・スパイク・日付整合性）

設計上のポイント:
- API レート制限（J-Quants: 120 req/min）を遵守
- リトライ（指数バックオフ）／401時の自動トークンリフレッシュ
- DuckDB 側は冪等性を担保する INSERT … ON CONFLICT を活用
- セキュリティ考慮（defusedxml / SSRF対策 / レスポンスサイズ制限 等）

## 機能一覧
- data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
- data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- data.schema
  - init_schema, get_connection（DuckDBスキーマ定義と初期化）
- data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- data.audit
  - init_audit_schema, init_audit_db（監査ログ用スキーマ）
- data.quality
  - 個別チェックと run_all_checks（missing_data / duplicates / spike / date_consistency）
- config
  - 環境変数読み込み・設定取得（自動 .env ロード、必要な env の検査）

## 前提・依存
推奨 Python バージョン: 3.10 以降（型ヒントに | 演算子を使用しているため）  
主な依存パッケージ（最低限）:
- duckdb
- defusedxml

（プロジェクト用途により追加のパッケージが必要になることがあります。requirements.txt がある場合はそちらを参照してください）

## 環境変数
主要な環境変数（必須とデフォルト）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabu station API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID

オプション（デフォルト有り）:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...。デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを無効化（1 で無効）

自動 .env 読み込み動作:
- パッケージ起点のファイルパスからプロジェクトルート（.git または pyproject.toml）を探し、見つかった場合はそのルートの `.env` を読み込みます。
- 読み込み優先順位: OS 環境 > .env.local > .env  
- テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / コピー
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数を直接設定してください。例:
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yyyy
     SLACK_BOT_TOKEN=zzzz
     SLACK_CHANNEL_ID=C123456
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 機密情報は .env.local に置き、リポジトリには .env.example を置く運用が推奨されます。
5. DuckDB スキーマ初期化（次項の使い方参照）

## 使い方（基本的な例）
以下は Python インタプリタやスクリプトから利用する基本例です。

1) DuckDB スキーマの初期化
```python
from kabusys.data import schema

# デフォルトのファイルパスを使う場合
conn = schema.init_schema("data/kabusys.duckdb")

# メモリDB を試したいとき
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL（株価・財務・カレンダーの差分取得と保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定しなければ今日が対象
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は銘柄抽出で有効なコードの集合（例: {"7203", "6758", ...}）
results = run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: 新規保存件数}
```

4) カレンダーの夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar records:", saved)
```

5) 監査ログスキーマの追加（既存の DuckDB 接続に監査テーブルを追加）
```python
from kabusys.data.audit import init_audit_schema
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

6) 品質チェックを直接実行
```python
from kabusys.data.quality import run_all_checks
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
issues = run_all_checks(conn)
for i in issues:
    print(i)
```

## よくある運用フロー（例）
- 深夜バッチ: calendar_update_job を実行してマーケットカレンダーを更新
- 朝起動時: run_daily_etl を実行して前営業日のデータを確定（バックフィル含む）
- 定期（数分〜数時間）: news_collector を実行してニュース収集、new_ids に基づき銘柄紐付け
- 監査: order_request / executions を audit スキーマに保存しておき、後から完全トレース可能にする

## 開発・テスト上の注意
- 自動 .env 読み込みはプロジェクトルートを .git / pyproject.toml から検出します。テストで環境汚染を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- news_collector は外部 HTTP を直接叩きます。ユニットテストでは kabusys.data.news_collector._urlopen などをモックしてネットワークを切り離してください。
- J-Quants API 呼び出しはレート制限とリトライロジックが組み込まれていますが、実際の運用では API 仕様変更やレート上限に注意してください。

## ディレクトリ構成
プロジェクトの主要ファイル／モジュール構成（一部抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - data/
      - __init__.py
      - jquants_client.py
      - news_collector.py
      - schema.py
      - pipeline.py
      - calendar_management.py
      - audit.py
      - quality.py
    - strategy/
      - __init__.py
    - execution/
      - __init__.py
    - monitoring/
      - __init__.py

主要モジュールの役割:
- kabusys/config.py: 環境変数管理・設定取得
- kabusys/data/schema.py: DuckDB の DDL（テーブル・インデックス）定義と init_schema
- kabusys/data/jquants_client.py: J-Quants API クライアント + DuckDB 保存ユーティリティ
- kabusys/data/pipeline.py: ETL の統合エントリ（run_daily_etl 等）
- kabusys/data/news_collector.py: RSS 取得・前処理・DB保存・銘柄抽出
- kabusys/data/quality.py: データ品質チェック
- kabusys/data/audit.py: 監査ログスキーマ初期化

## ライセンス / 貢献
（この README ではライセンス情報や貢献規約は省略しています。リポジトリに LICENSE や CONTRIBUTING.md がある場合はそちらを参照してください。）

---

この README はコードベースの公開 API と運用上のポイントをまとめたものです。より詳細な設計ドキュメント（DataPlatform.md 等）や運用手順書があれば、それに従って運用・拡張してください。必要であれば README に記載するサンプルコマンドや .env.example のテンプレートも追加できます。希望があれば作成します。