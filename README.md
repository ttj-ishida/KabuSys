KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買および研究用ライブラリ／ツール群です。  
主に以下の用途を想定しています。

- データ収集（J-Quants API、RSSニュースなど）
- ファクター計算・特徴量エンジニアリング
- シグナル生成（ファクター＋AIスコアの統合）
- ポートフォリオ構築（候補選定・配分・サイジング・セクター制約）
- バックテスト（擬似約定・手数料・スリッページモデル・評価指標）
- 研究用ユーティリティ（IC計算、ファクター探索など）

ライトでモジュール化された実装により、研究・バックテスト・本番ETL/運用の各層で再利用できます。

主な機能
--------
- data/
  - J-Quants API クライアント（ページネーション・トークンリフレッシュ・レート制限・DuckDB保存）
  - ニュース収集（RSS, 前処理、SSRF対策、DB保存、銘柄抽出）
- strategy/
  - 特徴量構築（research からの生ファクターを標準化して features に保存）
  - シグナル生成（ファクター・AIスコアを統合して BUY/SELL を生成）
- portfolio/
  - 候補選定（スコア順）
  - 重み計算（等配分 / スコア加重）
  - ポジションサイジング（risk-based / equal / score）
  - リスク調整（セクター上限、レジーム乗数）
- backtest/
  - ポートフォリオシミュレータ（擬似約定、スリッページ、手数料）
  - バックテストエンジン（全体ループ、DB読み取り/書き戻し）
  - メトリクス計算（CAGR, Sharpe, MaxDD, Win rate, Payoff）
  - CLI 実行エントリ（python -m kabusys.backtest.run）
- research/
  - ファクター計算（momentum / volatility / value）
  - ファクター探索用ユーティリティ（forward returns, IC, summary）

前提 / 要件
-----------
- Python 3.10+
  - typing の "|" 形式や新しい型注釈を使用しています
- 必須パッケージ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API を利用する場合は API トークンが必要

セットアップ手順
----------------

1. リポジトリをクローン（開発用）
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix / macOS
   - .venv\Scripts\activate     # Windows

3. 必要ライブラリのインストール（例）
   - pip install duckdb defusedxml
   - その他プロジェクトで使用するライブラリがある場合は requirements.txt を用意している想定で pip install -r requirements.txt

4. 環境変数設定
   - プロジェクトルートに .env を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動ロードを無効化できます）。
   - 必須の環境変数（例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネルID
     - （その他）
       - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
       - SQLITE_PATH（デフォルト: data/monitoring.db）
       - KABUSYS_ENV（development / paper_trading / live）
       - LOG_LEVEL（DEBUG / INFO / ...）
   - .env.example を参考に .env を作成してください（プロジェクトルート検出は .git または pyproject.toml に依存します）。

5. データベース初期化
   - DuckDB スキーマ初期化関数（schema.init_schema）がプロジェクトに提供されています。
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

使い方（主要操作）
------------------

1) バックテスト（CLI）
   - 事前に DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等が整備されている必要があります。
   - コマンド例:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db path/to/kabusys.duckdb \
       --allocation-method risk_based --max-positions 10

   - 出力: CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / Total Trades

2) プログラムからバックテストを実行
   - Python API:
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest
     conn = init_schema("path/to/kabusys.duckdb")
     result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
     # result.history, result.trades, result.metrics を参照

3) 特徴量構築・シグナル生成
   - build_features(conn, target_date)  # features テーブルを日付単位で置換
   - generate_signals(conn, target_date)  # signals テーブルを日付単位で置換（BUY/SELL）

   例:
     from kabusys.strategy import build_features, generate_signals
     build_features(conn, date(2024, 1, 5))
     generate_signals(conn, date(2024, 1, 5))

4) データ取得 & 保存（J-Quants）
   - fetch / save の流れ:
     from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
     token = get_id_token()  # settings.jquants_refresh_token を使用
     recs = fetch_daily_quotes(id_token=token, date_from=..., date_to=...)
     save_daily_quotes(conn, recs)

   - News収集:
     from kabusys.data.news_collector import run_news_collection
     run_news_collection(conn, sources=None, known_codes=set_of_codes)

注意点 / 実装上のポリシー
----------------------
- ルックアヘッドバイアス対策:
  - features / signals / raw データは target_date 時点の情報のみを用いて計算する設計です。
  - J-Quants 取得時は fetched_at を UTC で記録します。
- 冪等性:
  - DB への保存処理は重複更新を避ける（ON CONFLICT / 日付単位の削除と挿入）実装になっています。
- セキュリティ:
  - news_collector は SSRF 対策（ホスト確認・リダイレクト検査）・XML攻撃対策（defusedxml）を行います。
- レート制限・リトライ:
  - J-Quants クライアントはレートリミッタとリトライ/トークンリフレッシュを備えています。

ディレクトリ構成（概観）
----------------------
src/kabusys/
- __init__.py
- config.py  — 環境変数管理・自動 .env ロード・settings
- data/
  - jquants_client.py       — J-Quants API クライアント & DuckDB 保存
  - news_collector.py       — RSS 収集・前処理・DB保存・銘柄抽出
  - (その他: schema, calendar_management, stats などが想定)
- research/
  - factor_research.py      — momentum / volatility / value 計算
  - feature_exploration.py  — forward returns / IC / summary
- strategy/
  - feature_engineering.py  — features テーブル構築
  - signal_generator.py     — final_score 計算・BUY/SELL 生成
- portfolio/
  - portfolio_builder.py    — 候補選定・等配分/スコア配分
  - position_sizing.py      — 株数計算（risk_based 等）
  - risk_adjustment.py      — セクター上限・レジーム乗数
- backtest/
  - engine.py               — バックテストループ（run_backtest）
  - simulator.py            — 擬似約定・portfolio simulator
  - metrics.py              — バックテスト評価指標計算
  - run.py                  — CLI エントリ（python -m kabusys.backtest.run）
  - (clock.py)
- portfolio/ (パッケージエクスポートファイル)
- strategy/__init__.py
- research/__init__.py
- backtest/__init__.py
- その他: execution/, monitoring/（プレースホルダ）

開発・コントリビュート
----------------------
- コーディング規約やテストがある場合はリポジトリの CONTRIBUTING.md を参照してください（本README には含まれていません）。
- 自動 .env ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（単体テスト等で便利です）。
- 大きな変更やアルゴリズムの改定は設計ドキュメント（StrategyModel.md, PortfolioConstruction.md, BacktestFramework.md 等）に沿って行ってください（コード中で参照されています）。

ライセンス
---------
- 本 README にはライセンス情報を含めていません。実際の配布では LICENSE ファイルを参照してください。

問い合わせ
----------
- コードベースに関する設計意図や詳細な説明はソース内の docstring / コメントを参照してください。
- 実運用や API トークンの取り扱いについては組織のセキュリティポリシーに従ってください。

以上。必要であれば利用例（コードスニペット）や .env.example のテンプレート、requirements.txt の推奨内容を追加で作成します。どの内容を優先しますか？