KabuSys
======

日本株向けの自動売買・データ基盤ライブラリです。データ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集などの機能をモジュール化して提供します。

主な目的
- J-Quants からの株価・財務データ取得と DuckDB への保存（冪等）
- 研究用ファクター計算／特徴量作成（ルックアヘッドバイアスに配慮）
- 戦略シグナル生成（features と AI スコアの統合）
- バックテストフレームワーク（擬似約定・ポートフォリオシミュレータ・メトリクス）
- RSS ニュース収集と銘柄紐付け（SSRF対策・前処理・重複除去）

主な機能一覧
- データ取得・保存
  - J-Quants API クライアント（レートリミット・自動トークンリフレッシュ・リトライ）
  - raw_prices / raw_financials / market_calendar の取得と DuckDB への冪等保存
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックの仕組み
- 特徴量エンジニアリング（strategy.feature_engineering）
  - research モジュールの生ファクターから Z スコア正規化・ユニバースフィルタを適用し features テーブルに UPSERT
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合し final_score を計算、BUY/SELL シグナルを signals テーブルへ書き込み
  - Bear レジーム抑制、エグジット（ストップロス等）実装
- バックテスト（backtest パッケージ）
  - run_backtest(): 本番 DB からインメモリへデータコピーして日次ループをシミュレーション
  - PortfolioSimulator による擬似約定（スリッページ・手数料モデル）
  - バックテストメトリクス（CAGR, Sharpe, MaxDrawdown, Win rate 等）
  - CLI エントリポイント: python -m kabusys.backtest.run
- ニュース収集（data.news_collector）
  - RSS フィード取得、正規化、前処理、raw_news への保存、銘柄抽出と news_symbols 保存
  - SSRF/サイズ制限/XML 攻撃対策 を実装
- データスキーマ管理（data.schema）
  - DuckDB 用のスキーマ（Raw / Processed / Feature / Execution 層）を定義・初期化する init_schema()

動作要件
- Python >= 3.10（typing の | 演算子などを使用）
- 必要なパッケージ（最低限）
  - duckdb
  - defusedxml
- 環境によっては追加で標準ライブラリ外のパッケージが必要になる可能性があります。プロジェクトに requirements.txt があればそちらを使用してください。

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージを packaging/セットアップしている場合）pip install -e .
4. 環境変数の設定
   - プロジェクトルートの .env / .env.local から自動読み込みを行います（.git または pyproject.toml を検出して自動読み込み）。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD     : kabuステーション API 用パスワード（実行層で使用）
     - SLACK_BOT_TOKEN       : Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID      : Slack のチャネルID
   - 任意（デフォルト値あり）
     - KABUSYS_ENV           : development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - 例 .env（簡易）
     - JQUANTS_REFRESH_TOKEN=xxx
     - KABU_API_PASSWORD=your_kabu_password
     - SLACK_BOT_TOKEN=xoxb-...
     - SLACK_CHANNEL_ID=C12345678
     - DUCKDB_PATH=data/kabusys.duckdb

基本的な使い方（例）
- DuckDB スキーマ初期化
  - Python REPL / スクリプト:
    - from kabusys.data.schema import init_schema
    - conn = init_schema("data/kabusys.duckdb")
    - conn.close()
  - init_schema(":memory:") でインメモリ DB を作成できます（主にテスト・バックテスト用）。

- J-Quants からデータ取得 & 保存（ETL）
  - データ取得と保存の高レベル関数は kabusys.data.pipeline にあります（run_prices_etl など）。
  - 例（簡単な実行例、実運用ではログ・エラーハンドリングを整備してください）:
    - from datetime import date
      from kabusys.data.schema import init_schema
      from kabusys.data.pipeline import run_prices_etl
      conn = init_schema("data/kabusys.duckdb")
      fetched, saved = run_prices_etl(conn, target_date=date.today())
      conn.close()

- ニュース収集
  - from kabusys.data.schema import init_schema
    from kabusys.data.news_collector import run_news_collection
    conn = init_schema("data/kabusys.duckdb")
    results = run_news_collection(conn, sources=None, known_codes=None)
    conn.close()
  - sources を辞書で渡して収集ソースをカスタマイズできます。known_codes を渡すと記事から銘柄抽出→news_symbols への登録を行います。

- 特徴量作成（features テーブルの構築）
  - Python から:
    - from kabusys.data.schema import init_schema
      from kabusys.strategy import build_features
      conn = init_schema("data/kabusys.duckdb")
      build_count = build_features(conn, target_date=date(2024, 1, 1))
      conn.close()

- シグナル生成
  - from kabusys.strategy import generate_signals
    generate_count = generate_signals(conn, target_date=date(2024,1,1), threshold=0.6)

- バックテスト（CLI 例）
  - 付属のランナーを使う:
    - python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db data/kabusys.duckdb
  - オプションにより初期資金・スリッページ・手数料・max position を指定可能:
    - --cash, --slippage, --commission, --max-position-pct

- バックテスト（プログラム呼び出し）
  - from kabusys.backtest.engine import run_backtest
    result = run_backtest(conn, start_date, end_date, initial_cash=10000000)
    result.metrics  # BacktestMetrics インスタンス

設定・環境管理について
- 自動 .env ロード
  - kabusys.config モジュールは、プロジェクトルート（.git または pyproject.toml）を起点に .env および .env.local を自動読み込みします（OS 環境変数が優先）。
  - テストなどで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Settings API
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env などのプロパティを介して設定を参照できます。
  - 必須値が未設定の場合は ValueError が発生します（_require を使用）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数/設定管理
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得・保存関数）
    - news_collector.py          -- RSS 収集・前処理・保存
    - schema.py                  -- DuckDB スキーマ定義・init_schema()
    - stats.py                   -- z-score 等の統計ユーティリティ
    - pipeline.py                -- ETL パイプライン（差分取得等の補助）
  - research/
    - __init__.py
    - factor_research.py         -- momentum/volatility/value 等のファクター計算
    - feature_exploration.py     -- forward returns / IC / summary
  - strategy/
    - __init__.py
    - feature_engineering.py     -- features の作成（正規化・ユニバースフィルタ）
    - signal_generator.py        -- final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py                  -- run_backtest の実装（インメモリコピー含む）
    - simulator.py               -- PortfolioSimulator / mark_to_market / trades
    - metrics.py                 -- バックテスト評価指標計算
    - run.py                     -- CLI エントリポイント（python -m kabusys.backtest.run）
    - clock.py                   -- SimulatedClock（将来拡張用）
  - execution/                    -- 発注・実行関連（未詳細実装箇所）
  - monitoring/                   -- 監視関連（未詳細実装箇所）

設計上の注意点
- ルックアヘッドバイアス対策
  - 各処理は target_date 時点で「システムが知り得る」データのみ参照する設計です（fetched_at の記録、target_date以前の最新値参照など）。
- 冪等性
  - DuckDB へのデータ保存は可能な限り UPSERT / ON CONFLICT により冪等性を確保しています。
- 安全性
  - ニュース収集では SSRF 対策、XML パーサーの安全版（defusedxml）、受信サイズ制限などを実装しています。
- シンプルな外部依存
  - 主要ロジックは標準ライブラリと duckdb / defusedxml に依存します（外部の大きなデータフレーム系に依存しない設計）。

拡張・運用ヒント
- ETL の自動化
  - cron / Airflow / Prefect 等で run_prices_etl / run_news_collection を定期実行し、品質チェック結果を監視してください。
- AI スコアやレジーム計算
  - ai_scores テーブルを充実させることで signal_generator のニュース重みやレジーム判定が有効になります。
- 本番発注との連携
  - execution 層を実装して signals → 注文 → executions → trades を連携させることでライブ運用が可能になります（ただし十分なテストを行ってください）。

ライセンス / 貢献
- （リポジトリに合わせて LICENSE を明記してください）
- バグ報告・機能追加は Issue / Pull Request を通じてお寄せください。

問い合わせ
- プロジェクト内の各モジュールはドキュメント文字列（docstring）を充実させています。実装詳細は各ファイルの docstring と関数シグネチャを参照してください。

以上を参考にローカルで環境を整え、まずは schema の初期化 → データ取得（ETL）→ features の作成 → generate_signals → run_backtest の順で動作確認を行うことを推奨します。必要があれば README を更新して利用手順や運用例を追記してください。