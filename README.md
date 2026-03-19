KabuSys (v0.1.0)
=================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼戦略エンジンの基盤ライブラリです。
主な目的は以下です。

- J-Quants など外部データソースから株価・財務・カレンダーを取得し DuckDB に蓄積する（ETL）
- ニュース（RSS）を収集して記事と銘柄の紐付けを行う
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）を提供
- 特徴量の正規化・合成（feature engineering）と戦略シグナル生成（buy/sell）のロジックを提供
- DuckDB スキーマ（Raw / Processed / Feature / Execution / Audit）を管理・初期化する

設計上のポイント
- DuckDB を中心にローカルで高速に処理できるよう設計
- API 呼び出しはレート制御・リトライ・トークン自動リフレッシュを実装
- DB 操作は冪等性（ON CONFLICT）を考慮
- ルックアヘッドバイアスを防ぐため、常に target_date 時点のデータのみを参照する方針

主な機能一覧
--------------
- data/jquants_client.py
  - J-Quants API クライアント（ページネーション、レートリミット、リトライ、トークン自動更新）
  - 生データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等保存: save_daily_quotes, save_financial_statements, save_market_calendar
- data/schema.py
  - DuckDB の DDL（テーブル・インデックス）定義と初期化関数 init_schema
- data/pipeline.py
  - 日次 ETL パイプラインの実装（run_daily_etl など）
- data/news_collector.py
  - RSS 取得・前処理・記事ID生成（URL 正規化→SHA256）・DB 保存・銘柄抽出・紐付け
  - SSRF / gzip / XML 漏洩対策を実装
- data/calendar_management.py
  - JPX カレンダーの管理（営業日判定, next/prev_trading_day, get_trading_days, calendar_update_job）
- research/*
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 解析ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- strategy/feature_engineering.py
  - research の生ファクターを正規化・フィルタリングして features テーブルへ保存（build_features）
- strategy/signal_generator.py
  - features と ai_scores を組み合わせて最終スコアを計算し signals テーブルへ保存（generate_signals）
  - Bear レジーム抑制、売り（exit）判定（ストップロス等）、BUY/SELL の冪等保存を行う
- data/audit.py
  - シグナル→発注→約定のトレースのための監査テーブル定義・初期化
- data/stats.py
  - zscore_normalize 等の統計ユーティリティ

セットアップ手順
-----------------
前提
- Python 3.10 以上（Union 型 a | b を使用しているため）
- DuckDB（Python パッケージ）、defusedxml（RSS の安全な XML パース）などが必要

例: 仮想環境作成と依存パッケージインストール
1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

（プロジェクトがパッケージ化されている場合）
3. 開発インストール（任意）
   - pip install -e .

環境変数 / .env
- 自動でプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 必須（Config.Settings により required）:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabu ステーション等 API 用パスワード
  - SLACK_BOT_TOKEN       : Slack 通知用 bot token
  - SLACK_CHANNEL_ID      : Slack 通知先 channel id
- 任意（デフォルト値あり）
  - KABUSYS_ENV (development|paper_trading|live) — default: development
  - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
  - DUCKDB_PATH — default: data/kabusys.duckdb
  - SQLITE_PATH — default: data/monitoring.db

例 (.env.example)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（簡易サンプル）
--------------------

1) DB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

2) 日次 ETL 実行（J-Quants トークンは環境変数から取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定することも可
print(result.to_dict())
```

3) 特徴量の構築（build_features）
```python
from datetime import date
from kabusys.strategy import build_features
n = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {n}")
```

4) シグナル生成
```python
from datetime import date
from kabusys.strategy import generate_signals
count = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals written: {count}")
```

5) ニュース収集
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄抽出に使う有効コード集合（任意）
stats = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(stats)
```

6) カレンダー・営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
from datetime import date
print(is_trading_day(conn, date(2024,1,1)))
print(next_trading_day(conn, date(2024,12,30)))
```

注意事項
--------
- J-Quants API 利用時は API レート制限（120 req/min）を守るため内部でスロットリングを行います。
- jquants_client では 401 を受けた場合トークン自動リフレッシュを行い一回リトライします。
- DuckDB への INSERT では冪等性を保つため ON CONFLICT を多用しています。
- news_collector は SSRF / XML DoS (defusedxml) / gzip bomb 対策を実装しています。
- テストや CI で自動 .env ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成
----------------
（重要なファイル・モジュールを抜粋）

src/
  kabusys/
    __init__.py                 # __version__ = "0.1.0"
    config.py                    # 環境変数/設定管理
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント + 保存
      news_collector.py          # RSS -> raw_news / news_symbols
      schema.py                  # DuckDB スキーマ定義 & init_schema
      pipeline.py                # ETL パイプライン（run_daily_etl 等）
      calendar_management.py     # market_calendar 管理・営業日判定
      features.py                # zscore_normalize 再エクスポート
      stats.py                   # 統計ユーティリティ
      audit.py                   # 監査ログ DDL
      ...                        # （raw_executions 等テーブル対応）
    research/
      __init__.py
      factor_research.py         # calc_momentum, calc_volatility, calc_value
      feature_exploration.py     # calc_forward_returns, calc_ic, factor_summary, rank
      ...
    strategy/
      __init__.py
      feature_engineering.py     # build_features
      signal_generator.py        # generate_signals
    execution/                    # 発注層（雛形）
      __init__.py
    monitoring/                   # 監視関連（placeholder）

バージョン情報
--------------
パッケージバージョンは kabusys.__version__（現状: 0.1.0）で参照できます。

サポート / 貢献
----------------
- バグ報告や改善提案はリポジトリの issue にお願いします。
- 新機能追加や修正は PR を送ってください。テストとドキュメントを添付するとスムーズです。

ライセンス
---------
プロジェクトルートにライセンスファイルが含まれる想定です（ここでは明示なし）。リポジトリの LICENSE を参照してください。

補足
----
本 README はソースコード（src/kabusys 以下）をもとに作成しています。各関数・クラスの詳細な仕様は該当モジュールの docstring を参照してください。