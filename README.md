# KabuSys

日本株向けの自動売買 / 研究基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集、簡易シミュレーションなどのコンポーネントを備えています。

主な設計方針は「ルックアヘッドバイアスの排除」「DBへの冪等保存」「テスト容易性（依存注入）」です。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（例）
- ディレクトリ構成（主要ファイルの説明）
- 環境変数一覧 / .env の例
- 補足 / 注意事項

---

## プロジェクト概要

KabuSys は日本株の定量戦略を構築・運用するための社内向けライブラリ群です。主な役割は次のとおりです。

- J-Quants API からの市場データ・財務データ取得と DuckDB への保存（冪等）
- ETL パイプラインによる差分更新・品質チェック
- 研究モジュール（ファクター計算、探索用関数）
- 特徴量（features）作成と正規化
- シグナル生成（BUY / SELL）ロジック（重み・レジーム考慮）
- バックテストエンジン（シミュレーション・パフォーマンス指標）
- ニュース収集（RSS）と銘柄紐付け
- DuckDB ベースのスキーマ定義・初期化

設計上、発注 API（実注文を送る層）への直接依存を持たないモジュールが多く、ロジックの検証・バックテストを安全に行えるようになっています。

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント（レート制限、再試行、トークン自動リフレッシュ、ページネーション対応）
  - raw_prices / raw_financials / market_calendar の取得と DuckDB への冪等保存
- data/pipeline.py
  - 差分 ETL（最終取得日からの差分取得、backfill 対応、品質チェックフック）
- data/schema.py
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema(db_path) で初期化可能（:memory: サポート）
- data/news_collector.py
  - RSS から記事を収集、正規化、raw_news 保存、銘柄コード抽出・紐付け（SSRF対策・XML攻撃対策）
- research/*
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算 / IC（Spearman） / 統計サマリー
- strategy/feature_engineering.py
  - research で計算した生ファクターを正規化（Zスコア）、ユニバースフィルタ適用、features テーブルへ UPSERT
- strategy/signal_generator.py
  - features と ai_scores を合成して final_score を計算、BUY/SELL シグナル生成（Bear レジーム抑制、売却ルール含む）
- backtest/*
  - run_backtest: 本番 DB からインメモリ DuckDB に必要データをコピーして日次シミュレーション
  - PortfolioSimulator：擬似約定ロジック（スリッページ・手数料モデル）
  - metrics: CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio 等の計算
  - CLI: python -m kabusys.backtest.run によりバックテストを実行可能
- config.py
  - 環境変数管理（.env 自動ロード、必須チェック、環境判定、ログレベル等）

共通の設計特徴：
- DuckDB を主要なローカル DB として使用
- 冪等性を重視（ON CONFLICT / INSERT ... DO UPDATE / DO NOTHING）
- ルックアヘッドバイアス防止（target_date 時点のみ参照等）
- テストしやすい依存注入パターン（id_token など注入可能）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 型等を利用）
- Git リポジトリのルートに移動して作業することを想定

1. リポジトリをクローン（省略）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 必須（少なくとも以下をインストールしてください）:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml

   （プロジェクトによる追加依存があれば requirements.txt を用意している場合はそちらを利用してください。）

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   - :memory: を使った一時 DB も可能:
     - from kabusys.data.schema import init_schema; init_schema(':memory:')

5. 環境変数の設定
   - .env または .env.local をプロジェクトルートに置くと自動ロードされます（config.py により自動読み込み）。
   - 必須の環境変数（下記参照）を設定してください。

---

## 使い方（簡易ガイド）

いくつかの主要なユースケース例を示します。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema('data/kabusys.duckdb')
conn.close()
```

2) J-Quants から株価日足を取得して保存
```
from kabusys.data import jquants_client as jq
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')
records = jq.fetch_daily_quotes(date_from=...)   # id_token は settings を利用
saved = jq.save_daily_quotes(conn, records)
conn.close()
```

3) ETL（差分株価取得）の実行（pipeline）
- pipeline モジュールは差分更新ロジックを提供します（run_prices_etl 等）。usage の一例：
```
from kabusys.data.pipeline import run_prices_etl
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema('data/kabusys.duckdb')
result = run_prices_etl(conn, target_date=date.today())
# ETLResult を参照して結果確認
conn.close()
```
（詳細な引数や戻り値は pipeline.py を参照してください）

4) 特徴量作成 / シグナル生成
```
from kabusys.strategy import build_features, generate_signals
from kabusys.data.schema import init_schema
from datetime import date

conn = init_schema('data/kabusys.duckdb')
n_features = build_features(conn, target_date=date(2024, 1, 31))
n_signals = generate_signals(conn, target_date=date(2024, 1, 31))
```

5) バックテスト CLI
リポジトリルートで次のように実行できます:
```
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2024-12-31 \
  --cash 10000000 --db data/kabusys.duckdb
```
実行後、CAGR / Sharpe / MaxDD / WinRate / Payoff 等が表示されます。

6) ニュース収集（RSS）
```
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema('data/kabusys.duckdb')
res = run_news_collection(conn, sources=None, known_codes=set(['7203','6758']))
```

---

## ディレクトリ構成（主要ファイルの説明）

src/kabusys/
- __init__.py — パッケージ定義（version, export）
- config.py — 環境変数・設定管理（.env 自動読み込み、必須チェック）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント + 保存ユーティリティ（rate limit / retry / token refresh）
  - news_collector.py — RSS 収集・正規化・DB 保存（SSRF / XML 対策）
  - pipeline.py — ETL 差分更新ロジック（backfill、品質チェックフック）
  - schema.py — DuckDB スキーマ定義と init_schema()
  - stats.py — 共通統計ユーティリティ（zscore_normalize 等）
- research/
  - __init__.py
  - factor_research.py — momentum / volatility / value の生ファクター計算
  - feature_exploration.py — 将来リターン / IC / factor_summary / rank
- strategy/
  - __init__.py
  - feature_engineering.py — 生ファクターの正規化・ユニバースフィルタ・features 保存
  - signal_generator.py — final_score 計算・BUY/SELL シグナル生成
- backtest/
  - __init__.py
  - engine.py — run_backtest の実装（インメモリ DB を使った日次ループ）
  - simulator.py — PortfolioSimulator（擬似約定・mark_to_market）
  - metrics.py — バックテスト評価指標計算
  - clock.py — SimulatedClock（将来的な拡張用）
  - run.py — CLI エントリポイント（python -m kabusys.backtest.run）
- execution/ — （将来の発注実装用、現状空のパッケージ）
- monitoring/ — （監視関連のモジュールを配置予定）

---

## 環境変数（必須 / 主要）

config.Settings で参照される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション等の API パスワード（execution 層で利用）
- SLACK_BOT_TOKEN — Slack 通知用（監視 / alerting 用）
- SLACK_CHANNEL_ID — Slack チャンネル ID

オプション / デフォルトあり:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

例 (.env)
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を自動検出して .env / .env.local を読み込みます。

---

## 補足 / 注意事項

- Python バージョン: 本コードは Python 3.10+ を想定しています（PEP 604 union 型など）。
- DuckDB: 大量データを扱うため duckdb を利用しています。初期化は必ず init_schema を利用してください。
- 冪等性: jquants_client.save_* / news_collector.save_raw_news 等は冪等設計（ON CONFLICT / RETURNING）です。
- セキュリティ: news_collector は SSRF・XML Bomb 等の対策を含みますが、公開環境での運用時はさらに検討してください。
- テスト: 各モジュールは依存注入（id_token, conn など）に配慮しており、ユニットテストが容易です。
- 実運用: execution 層（実際の発注）や監視機能は別途実装・レビューが必要です。Live 環境では十分なリスク管理を行ってください。

---

この README はリポジトリ内のコード（src/kabusys 以下）を基に作成しています。各モジュールの詳細な使い方や設定（品質チェックルール、StrategyModel のパラメータ等）は該当するドキュメント（StrategyModel.md / DataPlatform.md / BacktestFramework.md 等）またはソース内の docstring を参照してください。