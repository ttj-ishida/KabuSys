# KabuSys

日本株自動売買システム（KabuSys）。  
DuckDB をデータレイヤとして用い、J-Quants 等からデータを取得・加工し、特徴量生成、シグナル生成、バックテストを行うためのライブラリ群です。本リポジトリは研究（research）・データパイプライン（data）・戦略（strategy）・バックテスト（backtest）などのモジュールを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発を支援するライブラリセットです。主な目的は以下です。

- J-Quants からの株価・財務・カレンダー等データの取得と DuckDB への保存（ETL）
- 研究用のファクター計算 / 特徴量エンジニアリング
- 正規化済み特徴量と AI スコアを用いたシグナル生成ロジック
- バックテストフレームワーク（シミュレータ、約定モデル、メトリクス）
- RSS ベースのニュース収集・記事と銘柄の紐付け

設計方針としてルックアヘッドバイアス回避、冪等性（ON CONFLICT）、明示的なトランザクション制御、外部依存の最小化を重視しています。

---

## 機能一覧

主な機能（モジュール単位）

- kabusys.config
  - .env / 環境変数自動ロード、必須値チェック、環境フラグ（development/paper_trading/live）
- kabusys.data
  - jquants_client: J-Quants API クライアント（レート制限・リトライ・トークン自動更新、DuckDB への保存機能）
  - news_collector: RSS フェッチ・前処理・raw_news 保存・銘柄抽出・紐付け
  - schema: DuckDB スキーマ定義と init / get_connection
  - pipeline: 差分 ETL の実装（prices / financials / calendar 等）
  - stats: Z スコア正規化ユーティリティ
- kabusys.research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー
- kabusys.strategy
  - feature_engineering.build_features: 正規化・ユニバースフィルタ適用・features テーブルへの書き込み
  - signal_generator.generate_signals: features と ai_scores を統合して BUY/SELL シグナル生成、signals テーブルへの書き込み
- kabusys.backtest
  - engine.run_backtest: 本番 DB からインメモリに必要データをコピーして日次ループでバックテスト実行
  - simulator.PortfolioSimulator: 約定・ポートフォリオ管理（スリッページ・手数料モデル）
  - metrics.calc_metrics: バックテスト指標（CAGR, Sharpe, MaxDD 等）
  - CLI エントリポイント: python -m kabusys.backtest.run

---

## 必要条件 / 依存

- Python 3.10 以上（PEP 604 の型記法（A | B）を使用しているため）
- 必須パッケージ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリ以外のパッケージは最小限。実行環境に応じて以下をインストールしてください。

例（pip）:
pip install duckdb defusedxml

※ 実運用では requirements.txt や Poetry/Poetry.lock に依存関係を明確にすることを推奨します。

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt や pyproject.toml がある場合はそれに従ってください）

4. 環境変数 / .env ファイルを準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` または `.env.local` を置くと自動読み込みされます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須の環境変数（まとめは下記の「環境変数」参照）

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプト内で:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - :memory: を指定するとインメモリ DB（主にテスト／バックテスト）になります。

---

## 環境変数（主なもの）

以下はコード内で参照される主な環境変数です。`.env.example` を作成する際の参考にしてください。

- JQUANTS_REFRESH_TOKEN  （必須） - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      （必須） - kabuステーション API パスワード（発注系を使う場合）
- KABU_API_BASE_URL      （省略可） - デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN        （必須） - Slack 通知用トークン（通知を使う場合）
- SLACK_CHANNEL_ID       （必須） - Slack チャネル ID
- DUCKDB_PATH            - デフォルト data/kabusys.duckdb
- SQLITE_PATH            - 監視用 SQLite（デフォルト data/monitoring.db）
- KABUSYS_ENV            - development / paper_trading / live（デフォルト development）
- LOG_LEVEL              - DEBUG/INFO/...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD - 1 を設定すると自動 .env ロードを無効化

サンプル .env:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な例）

以下はライブラリを使った代表的な操作例です。

1) DB 初期化（最初に一度だけ）
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")

2) J-Quants から株価を取得して保存
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
n = save_daily_quotes(conn, records)

3) 特徴量の構築（features テーブルへ）
from kabusys.strategy import build_features
build_features(conn, target_date=date(2024,1,31))

4) シグナル生成（signals テーブルへ）
from kabusys.strategy import generate_signals
generate_signals(conn, target_date=date(2024,1,31))

5) ニュース収集と銘柄紐付け
from kabusys.data.news_collector import run_news_collection
# known_codes: 有効な銘柄コードセット（抽出用）
results = run_news_collection(conn, known_codes={'7203','6758'})

6) バックテスト実行（CLI）
python -m kabusys.backtest.run \
  --start 2023-01-01 --end 2023-12-31 \
  --cash 10000000 --db data/kabusys.duckdb

またはプログラムから:
from kabusys.backtest.engine import run_backtest
result = run_backtest(conn, start_date, end_date)

戻り値は BacktestResult（history, trades, metrics）です。

注意点:
- generate_signals / build_features は DuckDB 上の所定テーブル（prices_daily, raw_financials, features, ai_scores, positions 等）を参照します。事前に必要データを準備してください。
- ETL は差分更新ロジックを持ちます（pipeline.run_prices_etl 等）。J-Quants API のレート制限に従う必要があります。

---

## 主要 API の説明（抜粋）

- init_schema(db_path)
  - DuckDB の全テーブルを作成して接続を返す（冪等）。

- fetch_daily_quotes / save_daily_quotes
  - J-Quants から日足を取得して raw_prices に保存する。save_* は ON CONFLICT で冪等保存。

- build_features(conn, target_date)
  - research モジュールの生ファクターを取得・正規化して features テーブルへ UPSERT（date 単位で置換）。

- generate_signals(conn, target_date, threshold=0.60, weights=None)
  - features と ai_scores を統合して final_score を計算し BUY/SELL を signals テーブルへ挿入（date 単位置換）。Bear レジーム抑制・エグジット判定を実装。

- run_backtest(conn, start_date, end_date, initial_cash=..., slippage_rate=..., commission_rate=..., max_position_pct=...)
  - 本番 DB からバックテスト用に必要テーブルをインメモリにコピーして日次シミュレーションを実行。PortfolioSimulator を用いた約定モデル、最後に性能指標を返す。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py
    data/
      __init__.py
      jquants_client.py
      news_collector.py
      pipeline.py
      schema.py
      stats.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    strategy/
      __init__.py
      feature_engineering.py
      signal_generator.py
    backtest/
      __init__.py
      engine.py
      simulator.py
      metrics.py
      clock.py
      run.py
    execution/
      __init__.py
    monitoring/   (未実装/プレースホルダ)
    (その他モジュール...)

説明:
- data: データ取得、保存、スキーマ定義、ETL パイプライン、RSS ニュース収集
- research: ファクター計算・解析用関数（研究用途）
- strategy: 戦略用の特徴量生成・シグナル生成
- backtest: バックテストエンジン、シミュレータ、メトリクス
- execution: 発注・実行層（将来的な実装を想定）
- monitoring: 監視系（プレースホルダ）

---

## 開発上の注意事項

- Python 3.10+ を想定しています。型ヒントで | 型結合を使っているため古いバージョンでは動作しません。
- DuckDB の型/制約を活用しているため、スキーマ変更時は注意してマイグレーションしてください。
- J-Quants API 利用時はレート制限とトークン管理に注意（モジュールはレート制御／リトライ／トークン更新を持ちますが、運用側でも監視を推奨）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献 / ライセンス

本 README では貢献手順やライセンスは未定義です。実運用・公開リポジトリ化する際は CONTRIBUTING.md / LICENSE を追加してください。

---

この README はコードベースの主要機能・利用方法を短くまとめたものです。詳細な API ドキュメントや運用手順（J-Quants トークン発行、kabuステーションの設定、Slack 通知設定、運用時の監視ルール等）は別途作成することを推奨します。