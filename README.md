# KabuSys

日本株向けの自動売買／研究プラットフォーム（モジュール群）。  
ポートフォリオ構築、ファクター計算、シグナル生成、バックテスト、データ取得（J-Quants）、ニュース収集などの機能を含むライブラリ形式のコードベースです。

## プロジェクト概要
KabuSys は日本株アルゴリズム取引のためのライブラリ群です。研究環境（DuckDB を使ったファクタ計算・探索）と運用環境（シグナル生成→発注／監視）を分離し、バックテストフレームワークやデータ収集パイプライン（J-Quants からの価格/財務、RSS ニュース収集）を提供します。設計はルックアヘッドバイアス回避、冪等性、堅牢なエラーハンドリングを重視しています。

主な設計方針（抜粋）
- DuckDB を中心にデータを管理（prices_daily / raw_financials / features / signals / positions 等）
- 研究用関数は副作用を持たない純粋関数（DB参照は可能だが発注 API 等には依存しない）
- API クライアントはレートリミット・リトライ・トークン自動更新を実装
- ニュース収集は SSRF・XML Bomb 等を考慮した堅牢実装

## 機能一覧
- 設定管理（kabusys.config）
  - .env 自動読込（プロジェクトルート検出）／必須環境変数チェック
- データ取得（kabusys.data）
  - J-Quants クライアント（価格・財務・上場銘柄・カレンダー）
  - RSS ニュース収集・前処理・銘柄抽出
  - DuckDB への冪等保存ユーティリティ
- 研究（kabusys.research）
  - momentum / volatility / value などのファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターを統合・Zスコア正規化・features テーブルへ UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - features + ai_scores を統合して final_score を計算
  - Bear レジームフィルタ、BUY/SELL シグナル生成、signals テーブルへの冪等書込
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額／スコア加重／リスクベースのサイジング
  - セクター集中上限適用、レジーム乗数
- バックテスト（kabusys.backtest）
  - インメモリ DuckDB コピーによる独立バックテスト環境構築
  - PortfolioSimulator（擬似約定、スリッページ／手数料モデル）
  - run_backtest：日次ループでシグナル生成→約定→記録→メトリクス算出
  - メトリクス（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio）
- ニュース処理（kabusys.data.news_collector）
  - RSS 取得・正規化・DB 保存・銘柄抽出（既存銘柄セットを使用）
  - セキュリティ対策（SSRF、XML、サイズ上限など）

## セットアップ手順

前提
- Python 3.10+（コードは型注釈で 3.10 の機能を使用）
- DuckDB を利用（ローカルファイルまたはメモリ）

1. リポジトリをクローン／パッケージをインストール
   - 開発中の場合（パッケージインストール）
     ```
     git clone <repo>
     cd <repo>
     pip install -e .
     ```
   - 必要なパッケージ（最低限）
     ```
     pip install duckdb defusedxml
     ```
   - 実運用で HTTP 関連や追加依存があれば requirements.txt を用意している想定です。

2. 環境変数の準備
   - プロジェクトルートに `.env` または `.env.local` を作成することで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化できます）。
   - 主要な環境変数（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi   # 任意、デフォルトあり
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development   # development | paper_trading | live
     LOG_LEVEL=INFO
     ```
   - 設定が不足していると Settings プロパティで ValueError が発生します（必須は jquants refresh token / kabu api password / slack tokens 等）。

3. DuckDB スキーマ初期化
   - 本コードは内部で `kabusys.data.schema.init_schema` を利用する想定です（リポジトリ内に schema 実装があるものとして）。スキーマの初期化方法（例）：
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
     ```
   - 必要なテーブル（prices_daily, raw_financials, features, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols, signals, positions 等）を作成してください。schema 実装が用意されていれば init_schema が処理します。

## 使い方

いくつかの代表的な操作方法を示します。

1. バックテスト実行（CLI）
   - 提供されているエントリポイント:
     ```
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --db data/kabusys.duckdb \
       --cash 10000000 \
       --allocation-method risk_based
     ```
   - オプション（抜粋）
     - --start / --end: YYYY-MM-DD
     - --db: DuckDB ファイルパス（必須）
     - --cash, --slippage, --commission, --max-position-pct, --allocation-method, --max-utilization, --max-positions, --risk-pct, --stop-loss-pct, --lot-size

2. ファクター計算（features ビルド）
   - Python から直接呼び出し：
     ```python
     from datetime import date
     import duckdb
     from kabusys.strategy.feature_engineering import build_features
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     count = build_features(conn, target_date=date(2024, 1, 31))
     print("written:", count)
     conn.close()
     ```
   - build_features は DuckDB の prices_daily / raw_financials を参照し、features テーブルへ日付単位で置換挿入します（冪等）。

3. シグナル生成
   - Python から:
     ```python
     from datetime import date
     from kabusys.strategy.signal_generator import generate_signals
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     n = generate_signals(conn, target_date=date(2024,1,31), threshold=0.60)
     print("signals generated:", n)
     conn.close()
     ```
   - generate_signals は features と ai_scores、positions を参照して BUY/SELL を signals テーブルに書き込みます。

4. ニュース収集ジョブ
   - RSS 収集と保存（既存の銘柄コード集合を渡すと銘柄紐付けを実行）
     ```python
     from kabusys.data.news_collector import run_news_collection
     from kabusys.data.schema import init_schema

     conn = init_schema("data/kabusys.duckdb")
     known_codes = {"7203", "6758", "9984"}  # 例: あらかじめ stocks から取得してセット化
     results = run_news_collection(conn, known_codes=known_codes)
     print(results)
     conn.close()
     ```
   - fetch_rss / save_raw_news / save_news_symbols 等の細分化された API も利用可能です。

5. J-Quants データ取得
   - 価格・財務・リスト情報を取得して DuckDB に保存する：
     ```python
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
     from kabusys.data.schema import init_schema
     from datetime import date

     conn = init_schema("data/kabusys.duckdb")
     token = get_id_token()  # settings.jquants_refresh_token を使う
     recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
     saved = save_daily_quotes(conn, recs)
     print("saved rows:", saved)
     conn.close()
     ```

注意点
- 各保存関数は「冪等性（ON CONFLICT 等）」を考慮して設計されています。
- J-Quants API 呼び出しはレートリミットとリトライロジックを含みます。ID トークンが 401 の場合はリフレッシュします。
- ニュース収集では SSRF や XML 攻撃対策、受信サイズ上限が組み込まれています。

## ディレクトリ構成（主要ファイル）
以下はこのリポジトリ内の主要モジュール／ファイル構成（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                        # 環境変数・設定管理
    - data/
      - jquants_client.py              # J-Quants API クライアント（取得 + 保存）
      - news_collector.py              # RSS 取得・前処理・保存・銘柄抽出
      - schema.py                      # （想定）DuckDB スキーマ初期化（init_schema）
      - calendar_management.py         # 市場カレンダー（トレーディングデイズ）
      - stats.py                       # zscore_normalize 等ユーティリティ
    - research/
      - factor_research.py             # momentum/volatility/value 計算
      - feature_exploration.py         # calc_forward_returns, calc_ic, factor_summary
    - strategy/
      - feature_engineering.py         # features のビルド（正規化・UPSERT）
      - signal_generator.py            # final_score 計算・signals 書込
    - portfolio/
      - portfolio_builder.py           # 候補選定・重み計算
      - position_sizing.py             # 株数決定・集約キャップ
      - risk_adjustment.py             # セクターキャップ・レジーム乗数
    - backtest/
      - engine.py                      # run_backtest（メインロジック）
      - simulator.py                   # PortfolioSimulator（擬似約定）
      - metrics.py                     # バックテスト評価指標
      - run.py                         # CLI エントリポイント
      - clock.py
    - execution/                        # 発注・実行層（API 実装や kabu 接続）
    - monitoring/                       # 監視用コード（Slack 通知等）
    - portfolio/__init__.py
    - research/__init__.py
    - strategy/__init__.py
    - backtest/__init__.py

（上記はコードベースから抜粋した構成です。実際のファイルはプロジェクト内をご確認ください。）

## 環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN (必須)：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須)：kabu ステーション API パスワード
- KABU_API_BASE_URL (任意)：kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)：Slack チャンネル ID
- DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH：SQLite（監視用 DB）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV：environment（development | paper_trading | live）
- LOG_LEVEL：ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD：1 にすると .env の自動ロードを無効化

## 開発・拡張のヒント
- ファクターやシグナルのロジックは research/ および strategy/ に分離されているため、新しいファクター追加は research/factor_research.py → feature_engineering.build_features → features テーブル → signal_generator というフローで統合できます。
- バックテストは本番 DB を直接汚さないように _build_backtest_conn でインメモリにコピーして実行します。バックテスト中に生成される signals/positions はコピー先で完結します。
- ニュース収集の銘柄抽出は単純な 4 桁数字パターンに基づきます。精度向上が必要なら NLP／辞書ベースの追加処理を検討してください。

---

問題や追加で欲しいサンプル（例: schema.init_schema の使い方、requirements.txt の推奨一覧、具体的な .env.example）などがあれば提供します。