KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
DuckDB を用いた時系列データ管理、研究用途のファクター計算、特徴量生成、シグナル生成、ポートフォリオ構築、バックテスト用シミュレータ、J-Quants/ニュース収集用の ETL ツール群などを含みます。  
設計は以下を重視しています: ルックアヘッドバイアスの排除、冪等性、シンプルな純粋関数・モジュール化、バックテストと本番ロジックの分離。

主な機能
--------
- データ取得 / ETL
  - J-Quants API クライアント（株価、財務、カレンダー）: レート制限・再試行・トークン管理対応
  - RSS ベースのニュース収集（SSRF 対策・トラッキングパラメータ除去・記事ID生成）
- 研究 (research)
  - モメンタム / ボラティリティ / バリュー 等のファクター計算
  - ファクターの統計解析（IC、要約統計）
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターを正規化して features テーブルへ保存
- シグナル生成（strategy.signal_generator）
  - features と AI スコアを統合し BUY/SELL シグナルを生成（レジーム考慮、エグジット判定含む）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算（等配分／スコア加重）、リスク調整（セクターキャップ、レジーム乗数）、株数サイジング（単元・最大比率・リスクベース）
- バックテスト（backtest）
  - インメモリ DuckDB によるデータ準備、シミュレータ（約定・スリッページ・手数料）、メトリクス算出、CLI 実行可能
- その他
  - 環境変数・設定管理（自動 .env ロード、必須キー検査）
  - ニュース → 銘柄紐付けユーティリティ

前提条件 / 依存
---------------
（このリポジトリに requirements.txt が無い場合は適宜追加してください。以下は主要依存例）
- Python 3.9+（型ヒントに union 型などを利用）
- duckdb
- defusedxml
- その他：標準ライブラリ（urllib, logging, datetime, math, re 等）

セットアップ手順
---------------
1. リポジトリを取得
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb defusedxml
   - （パッケージ化されていれば）pip install -e .
4. 環境変数（.env）を用意
   - プロジェクトルートに .env/.env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（runtime で参照されるもの）例:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意/デフォルト:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|... (デフォルト: INFO)
     - DUCKDB_PATH=data/kabusys.duckdb (デフォルト)
     - SQLITE_PATH=data/monitoring.db
   - 例 (.env.example):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabus_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方
------
※ 以下は代表的な操作例です。実行前に DB スキーマ（init_schema）やデータ準備が必要です。

1) バックテスト（CLI）
   - DuckDB に prices_daily / features / ai_scores / market_regime / market_calendar 等が準備されている必要があります。
   - 実行例:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db path/to/kabusys.duckdb
   - 主要オプション:
     --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --lot-size など

2) 特徴量構築（Python API）
   - DuckDB 接続を取得して呼ぶ例:
     from kabusys.data.schema import init_schema
     from kabusys.strategy import build_features
     import duckdb
     conn = init_schema("path/to/kabusys.duckdb")
     count = build_features(conn, target_date)  # target_date は datetime.date
     conn.close()
   - build_features は features テーブルの日付単位置換（冪等）を行います。

3) シグナル生成（Python API）
   - generate_signals(conn, target_date, threshold=0.6, weights=None)
   - signals テーブルに BUY/SELL を書き込みます（同様に日付単位の置換）。

4) ニュース収集（RSS）
   - run_news_collection(conn, sources=None, known_codes=None)
   - fetch_rss / save_raw_news / save_news_symbols を組み合わせて実行します。
   - RSS の取得では SSRF 対策やサイズ制限、トラッキング除去が組み込まれています。

5) J-Quants データ取得と保存
   - kabusys.data.jquants_client.fetch_daily_quotes(...) を使ってデータを取得し、
     save_daily_quotes(conn, records) で raw_prices に保存できます。
   - トークン管理はモジュール内で自動処理されます（get_id_token）。

構成・ディレクトリ
------------------
（主要ファイルと役割を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス（必須キー取得）
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py — RSS 収集・記事保存・銘柄抽出
    - (schema.py, calendar_management などは参照されるが本サマリのコード列挙では省略)
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - strategy/
    - feature_engineering.py — ファクター正規化・features テーブルへの書き込み
    - signal_generator.py — final_score 計算・BUY/SELL シグナル生成
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数決定・aggregate cap
  - backtest/
    - engine.py — バックテスト全体ループ（データコピー・シミュレーション連携）
    - simulator.py — PortfolioSimulator（約定ロジック・時価評価）
    - metrics.py — バックテスト評価指標算出（CAGR, Sharpe, MaxDD, etc.）
    - run.py — CLI エントリポイント
    - clock.py — 将来拡張用模擬時計
  - portfolio/
  - execution/ (存在は宣言されているが実体は別途実装)
  - monitoring/ (同上)

設計上の注意点 / 運用メモ
------------------------
- ルックアヘッドバイアスを避けるため、特徴量/シグナル生成/バックテストは target_date 以前のデータのみ参照するよう設計されています。バックテストでは本番 DB を汚さないためインメモリコピーを作成します。
- .env 自動読み込みはプロジェクトルート (.git または pyproject.toml を起点) を探索して行います。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- J-Quants API はレート制限（120 req/min）に従うよう内部でスロットリングしています。大量取得の際は配慮してください。
- news_collector は RSS の SSRF 対策や gzip/bomb 対応を実装しています。外部 RSS を追加する際は DEFAULT_RSS_SOURCES を確認してください。
- バックテストの allocation_method="risk_based" では weight を使わず、risk_pct/stop_loss_pct を用いた株数算定が行われます。
- production 環境での自動売買を行う場合は、kabu ステーション API 関連（KABU_API_PASSWORD 等）を含むさらなる実装と厳格な安全対策が必要です。

貢献 / ライセンス
-----------------
- バグ報告・PR は歓迎します。README に要望があれば CONTRIBUTING を追加してください。  
- ライセンス表記は本リポジトリに従ってください（ここでは明示していません）。

補足
----
- この README はコードベースに基づく概要ドキュメントです。詳細な使用法（DB スキーマ、ETL 手順、AI スコア生成方法、運用フロー等）は別途ドキュメント（Design/Strategy/Backtest 文書）を参照してください。