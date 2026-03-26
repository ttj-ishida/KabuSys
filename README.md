KabuSys — 日本株自動売買プラットフォーム（README）
=====================================

概要
----
KabuSys は日本株のデータ取得、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集などを含む自動売買／研究用のコードベースです。本リポジトリは以下の主要機能をモジュール化して提供します。

主な特徴
--------
- データ取得
  - J-Quants API 経由で日足（OHLCV）、財務データ、上場情報、マーケットカレンダーを取得（jquants_client）。
- データ ETL / 保存
  - DuckDB に対する冪等的な保存関数（raw_prices、raw_financials、market_calendar など）。
- 特徴量エンジニアリング
  - research モジュールで momentum / volatility / value 系ファクターを計算し、features テーブルへ保存（feature_engineering）。
- シグナル生成
  - 正規化済みファクターと AI スコアを統合して買い・売りシグナルを作成（signal_generator）。
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）、リスク調整（セクター制限／レジーム乗数）、株数決定（position_sizing）。
- バックテスト
  - インメモリ DuckDB を使った完全なバックテスト実行ループ（engine.run_backtest）。スリッページ／手数料モデル、約定ロジックを備えたシミュレータ。
- ニュース収集
  - RSS フィードを安全に収集・正規化して raw_news / news_symbols に保存（news_collector）。
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート基準）、必須環境変数チェック（config.Settings）。

サポート機能（設計上のポイント）
- Look-ahead bias を避ける設計（取得時刻の記録、target_date ベースの計算）
- 冪等性を考慮した DB 更新（ON CONFLICT / トランザクション）
- リトライ・レートリミット実装（J-Quants クライアント）
- SSRF や XML 攻撃対策（news_collector）


セットアップ
-----------
前提
- Python 3.10 以上（コード内の型アノテーションで | を使用）
- DuckDB を使用（duckdb Python パッケージ）
- defusedxml（ニュース XML の安全パース）

推奨手順（UNIX 系の例）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成/有効化
   - python -m venv .venv
   - source .venv/bin/activate
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ管理用 requirements.txt があれば pip install -r requirements.txt）
4. パッケージをインストール（開発モード）
   - pip install -e .
5. 環境変数を設定
   - プロジェクトルートに .env（または .env.local）を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
   - オプション／デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — デフォルト data/monitoring.db

使い方（代表例）
----------------

1) バックテスト実行（CLI）
- 準備: DuckDB に必要テーブル（prices_daily / features / ai_scores / market_regime / market_calendar など）が整っていること。
- 実行例:
  - python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db data/kabusys.duckdb
- オプションで slippage、commission、allocation-method（equal|score|risk_based）等を指定可能。
- 実行結果として標準出力に CAGR / Sharpe / MaxDD / WinRate / Trades 等が表示されます。

2) DuckDB にデータを取り込む（J-Quants から取得 → 保存）
- 例（スクリプト内で）:
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")
  - data = fetch_daily_quotes()  # 必要に応じて code/date_from/date_to を指定
  - save_daily_quotes(conn, data)
  - conn.close()
- jquants_client は内部でレート制限とリトライを実装しています。401 でトークン自動更新も行います。

3) 特徴量生成 / シグナル生成（DuckDB 上で）
- 例（スクリプト内で）:
  - from datetime import date
  - import duckdb
  - from kabusys.strategy import build_features, generate_signals
  - conn = duckdb.connect("data/kabusys.duckdb")
  - build_features(conn, date(2023, 12, 31))
  - generate_signals(conn, date(2023, 12, 31))
  - conn.close()

4) ニュース収集ジョブ（RSS）
- run_news_collection 関数を呼ぶと RSS を取得して raw_news, news_symbols へ保存します。
- 例:
  - from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  - conn = init_schema("data/kabusys.duckdb")
  - known_codes = set(...)  # stocks テーブルなどからコードセットを用意
  - run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)

主要 API（抜粋）
----------------
- kabusys.config.settings — 環境設定アクセサ（settings.jquants_refresh_token 等）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=...)
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest
  - run_backtest(conn, start_date, end_date, ...)

ディレクトリ構成（主要ファイル）
------------------------------
（抜粋、実ファイルは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 & 設定管理
  - data/
    - jquants_client.py            — J-Quants API client + DuckDB 保存
    - news_collector.py            — RSS ニュース取得・保存
    - (schema.py, calendar_management.py など：スキーマ初期化やカレンダー管理想定)
  - research/
    - factor_research.py           — momentum/volatility/value ファクター
    - feature_exploration.py       — IC / forward returns / summary
  - strategy/
    - feature_engineering.py       — features のビルド
    - signal_generator.py          — final_score からシグナル作成
  - portfolio/
    - portfolio_builder.py         — 候補選定・重み計算
    - position_sizing.py           — 株数決定・資金配分
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py                    — バックテストループ、run_backtest
    - simulator.py                 — 約定シミュレータ、ポートフォリオ状態
    - metrics.py                   — バックテスト評価指標計算
    - run.py                       — CLI エントリポイント
  - execution/                      — 実際の発注実装（空モジュールのプレースホルダ）
  - monitoring/                     — 監視・アラート（Slack 等）用モジュール（想定）
  - portfolio/                      — 上記ポートフォリオロジック集

注意点 / 運用上のヒント
----------------------
- DuckDB のスキーマ初期化用関数（data.schema.init_schema）を使って DB を準備してください（サンプルスキーマはコードベースに含まれている想定）。
- バックテストは本番 DB からデータをコピーしてインメモリ DB を作るため、本番の signals/positions を汚染しません。
- レジーム（market_regime）が欠けている期間は 'bull' としてフォールバックされます。
- .env 自動読み込みはプロジェクトルート（.git or pyproject.toml を基準）を探して行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。
- ニュース収集や外部アクセスには SSRF / XML 攻撃対策やレスポンスサイズ制限が組み込まれていますが、運用時はソース URL の管理に注意してください。

ライセンス / 貢献
-----------------
（ここにはライセンス情報やコントリビュート手順を記載してください。リポジトリに応じて追記を推奨します。）

補足
----
この README はコードベースの現状スナップショットに基づいて作成しています。実運用では細かな設定や DB スキーマ、外部サービスの認証情報管理（Vault 等）を整備してください。必要であれば、README に含めるサンプル .env.example、schema の初期化 SQL、requirements.txt、運用手順（ETL / cron / CI）を追加できます。