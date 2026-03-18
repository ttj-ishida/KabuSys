KabuSys
=======

日本株向けの自動売買／データ基盤ライブラリです。  
DuckDB をデータストアに使い、J-Quants API からのデータ取得、ETL、品質チェック、ニュース収集、特徴量計算、監査ログなどを一貫して提供します。研究・バッチ処理・発注連携の基盤実装を主眼に置いたモジュール群です。

主な特徴
-------
- J-Quants API クライアント（レート制御・リトライ・トークン自動更新・ページネーション対応）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar など
- DuckDB ベースのスキーマ定義・初期化（raw / processed / feature / execution / audit 層）
  - data.schema.init_schema, data.schema.get_connection
- ETL パイプライン（差分更新・バックフィル・品質チェック）
  - data.pipeline.run_daily_etl、個別ETL: run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック（欠損・スパイク・重複・日付不整合）
  - data.quality.run_all_checks
- ニュース収集（RSS -> 前処理 -> raw_news 登録、銘柄抽出）
  - data.news_collector.fetch_rss / run_news_collection / save_raw_news
- 研究用特徴量計算（モメンタム、ボラティリティ、バリュー、将来リターン、IC 等）
  - research.factor_research.calc_momentum / calc_volatility / calc_value
  - research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize（Z スコア正規化ユーティリティ）
- マーケットカレンダー管理（営業日判定・前後営業日取得・夜間更新ジョブ）
  - data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
- 監査ログ（signal → order_request → execution のトレース用テーブル群）
  - data.audit.init_audit_schema / init_audit_db

セットアップ
--------

前提
- Python 3.10 以上（型ヒントに | 演算子を使用）
- DuckDB、defusedxml 等のライブラリが必要

例: pip で最低限の依存をインストールする
```
pip install duckdb defusedxml
```

環境変数 / .env
- このパッケージは環境変数から設定を読み込みます。package 内の settings 経由で使用してください（kabusys.config.settings）。
- 自動でプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、そこにある .env および .env.local を読み込みます。
- 自動 .env 読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時に有用）。

主な環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
- KABU_API_PASSWORD : kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN : Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID : Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH : DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV : 動作環境（development / paper_trading / live。省略時 development）
- LOG_LEVEL : ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL。省略時 INFO）

例 (.env.example)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

基本的な使い方
----------

1) DuckDB スキーマを初期化する
- data.schema.init_schema() で必要な全テーブルを作成します。

例:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行する
- data.pipeline.run_daily_etl を呼ぶと、カレンダー・株価・財務データを差分取得して保存し、品質チェックを実行します。

例:
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブを実行する
- RSS を収集して raw_news に保存し、既知銘柄セットがあれば news_symbols に紐付けます。

例:
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9432"}  # 例: 有効銘柄コード集合
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

4) 研究・特徴量計算
- research.factor_research や research.feature_exploration の関数は DuckDB 接続と日付を渡して利用します。
- zscore_normalize は data.stats により提供され、計算結果の正規化に使います。

例:
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, zscore_normalize
conn = get_connection("data/kabusys.duckdb")
mom = calc_momentum(conn, date(2025, 1, 31))
vol = calc_volatility(conn, date(2025, 1, 31))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

主要 API（抜粋）
-------------
- kabusys.config.settings — 環境変数からの設定取得（必須値は _require() により例外）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss, save_raw_news, run_news_collection, extract_stock_codes
- kabusys.data.quality
  - run_all_checks（個別 check_* 関数も公開）
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize
- kabusys.data.calendar_management
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False), init_audit_db(db_path)

ディレクトリ構成（抜粋）
--------------------
src/kabusys/
- __init__.py — パッケージ初期化（__version__ 等）
- config.py — 環境変数読み込み・Settings
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + 保存）
  - news_collector.py — RSS取得・前処理・DB保存
  - schema.py — DuckDB スキーマ定義・初期化
  - pipeline.py — ETL パイプライン
  - quality.py — 品質チェック
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - features.py — 特徴量ユーティリティ公開
  - calendar_management.py — マーケットカレンダー管理
  - audit.py — 監査ログ用テーブル初期化
  - etl.py — ETL 用公開型再エクスポート
- research/
  - __init__.py — 研究用 API の集約エクスポート
  - factor_research.py — モメンタム/ボラティリティ/バリュー等
  - feature_exploration.py — 将来リターン・IC・サマリー等
- strategy/ — 戦略層（空の __init__、実装はユーザが追加）
- execution/ — 発注/実行層（空の __init__、実装はユーザが追加）
- monitoring/ — 監視系モジュール用（空の __init__）

運用上の注意
----------
- 環境（KABUSYS_ENV）が live の場合は本番発注や実口座との連携に注意してください。テスト・リハーサルは paper_trading を用いることを推奨します。
- J-Quants のレート制限（120 req/min）はクライアント実装で尊重されますが、並列化や別プロセスからの呼び出しで規約を破らないようにしてください。
- ニュース収集は外部 URL を扱うため SSRF 対策および XML パーサの安全化（defusedxml）を実装しています。外部フィードの信頼性やサイズに注意してください。
- DuckDB のバージョンやランタイム状況により SQL の挙動（制約やインデックスの扱い）が異なることがあります。テスト環境で十分に検証してください。

拡張・開発
---------
- strategy / execution / monitoring ディレクトリはユーザが戦略やブローカー接続を実装するための入口です。監査ログ・signal_queue 等のスキーマに合わせて実装してください。
- 研究用途の関数は標準ライブラリ中心で実装されているため、pandas 等での代替実装を容易に統合できます。必要に応じて性能改善（ベクトル化・DuckDB SQL 化）を検討してください。

ライセンス・貢献
--------------
（このテンプレートにはライセンス情報は含まれていません。実際のリポジトリでは LICENSE ファイルに記載してください。）

問い合わせ
----------
- 実装に関する詳細や使い方の質問は、リポジトリの issue へ記載してください。README の改善提案も歓迎します。