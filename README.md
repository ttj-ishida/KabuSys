KabuSys
=======

概要
----
KabuSys は日本株の自動売買（リサーチ → シグナル生成 → 発注シミュレーション／バックテスト）を目的とした Python ライブラリです。  
主に以下の機能を提供します。

- J-Quants API からのデータ取得（株価日足、財務、上場銘柄情報、マーケットカレンダー）
- ニュース（RSS）収集と記事→銘柄紐付け
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量の正規化および features テーブルへの書き込み
- 戦略の最終スコア計算と BUY/SELL シグナル生成
- ポートフォリオ構築（候補選定・重み計算・ポジションサイジング・セクター制限・レジーム調整）
- バックテストエンジン（擬似約定、日次スナップショット、メトリクス計算）
- 各種ユーティリティ（環境設定読み込み、DB 保存ユーティリティ等）

主な特徴
----
- 明確に分離されたレイヤ（data / research / strategy / portfolio / backtest）
- DuckDB を用いた分析・ETL の想定（冪等性を考慮した DB 書き込み設計）
- J-Quants クライアントのレート制御・リトライ・自動トークンリフレッシュ対応
- ニュース収集での SSRF 対策、圧縮／サイズ制限、XML パースの安全対策（defusedxml）
- バックテストではスリッページ・手数料・単元丸め・部分約定等の振る舞いをシミュレート
- 設定は .env / OS 環境変数を利用（自動ロード機構あり）

必要条件
----
- Python 3.10+
- 必要な外部ライブラリ（例）
  - duckdb
  - defusedxml
  - ※プロジェクトに requirements.txt がある場合はそれを使用してください。なければ最低限上記を pip でインストールしてください。

セットアップ手順
----
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （もし requirements.txt があれば）pip install -r requirements.txt
4. 環境変数を用意
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env または .env.local を作成できます。以下は代表的な環境変数（例）：

   - JQUANTS_REFRESH_TOKEN=xxxxx
   - KABU_API_PASSWORD=xxxxx
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # optional
   - SLACK_BOT_TOKEN=xxxxx
   - SLACK_CHANNEL_ID=xxxxx
   - DUCKDB_PATH=data/kabusys.duckdb  # optional
   - SQLITE_PATH=data/monitoring.db   # optional
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   自動読み込みを無効にする場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 初期 DB スキーマの準備
   - プロジェクト内のデータスキーマ初期化関数（例: kabusys.data.schema.init_schema）を使って DuckDB を初期化してください。
   - 実運用/バックテストに必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks, raw_prices, raw_financials, raw_news, news_symbols, positions, signals 等）を用意する必要があります（schema 定義は data/schema モジュールを参照）。

基本的な使い方
----
- バックテストの実行（CLI）
  - モジュール entry: src/kabusys/backtest/run.py に CLI が用意されています。
  - 例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db path/to/kabusys.duckdb

  - オプションの主なもの:
    - --start / --end : 開始・終了日（YYYY-MM-DD）
    - --cash : 初期資金（JPY）
    - --slippage / --commission : スリッページ・手数料率
    - --allocation-method : equal|score|risk_based
    - --max-positions : 最大保有銘柄数
    - --lot-size : 単元株数（デフォルト 100）
    - --db : DuckDB ファイルパス（必須）

- 研究/特徴量作成
  - build_features(conn, target_date)
    - 使い方例:
      from datetime import date
      import duckdb
      from kabusys.strategy import build_features
      conn = duckdb.connect("path/to/kabusys.duckdb")
      build_features(conn, date(2024, 1, 4))

- シグナル生成
  - generate_signals(conn, target_date, threshold=0.6, weights=None)
    - 使い方例:
      from kabusys.strategy import generate_signals
      generate_signals(conn, date(2024, 1, 4))

- J-Quants データ取得と保存
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes(conn, records) 等の保存関数で DuckDB に書き込むことができます。
  - 例:
      from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
      records = fetch_daily_quotes(date_from=..., date_to=...)
      save_daily_quotes(conn, records)

- ニュース収集（RSS）
  - run_news_collection(conn, sources=None, known_codes=None)
    - RSS フェッチ、raw_news への保存、銘柄抽出 → news_symbols への保存まで一気通貫で行います。

設定と環境変数（まとめ）
----
必須（実行する機能に応じて）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（data.jquants_client が必須）
- KABU_API_PASSWORD : kabu API を用いる場合
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知を使う場合

任意（デフォルトあり）:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development|paper_trading|live) — settings.is_live / is_paper / is_dev フラグに影響
- LOG_LEVEL

自動 .env ロード:
- プロジェクトルートに .env/.env.local がある場合、KABUSYS_DISABLE_AUTO_ENV_LOAD が未設定なら自動で読み込みます。
- 優先順位: OS 環境変数 > .env.local > .env
- テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要モジュール / ディレクトリ構成
----
（抜粋・説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込みと Settings クラス。.env 自動読み込み機能。
  - data/
    - jquants_client.py : J-Quants API クライアント（レート制御、リトライ、保存ユーティリティ）
    - news_collector.py : RSS フェッチ、前処理、raw_news/news_symbols 保存
    - (schema.py, calendar_management などの補助モジュールが想定される)
  - research/
    - factor_research.py : モメンタム / ボラティリティ / バリューのファクター計算
    - feature_exploration.py : 将来リターン、IC、統計サマリー等のリサーチユーティリティ
  - strategy/
    - feature_engineering.py : ファクターの正規化・features テーブルへの書き込み
    - signal_generator.py : ファクター＋AIスコアから final_score を計算して signals へ保存
  - portfolio/
    - portfolio_builder.py : 候補選定・重み計算（等金額・スコア加重）
    - position_sizing.py : 発注株数算出（risk_based / equal / score）
    - risk_adjustment.py : セクターキャップ・レジーム乗数
  - backtest/
    - engine.py : バックテストループ（データコピー → シミュレータ実行 → シグナル生成 → 発注）
    - simulator.py : 擬似約定・ポートフォリオ状態管理（PortfolioSimulator）
    - metrics.py : バックテスト評価指標（CAGR, Sharpe 等）
    - run.py : CLI エントリポイント
    - clock.py : 将来拡張用の模擬時計
  - execution/ (placeholder)
  - monitoring/ (placeholder)
  - portfolio/, research/, strategy/, backtest/ はプロジェクトの中核ロジックを提供

設計上の注意点 / ベストプラクティス
----
- ルックアヘッドバイアスの防止: すべての研究/シグナル生成は target_date 時点で「当該日時点で実際に知り得る」データのみを使う設計になっています（prices_daily の最新レコード参照等）。
- DB 操作は冪等性を意識（ON CONFLICT 句、日付単位の置換トランザクション等）。
- ニュース関連は SSRF や XML 攻撃対策を備えています（_SSRFBlockRedirectHandler、defusedxml、サイズ制限等）。
- バックテストは本番 DB を汚さないよう一時的に in-memory DuckDB にデータをコピーして実行します。

貢献・拡張
----
- 研究用ファクターの追加、戦略重みの調整、execution 層（実際の発注）の実装や Slack 通知の統合などが想定拡張領域です。
- テストと CI による回帰防止を推奨します（特に金融ロジックは数値の丸め・境界条件で差が出るため）。

ライセンス / 著作権
----
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください（本 README では規定していません）。

補足（参考コマンド）
----
- DuckDB でスキーマを初期化（例）:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- バックテスト（具体例）:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- 研究用特徴量作成:
  from datetime import date
  from kabusys.strategy import build_features
  build_features(conn, date(2024, 1, 4))

以上が KabuSys の README です。必要であれば、各モジュールの詳細ドキュメント（関数シグネチャ、入出力の例、期待される DB スキーマ）も作成できます。どの部分を詳細化しましょうか？