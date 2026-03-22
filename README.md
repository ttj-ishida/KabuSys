KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システム（データパイプライン、研究用ファクター計算、シグナル生成、バックテスト、ニュース収集など）を提供する Python パッケージです。  
主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「外部依存を最小化したロジック実装（DuckDB を DB として利用）」です。

主な機能
--------
- データ取得・保存
  - J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レートリミット・リトライ）
  - raw_prices / raw_financials / market_calendar 等の生データ保存（DuckDB）
- ETL パイプライン
  - 差分取得、バックフィル（後出し修正吸収）、品質チェック（quality モジュールを想定）
- ニュース収集
  - RSS フィード収集、URL 正規化、SSRF 対策、記事保存、銘柄コード抽出（news_symbols）
- 研究（research）
  - ファクター計算: momentum / volatility / value（prices_daily / raw_financials を参照）
  - ファクター探索: 将来リターン計算、IC（Spearman）計算、統計サマリー
- 特徴量エンジニアリング（strategy.feature_engineering）
  - 生ファクターの正規化（Z スコア）・ユニバースフィルタ（最低株価・売買代金）・features テーブルへの日付単位アップサート
- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を算出し BUY/SELL シグナルを作成、signals テーブルへ日付単位で置換（冪等）
  - Bear レジーム抑制・ストップロス等のエグジット条件を実装
- バックテスト（backtest）
  - PortfolioSimulator による擬似約定（スリッページ・手数料モデル）
  - run_backtest() による日次ループ、ポジション管理、シグナル生成のフルシミュレーション
  - 評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）

セットアップ
----------
以下は一般的なセットアップ手順の例です（プロジェクトに requirements.txt / pyproject.toml があることを想定）。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   または
   - pip install -e .  （パッケージとして編集可能インストール）

   ※ 本コードベースで明示的に使用されている主要パッケージ:
   - duckdb
   - defusedxml
   - （標準ライブラリのみの内部ユーティリティが多い）

4. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   必須の環境変数（設定モジュール kabusys.config に基づく）
   - JQUANTS_REFRESH_TOKEN    （J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD        （kabu API 用パスワード）
   - SLACK_BOT_TOKEN          （Slack 通知を使う場合）
   - SLACK_CHANNEL_ID         （Slack 通知先チャンネル）
   オプション（デフォルトあり）
   - KABUSYS_ENV              ("development" | "paper_trading" | "live"; デフォルト "development")
   - LOG_LEVEL                ("DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"; デフォルト "INFO")
   - KABU_API_BASE_URL        （kabu API の base URL; デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH              （DuckDB の DB ファイル; デフォルト data/kabusys.duckdb）
   - SQLITE_PATH              （監視 DB など; デフォルト data/monitoring.db）

5. DuckDB スキーマ初期化
   - Python から:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()
   - 上記で必要なテーブル（raw/processed/feature/execution レイヤ）を作成します。

使い方（代表的なワークフロー）
----------------------------

1) データ収集（J-Quants）
   - J-Quants から差分取得して保存する（jquants_client + data.pipeline を使用）
   - 直接呼び出し例（概念）:
     from kabusys.data import jquants_client as jq
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     records = jq.fetch_daily_quotes(date_from=..., date_to=...)
     jq.save_daily_quotes(conn, records)

   - または ETL パイプラインを利用:
     from kabusys.data.pipeline import run_prices_etl
     res = run_prices_etl(conn, target_date=date.today())

   - 注意: jquants_client はレート制御・リトライ・401 リフレッシュを備えています。

2) ニュース収集
   - RSS フィードを fetch_rss → save_raw_news → save_news_symbols
   - まとめ実行:
     from kabusys.data.news_collector import run_news_collection
     results = run_news_collection(conn, sources=None, known_codes=set_of_valid_codes)

   - news_collector は SSRF 対策、gzip 上限チェック、トラッキングパラメータ除去、ID の SHA256 ベース生成等を行います。

3) 特徴量作成（features）
   - DuckDB コネクションを用意して build_features を呼ぶ:
     from kabusys.strategy import build_features
     count = build_features(conn, target_date=some_date)
   - 生ファクター（research モジュール）を集約→ユニバースフィルタ→Zスコア正規化→features テーブルへ UPSERT します。

4) シグナル生成
   - generate_signals(conn, target_date=some_date, threshold=0.6, weights=None)
     from kabusys.strategy import generate_signals
     n = generate_signals(conn, target_date=some_date)

   - ai_scores が無い場合は中立スコアで補完。Bear レジーム判定やエグジット（stop loss, score drop）を実施。

5) バックテスト実行（CLI）
   - 用意された CLI を利用してバックテストを実行できます：
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

   - run_backtest() は本番 DB から必要データをコピーしてインメモリ DuckDB でシミュレーションを実行します。出力は履歴（DailySnapshot）、トレード履歴、評価指標（BacktestMetrics）。

6) プログラムからの利用（例）
   - スキーマ初期化
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 特徴量計算＋シグナル生成＋バックテスト（擬似例）
     from kabusys.strategy import build_features, generate_signals
     from kabusys.backtest.engine import run_backtest
     build_features(conn, target_date)
     generate_signals(conn, target_date)
     result = run_backtest(conn, start_date, end_date)

ディレクトリ構成（抜粋）
----------------------
プロジェクトの主要モジュール構成は以下の通りです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（fetch/save）
    - news_collector.py            # RSS → raw_news / news_symbols
    - pipeline.py                  # ETL パイプライン（差分取得等）
    - schema.py                    # DuckDB スキーマ初期化
    - stats.py                     # zscore_normalize 等ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           # momentum/volatility/value の計算
    - feature_exploration.py       # 将来リターン / IC / 統計サマリー
  - strategy/
    - __init__.py
    - feature_engineering.py       # features 作成
    - signal_generator.py          # signals 作成
  - backtest/
    - __init__.py
    - engine.py                    # run_backtest / バックテストループ
    - simulator.py                 # 擬似約定 / PortfolioSimulator
    - metrics.py                   # バックテスト評価指標
    - run.py                       # CLI エントリポイント
    - clock.py                     # SimulatedClock（将来用途）
  - execution/                      # 発注・実行関連（空のパッケージプレースホルダ）
  - monitoring/                     # 監視用モジュール（想定）

主要ファイルの責務まとめ
- config.py: .env 自動ロード（.env / .env.local）、必須環境変数要求、KABUSYS_ENV / LOG_LEVEL の検証
- data/schema.py: DuckDB の全テーブル定義と init_schema()
- data/jquants_client.py: API レート制御 / トークン取得 / fetch/save の高信頼実装
- data/news_collector.py: RSS 収集、XML パース防御、SSRF 対策、記事保存、銘柄抽出
- research/*: ファクター計算および解析ユーティリティ
- strategy/*: features の構築と signals の生成（重み・閾値の調整可）
- backtest/*: シミュレーションと評価指標

注意事項 / トラブルシューティング
---------------------------------
- 環境変数が不足していると Settings._require が ValueError を上げます。必須項目を .env に設定してください。
- DuckDB の初期化は init_schema() を必ず実行してください（テーブルが存在しないと処理が失敗します）。
- jquants_client は API レート制限を守るため内部で sleep します。大規模なバックフィルは時間がかかる点に注意してください。
- news_collector は外部 URL をフェッチするためネットワーク環境（プロキシ・ファイアウォール等）に影響されます。SSRF やサイズ制限のため一部フィードがスキップされる場合があります。
- バックテストでは本番 DB の signals / positions を汚さないために、run_backtest はソース DB からインメモリ DB へ必要なテーブルをコピーして実行します。

拡張 / 開発メモ
----------------
- execution 層（実際の発注）は現在プレースホルダです。kabu ステーション API 等との接続は execution 以下に実装してください。
- AI スコア周り（ai_scores テーブル）やマーケットレジームは戦略ロジックに組み込まれています。外部モデルの結果を ai_scores テーブルに入れることで戦略に反映できます。
- テスト可能性のため、HTTP 呼び出しや time.sleep などはモック可能な形（関数注入やモジュールレベル関数の差し替え）で設計されています。

ライセンス / コントリビュート
-----------------------------
（この README には含まれていません。リポジトリルートの LICENSE / CONTRIBUTING を参照してください。）

付録: 便利なコマンド例
--------------------
- DB スキーマ初期化（対話的）:
  python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"

- バックテスト（CLI）:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- Python スクリプトから features 作成 + シグナル生成:
  from kabusys.data.schema import init_schema
  from kabusys.strategy import build_features, generate_signals
  conn = init_schema('data/kabusys.duckdb')
  build_features(conn, target_date=date(2024,1,10))
  generate_signals(conn, target_date=date(2024,1,10))
  conn.close()

以上で README の概略です。必要であれば README に含める具体的な .env.example のテンプレートや、よくあるエラーメッセージと対処法の項目も追加します。どの情報を追記しますか？