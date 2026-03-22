# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（軽量なデータレイヤ、ファクター開発、シグナル生成、バックテスト等を含む）。

このリポジトリは DuckDB をデータストアに使い、J-Quants からのデータ取り込み、ニュース収集、特徴量生成、シグナル生成、擬似約定によるバックテストを行えるよう設計されています。

---

## 主な機能

- データ取得・ETL
  - J-Quants API クライアント（差分取得・ページネーション・リトライ・レート制御）
  - RSS ベースのニュース収集（SSRF 対策、トラッキングパラメータ除去、記事ID生成）
  - DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）

- データ処理 / 研究
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - クロスセクション Z スコア正規化、ファクター探索（IC、統計サマリー、将来リターン）

- 戦略
  - 特徴量エンジニアリング（build_features）
  - シグナル生成（generate_signals）：AIスコア統合、レジームフィルタ、BUY/SELL 生成

- バックテスト
  - 日次ループベースのバックテスト実行（擬似約定、スリッページ・手数料モデル）
  - ポートフォリオシミュレータ（PortfolioSimulator）
  - バックテストメトリクス計算（CAGR, Sharpe, MaxDD, WinRate 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）

- 実行層（execution）用の基盤（スキーマ等を含む）。実際の発注ロジックは層をまたがらないよう分離設計。

---

## 動作要件

- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - defusedxml

インストール例:
- 仮想環境作成後:
  - pip install duckdb defusedxml
- 開発時: pip install -e .

（プロジェクトに requirements.txt があればそれに従ってください）

---

## 環境変数 / 設定

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（モジュール: `kabusys.config`）。

重要な環境変数（必須）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注実装時に使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

その他（既定値あり）
- KABUSYS_ENV           : `development` / `paper_trading` / `live`（既定: development）
- LOG_LEVEL             : `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`（既定: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（既定: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : `1` を設定すると自動 .env 読み込みを無効化

.env の読み込み順序:
1. OS 環境変数（優先）
2. .env.local（存在すれば上書き）
3. .env（存在すれば読み込み）

`kabusys.config.settings` から設定を参照できます:
- 例: from kabusys.config import settings; settings.jquants_refresh_token

---

## セットアップ手順（ざっくり）

1. リポジトリをクローンして仮想環境を作る
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml

3. 環境変数を設定する
   - プロジェクトルートに `.env` を作り、必要なキーを設定する（.env.example を参考にしてください）

4. DuckDB スキーマを初期化
   - Python REPL またはスクリプトから:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")
     - conn.close()

   - あるいはコード内で `init_schema(settings.duckdb_path)` を呼ぶ

---

## 使い方（主要ユースケース）

- データベース初期化（Python）
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- J-Quants から株価を取得して保存（手動呼び出し例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - records = fetch_daily_quotes(date_from=..., date_to=...)
  - save_daily_quotes(conn, records)

- ニュース収集ジョブ実行
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes=set_of_codes)

- ETL パイプライン（prices / financials / calendar 等）
  - Data pipeline モジュール内の関数を利用（run_prices_etl など）
  - 例: from kabusys.data.pipeline import run_prices_etl
    - run_prices_etl(conn, target_date)

  （pipeline モジュールは差分取得・バックフィル・品質チェックを実装しています）

- 特徴量構築（features テーブルへの書き込み）
  - from kabusys.strategy import build_features
  - build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成（signals テーブルへの書き込み）
  - from kabusys.strategy import generate_signals
  - generate_signals(conn, target_date=date(2024, 1, 31), threshold=0.6)

- バックテスト（Python API）
  - from kabusys.data.schema import init_schema
  - from kabusys.backtest.engine import run_backtest
  - conn = init_schema("data/kabusys.duckdb")  # or get_connection for existing DB
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
  - result.history / result.trades / result.metrics

- バックテスト（CLI）
  - python -m kabusys.backtest.run --start YYYY-MM-DD --end YYYY-MM-DD --db path/to/kabusys.duckdb
  - 追加オプション: --cash, --slippage, --commission, --max-position-pct

---

## API 概要（主要モジュール）

- kabusys.config
  - Settings オブジェクト経由で環境設定を取得

- kabusys.data
  - jquants_client: J-Quants API 取得・保存（save_daily_quotes, save_financial_statements, save_market_calendar）
  - news_collector: RSS 取得と raw_news / news_symbols 保存（fetch_rss, save_raw_news, run_news_collection）
  - schema: DuckDB スキーマ定義 / init_schema / get_connection
  - stats: zscore_normalize 等の統計ユーティリティ
  - pipeline: 差分 ETL ロジック（run_prices_etl 等）

- kabusys.research
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.strategy
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, threshold, weights)

- kabusys.backtest
  - engine.run_backtest(conn, start_date, end_date, ...)
  - simulator.PortfolioSimulator（擬似約定）
  - metrics.calc_metrics

- kabusys.data.jquants_client の注意点
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュを実装
  - 取得データは fetched_at（UTC）で記録し、Look-ahead バイアスを抑止

---

## ディレクトリ構成

（重要なファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + 保存関数
    - news_collector.py      — RSS 収集・保存
    - schema.py              — DuckDB スキーマ定義 / init_schema
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - pipeline.py            — ETL パイプライン（差分取得等）
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC / forward return / summary
  - strategy/
    - __init__.py
    - feature_engineering.py — features テーブル構築（正規化・フィルタ）
    - signal_generator.py    — final_score の計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py              — 日次ループのバックテストエンジン
    - simulator.py           — PortfolioSimulator（擬似約定）
    - metrics.py             — バックテスト評価指標計算
    - run.py                 — CLI エントリポイント
    - clock.py               — 模擬時計（将来拡張）
  - execution/               — 発注・実行層（パッケージ化済み; 実実装を追加する想定）
  - monitoring/              — 監視・メトリクス用（例: sqlite 用コード）
  - backends / その他: 実運用で拡張するためのモジュール群

---

## 開発・拡張時の注意点

- Look-ahead バイアスに注意
  - ファクター計算 / シグナル生成は target_date 時点の利用可能データのみを参照する設計になっています。コード内のコメント（各モジュールの設計方針）を遵守してください。

- DuckDB スキーマは冪等（idempotent）に作られているため、init_schema を何度呼んでも安全です。

- ニュース収集は SSRF 対策・XML の安全パース（defusedxml）を行っています。外部ネットワークの取り扱いについてはログおよび設定で監視してください。

---

## 参考コマンド例

- DB 初期化:
  - python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- バックテスト（CLI）:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- Python から特徴量→シグナル生成:
  - from datetime import date
    from kabusys.data.schema import init_schema
    from kabusys.strategy import build_features, generate_signals
    conn = init_schema('data/kabusys.duckdb')
    build_features(conn, date(2024,1,31))
    generate_signals(conn, date(2024,1,31))
    conn.close()

---

必要であれば、README に含める具体的な .env.example のテンプレートや、CI / デプロイ手順、ロギング設定の例、単体テスト手順なども作成します。どの項目を優先して追加しますか？