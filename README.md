# KabuSys

日本株向けの自動売買フレームワーク（ライブラリ）です。データ取得・ETL、ファクター計算、特徴量生成、シグナル生成、バックテスト、ニュース収集、バックエンド用の DuckDB スキーマなどを含みます。

バージョン: 0.1.0

## 概要
- J-Quants API や RSS フィード等から市場データ・財務データ・ニュースを取得し DuckDB に保存する。
- 研究（research）モジュールでファクターを算出し、strategy 層で特徴量の正規化・合成、シグナル生成を行う。
- バックテストエンジンでポートフォリオシミュレーション（スリッページ・手数料モデル）を実行し、メトリクスを算出。
- ニュース収集・銘柄抽出機能や、ETL の差分取得機能を備えています。
- 発注（execution）層・監視（monitoring）層の土台も用意されています（実装は別途）。

設計方針のポイント:
- ルックアヘッドバイアス回避（target_date 時点の情報のみを利用）
- 冪等性（DB への保存は ON CONFLICT/トランザクションで安全）
- 外部 API 呼び出しはレート制御・リトライを備える
- DuckDB を中心とした単一 DB でデータ層を完結

## 主な機能一覧
- data
  - J-Quants API クライアント（レートリミット・自動トークンリフレッシュ・リトライ）
  - RSS ニュース収集（SSRF 対策・URL 正規化・銘柄抽出）
  - DuckDB スキーマ初期化（init_schema）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
  - 汎用統計ユーティリティ（Z スコア正規化など）
- research
  - ファクター計算（momentum / volatility / value 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- strategy
  - 特徴量作成（build_features: ファクター正規化・ユニバースフィルタ）
  - シグナル生成（generate_signals: final_score 計算、BUY/SELL 判定）
- backtest
  - ポートフォリオシミュレータ（擬似約定・マークツーマーケット）
  - バックテストエンジン（データをコピーして日次シミュレーション）
  - バックテスト CLI（python -m kabusys.backtest.run）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown 等）
- execution / monitoring
  - 発注・モニタリング層のためのパッケージ構成（拡張用）

## 要件（想定）
- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード）

※ requirements.txt はコードベースに含まれていないため、上記を仮定してインストールしてください。

## 環境変数・設定
自動的にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルトデータベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

Settings は kabusys.config.settings からアクセスできます。未設定の必須変数は ValueError を投げます。

## セットアップ手順（基本）
1. レポジトリをクローン
   - git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール（例）
   - pip install duckdb defusedxml

   プロジェクトを editable インストールする場合:
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成し、必要なキーを記載
     例:
       JQUANTS_REFRESH_TOKEN=xxxxx
       SLACK_BOT_TOKEN=xoxb-...
       SLACK_CHANNEL_ID=C01234567
       KABU_API_PASSWORD=...

   - テストや CI では環境変数を直接エクスポートしても可

## 初期 DB 作成（DuckDB）
Python REPL から:
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- conn.close()

":memory:" を指定するとインメモリ DB が作成されます（バックテスト用に便利）。

## 使い方（主要なワークフローと例）

1) データ取得（ETL）
- 株価差分 ETL（例）:
  - from kabusys.data.pipeline import run_prices_etl
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_prices_etl(conn, target_date=<date object>)
  - conn.close()

  （pipeline モジュールは差分取得・バックフィルを行い、jquants_client の save_* を使って冪等に保存します）

2) ニュース収集
- RSS から記事を取得して保存:
  - from kabusys.data.news_collector import run_news_collection
  - conn = init_schema("data/kabusys.duckdb")
  - results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
  - conn.close()

3) 特徴量生成（features テーブルへの書き込み）
- build_features を呼ぶ:
  - from kabusys.strategy import build_features
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - count = build_features(conn, target_date=<date object>)
  - conn.close()

4) シグナル生成（signals テーブルへの書き込み）
- generate_signals を呼ぶ:
  - from kabusys.strategy import generate_signals
  - conn = init_schema("data/kabusys.duckdb")
  - total = generate_signals(conn, target_date=<date object>, threshold=0.6)
  - conn.close()

5) バックテスト
- CLI で実行:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- Python API:
  - from kabusys.backtest.engine import run_backtest
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_backtest(conn, start_date=<date>, end_date=<date>, initial_cash=10_000_000)
  - result.metrics / result.history / result.trades を参照
  - conn.close()

6) J-Quants 直接コール（必要に応じて）
- from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
- data = fetch_daily_quotes(code="7203", date_from=..., date_to=...)
- conn = init_schema("data/kabusys.duckdb")
- save_daily_quotes(conn, data)

## 注意事項 / 実装上のポイント
- jquants_client は API レート制御（120 req/min）とリトライ処理を備えています。401 を検出した際はトークンリフレッシュを行います。
- news_collector は SSRF 対策や gzipped レスポンス検査、受信サイズ制限などを実装しています。
- strategy 層のシグナル生成は市場レジーム（AI の regime_score）を考慮し、Bear 状態では BUY を抑制します。エグジット（SELL）条件にはストップロス等が含まれます。
- バックテストは本番 DB を汚染しないためにデータをインメモリ DB にコピーして実行します。
- 設定は Settings クラス（kabusys.config）経由でアクセスしてください。必須の環境変数が欠けていると例外が発生します。

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下にパッケージが配置されています）

- src/kabusys/
  - __init__.py  (パッケージバージョン等)
  - config.py    (環境変数・設定読み込み)
  - data/
    - __init__.py
    - jquants_client.py       (J-Quants API クライアント)
    - news_collector.py      (RSS ニュース収集)
    - schema.py              (DuckDB スキーマ初期化)
    - pipeline.py            (ETL パイプライン)
    - stats.py               (統計ユーティリティ: zscore_normalize)
  - research/
    - __init__.py
    - factor_research.py     (momentum/volatility/value 等の計算)
    - feature_exploration.py (forward return, IC, summaries)
  - strategy/
    - __init__.py
    - feature_engineering.py (features 作成: 正規化・ユニバースフィルタ)
    - signal_generator.py    (final_score 計算と signals 書き込み)
  - backtest/
    - __init__.py
    - engine.py              (バックテストエンジン)
    - simulator.py           (PortfolioSimulator, TradeRecord, DailySnapshot)
    - metrics.py             (バックテスト評価指標)
    - clock.py               (SimulatedClock)
    - run.py                 (CLI エントリポイント)
  - execution/               (発注層: 空の __init__.py 等。拡張用)
  - monitoring/              (監視層: 拡張用)

## 開発・拡張
- strategy、research、data の各モジュールは比較的独立しているため、ファクター追加やシグナルロジックの変更は局所的に可能です。
- テストを書く際は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化できます。
- DB スキーマは schema.py の DDL を編集して拡張してください（外部キーの一部は DuckDB のバージョン制約のためアプリケーション側で管理する設計になっています）。

---

README に載せるべき追加情報（例: requirements.txt、CI/CD、実運用注意点、ライセンスなど）があれば指示してください。必要に応じてサンプルの .env.example やデプロイ手順も作成します。