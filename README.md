# KabuSys

KabuSys は日本株を対象とした自動売買システムのコアライブラリです。データ取得（J-Quants 等）、データパイプライン、特徴量作成、シグナル生成、バックテストフレームワーク、ニュース収集などを含むモジュール群を提供します。設計方針として「ルックアヘッドバイアスの排除」「冪等性」「テスト容易性」を重視しています。

---

## 主な機能（概要）

- データ取得
  - J-Quants API クライアント（レートリミット・リトライ・トークン自動更新対応）
  - RSS ベースのニュース収集（SSRF/サイズ上限/トラッキング除去対応）
- データ基盤
  - DuckDB スキーマ定義・初期化（init_schema）
  - 生データ / 加工データ / 特徴量 / 実行レイヤーのテーブル設計
- ETL / パイプライン
  - 差分取得・バックフィル・品質チェックを意識した ETL 実装（pipeline モジュール）
- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 特徴量・シグナル
  - 特徴量作成（Z スコア正規化・ユニバースフィルタ等）
  - シグナル生成（コンポーネントスコア統合・Bear レジーム抑制・エグジット判定）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ / 手数料モデル）
  - バックテストエンジン（in-memory DuckDB コピーで本番 DB を汚さない）
  - メトリクス計算（CAGR / Sharpe / MaxDD / 勝率等）
- 実行 / 監視（骨格）
  - execution / monitoring 層のための基本構成（発展用途向け）

---

## 要件

- Python 3.10 以上（Union 型注記や新しい構文を使用）
- 主要依存パッケージ（最低限）:
  - duckdb
  - defusedxml

必要に応じて他の標準ライブラリ外パッケージが増える可能性があります（例: requests 等）。環境に合わせて pip で追加してください。

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   （パッケージ群を requirements.txt にまとめている場合はそちらを利用してください）

4. パッケージを開発モードでインストール（任意）
   - pip install -e .

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

   - あるいはインメモリでテスト:
     init_schema(":memory:")

---

## 環境変数 / 設定 (.env)

`kabusys.config.Settings` が参照する主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")（デフォルト: INFO）

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例（.env）:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（代表的な利用方法）

- DuckDB スキーマ作成（スクリプト例）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

- J-Quants から株価を取得して保存（概念例）
  from kabusys.data import jquants_client as jq
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)

- ETL（パイプライン）呼び出し（概念例）
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_prices_etl
  conn = init_schema("data/kabusys.duckdb")
  result = run_prices_etl(conn, target_date=date.today())
  # ETLResult オブジェクト: result.prices_saved 等を参照

- 特徴量作成
  from kabusys.strategy import build_features
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 31))

- シグナル生成
  from kabusys.strategy import generate_signals
  generate_signals(conn, target_date=date(2024, 1, 31))

- バックテスト（CLI）
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

  バックテスト API（プログラム呼出し）:
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10000000)

- ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", ...}  # 有効銘柄リスト
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

---

## よく使う API（簡易一覧）

- kabusys.config.settings — 環境設定アクセス
- kabusys.data.schema.init_schema(db_path) — DuckDB スキーマ初期化
- kabusys.data.jquants_client — J-Quants 取得 / 保存関数群
- kabusys.data.pipeline.run_prices_etl — 株価 ETL（差分取得）
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection — RSS 収集
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic — 研究用ユーティリティ
- kabusys.strategy.build_features — 特徴量作成
- kabusys.strategy.generate_signals — シグナル生成
- kabusys.backtest.run_backtest / backtest.run CLI — バックテスト実行
- kabusys.backtest.simulator.PortfolioSimulator — 約定・ポートフォリオ管理（シミュレータ）

各関数は README のサンプルを参照して DuckDB 接続と日付を渡して使います。多くの関数は冪等（同一日付での再実行）を前提に設計されています。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / 保存ロジック
    - news_collector.py          — RSS 収集・前処理・DB 保存
    - schema.py                  — DuckDB スキーマ定義・初期化
    - stats.py                   — z-score 正規化等の統計ユーティリティ
    - pipeline.py                — ETL パイプライン（差分取得等）
  - research/
    - __init__.py
    - factor_research.py         — ファクター計算（momentum/volatility/value）
    - feature_exploration.py     — IC / 将来リターン / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py     — ファクター正規化・features 書込
    - signal_generator.py        — final_score 計算・signals 書込
  - backtest/
    - __init__.py
    - engine.py                  — バックテストエンジン（メインループ）
    - simulator.py               — ポートフォリオ・約定シミュレータ
    - metrics.py                 — バックテスト評価指標計算
    - run.py                     — CLI エントリポイント
    - clock.py                   — 模擬時計（将来拡張用）
  - execution/                   — 発注 / 実行層（パッケージ骨格）
  - monitoring/                  — 監視用モジュール（骨格）

---

## 注意事項 / 実運用に向けた留意点

- 環境変数（トークン等）は厳重に管理してください。README の .env 例はサンプルです。
- J-Quants API のレート制限や HTTP エラーに対する挙動は jquants_client に実装されていますが、API仕様変更に注意してください。
- DuckDB のファイルパスはバックアップ・排他制御を検討してください（複数プロセスの同時書き込み等）。
- テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env 読み込みを無効にできます。
- 一部の機能（例えば監視・実際の発注）は本リポジトリでは骨格実装または未実装の箇所があります。実運用時は追加の安全機構（注文検証・二重確認・接続監視等）を実装してください。

---

この README はコードベースの主要機能と使い方の概要を示しています。詳細な設計仕様（StrategyModel.md、DataPlatform.md、BacktestFramework.md 等）や追加の利用例は別途ドキュメントを参照してください。必要であれば README にサンプルスクリプトやより詳しいセットアップ手順（Docker / systemd / scheduler 連携など）を追加します。