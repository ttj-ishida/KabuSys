# KabuSys

日本株向けの自動売買・データプラットフォームコンポーネント群です。  
価格データ収集、財務データ取得、ニュース収集、特徴量生成、シグナル生成、バックテスト、ETL パイプラインなど、実運用に近い設計方針で実装されています。

主な対象は DuckDB をデータストアとして用いる研究・バックテスト・運用前段階のワークフローです。

---

## 概要

KabuSys は次のレイヤーを含むモジュール群を提供します。

- データ取得・保存（J-Quants クライアント、RSS ニュース収集、DuckDB スキーマ + 保存関数）
- ETL パイプライン（差分収集、品質チェックのフック）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量エンジニアリング（正規化・クリップ・features テーブルへの反映）
- シグナル生成（特徴量 + AI スコアを統合して BUY/SELL を生成）
- バックテストフレームワーク（シミュレータ、メトリクス、エンジン）
- ニュース処理（RSS 取得、正規化、記事保存、銘柄抽出）

設計上の特徴：
- ルックアヘッドバイアス対策（target_date 時点のデータのみを使用）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで実装）
- 外部 API 呼び出しは data 層に限定し、strategy/ backtest 層は API に依存しない
- DuckDB を用いたローカル高速分析・バックテストに最適化

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local からの自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN 等）
- kabusys.data.jquants_client
  - J-Quants API からの株価 / 財務データ / カレンダー取得（レート制御・リトライ・トークン自動更新）
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar 等）
- kabusys.data.news_collector
  - RSS 取得、URL 正規化、記事ID 生成、raw_news / news_symbols への保存
  - SSRF / Gzip サイズ / XML Bomb 対策を備えた実装
- kabusys.data.schema
  - DuckDB のスキーマ定義と init_schema(db_path) による初期化
- kabusys.data.pipeline
  - 差分 ETL（差分取得、backfill の取り扱い、品質チェックフック）
- kabusys.research.factor_research / feature_exploration
  - momentum / volatility / value などファクターの計算
  - 将来リターン計算、IC（Spearman）や統計サマリ
- kabusys.strategy.feature_engineering
  - ファクターの統合・Z スコア正規化・ユニバースフィルタ・features への UPSERT
- kabusys.strategy.signal_generator
  - features と ai_scores を統合して final_score を算出、BUY/SELL シグナル生成（冪等）
  - Bear レジーム時の BUY 抑制、SELL のエグジット条件（ストップロス等）
- kabusys.backtest
  - PortfolioSimulator（擬似約定、スリッページ・手数料モデル）
  - run_backtest（本番 DB からデータをコピーして日次シミュレーション）
  - metrics（CAGR / Sharpe / MaxDD / WinRate / Payoff 等）
  - CLI エントリーポイント: python -m kabusys.backtest.run

---

## 要件（推奨）

- Python 3.10 以上（型ヒントに | 演算子等を使用）
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, logging 等）を広く使用

（プロジェクトに requirements.txt があればそちらを使用してください）

---

## 環境変数

重要な環境変数（config.Settings で参照）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（省略時 default: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, ...、デフォルト INFO）

自動読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順

1. Python の準備
   - 推奨: Python 3.10 以上をインストール

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install duckdb defusedxml
   - あるいはプロジェクトに requirements.txt があれば pip install -r requirements.txt
   - 開発インストール: pip install -e .

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - :memory: を指定すればインメモリ DB が作成されます（テスト用）

5. 環境変数設定
   - .env をプロジェクトルートに作成し、必須変数を設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=あなたのトークン
     KABU_API_PASSWORD=xxxxxxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

---

## 使い方（代表的なワークフロー）

以下は主要ユースケースの簡単な例です。

1) DuckDB スキーマを初期化
- Python:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

2) データ収集（J-Quants）
- J-Quants の株価や財務データを取得して保存:
  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)

3) RSS ニュース収集
- fetch_rss / save_raw_news:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)

4) ETL（差分更新）
- pipeline モジュールを利用して差分 ETL を実行（例: run_prices_etl）
  from kabusys.data.pipeline import run_prices_etl
  fetched, saved = run_prices_etl(conn, target_date=date.today())

5) 特徴量の構築
- DuckDB 接続と対象日を渡して features を構築:
  from kabusys.strategy import build_features
  count = build_features(conn, target_date=date(2024, 1, 5))

6) シグナル生成
- features / ai_scores / positions を参照して signals を生成:
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, target_date=date(2024, 1, 5))

7) バックテスト実行（CLI 例）
- DB を事前に用意し、prices_daily / features / ai_scores / market_regime / market_calendar を入れておく:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb

- または Python から run_backtest を直接呼ぶ:
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date)

結果: BacktestResult（history, trades, metrics）が返ります。metrics により CAGR / Sharpe / MaxDD / Trades 等を確認できます。

---

## 主要 API（抜粋）

- kabusys.data.schema.init_schema(db_path)
  - DB 初期化（テーブル作成、インデックス作成）
- kabusys.data.jquants_client.fetch_daily_quotes(...)
  - J-Quants から OHLCV を取得（ページネーション対応）
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
  - raw_prices への冪等保存
- kabusys.data.news_collector.fetch_rss(url, source)
  - RSS フィードの取得と記事パース
- kabusys.data.news_collector.save_raw_news(conn, articles)
  - raw_news テーブルへ挿入
- kabusys.data.pipeline.run_prices_etl(...)
  - 差分 ETL（差分取得 → 保存 → 品質チェック）
- kabusys.research.calc_momentum / calc_volatility / calc_value
  - ファクター計算
- kabusys.strategy.build_features(conn, target_date)
  - features テーブルへ特徴量を整備して書き込む
- kabusys.strategy.generate_signals(conn, target_date, threshold=?, weights=?)
  - signals テーブルへ BUY/SELL を書き込む
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...)
  - 日次バックテストを実行して結果を返す

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイルと内容の概略です。

- src/kabusys/
  - __init__.py
  - config.py                   - 環境変数管理（.env 自動読込）
  - data/
    - __init__.py
    - jquants_client.py         - J-Quants API クライアント、保存関数
    - news_collector.py         - RSS 収集・記事解析・DB 保存
    - pipeline.py               - ETL パイプライン（差分取得等）
    - schema.py                 - DuckDB スキーマ定義と初期化
    - stats.py                  - Z スコア正規化等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py        - momentum/volatility/value の計算
    - feature_exploration.py    - forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py    - 正規化・ユニバースフィルタ・features 反映
    - signal_generator.py       - final_score 計算・BUY/SELL 生成
  - backtest/
    - __init__.py
    - engine.py                 - run_backtest / エンジンループ
    - simulator.py              - PortfolioSimulator（擬似約定）
    - metrics.py                - バックテスト評価指標
    - clock.py                  - SimulatedClock（将来拡張用）
    - run.py                    - CLI エントリーポイント

---

## 注意事項 / 運用上のポイント

- 環境変数の管理:
  - .env/.env.local をプロジェクトルートに配置して自動ロードされます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
- DuckDB のファイルパスは既定で data/kabusys.duckdb です。適切なディレクトリと権限を用意してください。
- ニュース収集では外部リソースを取得するため、ネットワークの安全性（SSRF 対策）や取得サイズの制限が実装されています。RSS ソースの追加や既知銘柄コードの指定は明示的に行ってください。
- 実運用での発注・実行（kabuステーション接続等）は execution 層に対応する実装が必要です（本コードベースは基盤・戦略・バックテストが中心）。
- 本リポジトリの設計は外部仕様書（StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）に準拠した実装を目指しています。実運用前に仕様を確認してください。

---

もし README に追加したい内容（例: サンプル .env.example、CI / テスト手順、より詳細な API 仕様など）があれば教えてください。必要に応じて追記します。