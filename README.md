KabuSys — 日本株自動売買基盤
=========================

概要
----
KabuSys は日本株向けのデータプラットフォームと戦略層を備えた自動売買基盤のライブラリです。本リポジトリは以下の主要要素を含みます。

- データ層: J-Quants からの株価・財務・市場カレンダー・ニュース収集、DuckDB スキーマ定義と ETL パイプライン
- 研究（research）層: ファクター計算・特徴量探索ユーティリティ
- 戦略（strategy）層: 特徴量の正規化・合成（build_features）、シグナル生成（generate_signals）
- 実行（execution）・監査（audit）に関するスキーマとユーティリティ（発注は API 層で実装）
- ニュース収集（news_collector）と電文前処理（SSRF・XML 安全対策など）

主な機能
--------
- J-Quants API クライアント（ページネーション、トークン自動更新、レート制御、リトライ）
- DuckDB による永続データスキーマ（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェックフック）
- ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 特徴量構築（Z スコア正規化・ユニバースフィルタ）
- シグナル生成（コンポーネントスコアの統合、BUY/SELL 生成、Bear レジーム抑制、エグジット判定）
- ニュース RSS 収集（XML 安全パース、URL 正規化、記事→銘柄紐付け）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day）

セットアップ
-----------

前提
- Python 3.9+（typing の一部構文を使用）
- DuckDB を使用（duckdb Python パッケージ）
- defusedxml（RSS/XML の安全パース）

ローカル開発の最低手順例
1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトを packaging する場合は requirements.txt / pyproject.toml に追加してください）

3. 環境変数を設定（.env）
   プロジェクトルートの .env または OS 環境変数で次の必須キーを設定してください:

   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - SLACK_BOT_TOKEN=<your_slack_bot_token>
   - SLACK_CHANNEL_ID=<your_slack_channel_id>
   - KABU_API_PASSWORD=<kabu_station_api_password>  # 発注連携を行う場合
   - (任意) KABUSYS_ENV=development|paper_trading|live
   - (任意) LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

   設定読み込み:
   - kabusys.config はプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。
   - テストなどで自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（簡易サンプル）
--------------------

以下は Python REPL / スクリプトでの基本的な利用例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# デフォルト DB パスは settings.duckdb_path（デフォルト: data/kabusys.duckdb）
conn = init_schema(settings.duckdb_path)
# 既存 DB に接続するだけなら:
# conn = get_connection(settings.duckdb_path)
```

2) 日次 ETL 実行（株価 / 財務 / カレンダー を差分取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を明示したい場合は日付オブジェクトを渡す
print(result.to_dict())
```

3) 特徴量構築（features テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import build_features

count = build_features(conn, target_date=date(2024, 1, 31))
print(f"features upserted: {count}")
```

4) シグナル生成（signals テーブルへ書き込み）
```python
from datetime import date
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date(2024, 1, 31))
print(f"signals generated: {n}")
```

5) ニュース収集ジョブ（RSS 収集→raw_news 保存→銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes

known_codes = {"7203", "6758", ...}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

6) カレンダー夜間更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"market_calendar saved: {saved}")
```

主要 API（エントリポイント）
----------------------------
- kabusys.config.settings — 環境変数経由の設定アクセス
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ作成と接続取得
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL の実行
- kabusys.data.jquants_client.* — J-Quants からのフェッチ & DuckDB 保存関数（fetch_* / save_*）
- kabusys.data.news_collector.run_news_collection(...) — RSS 収集ジョブ
- kabusys.data.calendar_management.* — 営業日判定・更新ジョブ
- kabusys.research.* — factor 計算・探索ユーティリティ（calc_momentum 等）
- kabusys.strategy.build_features / generate_signals — 特徴量構築・シグナル生成

ディレクトリ構成（主なファイル）
-----------------------------
以下は src/kabusys 配下の主要モジュールと役割の概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（フェッチ + 保存）
    - news_collector.py      — RSS ニュース収集と保存
    - schema.py              — DuckDB スキーマ定義 / 初期化
    - stats.py               — zscore_normalize など統計ユーティリティ
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - audit.py               — 監査ログ向けスキーマ / DDL
    - features.py            — 公開インターフェース（zscore_normalize の再エクスポート）
  - research/
    - __init__.py
    - factor_research.py     — モメンタム／ボラ／バリュー計算
    - feature_exploration.py — 将来リターン・IC 計算、統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py — features の構築（正規化・ユニバースフィルタ等）
    - signal_generator.py    — final_score 計算と BUY/SELL 生成
  - execution/               — 発注・実行関連のパッケージ（雛形）
  - monitoring/              — 監視用ユーティリティ（存在する場合）

設計上の注意点 / 動作ポリシー
----------------------------
- ルックアヘッドバイアス対策: 戦略・研究モジュールは target_date 時点のデータのみを参照する設計です。
- 冪等性: DB への保存は ON CONFLICT / トランザクションを用いて冪等性を確保します。
- ネットワーク安全: RSS の取得は SSRF 対策やデータサイズ上限、defusedxml を使用した安全パースを行っています。
- 設定の自動読み込み: .env / .env.local はプロジェクトルートから自動読み込みされます（無効化可）。

環境変数（主要）
----------------
必須:
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

推奨 / デフォルトあり:
- KABU_API_PASSWORD
- KABUSYS_ENV (development / paper_trading / live) — デフォルト development
- LOG_LEVEL — デフォルト INFO
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db

貢献と拡張
-----------
- 戦略の重みや閾値は generate_signals の引数で上書き可能です（weights, threshold）。
- 発注実装は execution 層と証券会社 API ラッパーを追加して連携してください。
- テストは設定自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると環境依存を避けられます。

ライセンス
----------
（ここにライセンス情報を記載してください。README に記載がない場合はリポジトリの LICENSE を参照してください）

最後に
------
この README はコードベースの主要な利用方法をまとめたものです。より詳細な仕様（StrategyModel.md、DataPlatform.md 等）や運用手順書が別途あることを想定しています。必要であれば README にサンプルの .env.example、docker / systemd の運用例、CI テスト手順などを追加できます。希望があればその内容を追記します。