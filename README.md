KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリです。
本リポジトリはデータ取得（J-Quants）、ETL、特徴量作成、シグナル生成、バックテスト、ニュース収集、擬似約定シミュレータ等を含む一連の機能を提供します。モジュール化されており、実運用（kabuステーション連携等）および研究・バックテスト用途の両方に対応する設計になっています。

主な特徴
--------
- J-Quants API クライアント（レート制御・リトライ・自動トークンリフレッシュ）
- DuckDB を用いたスキーマ定義と冪等な保存（ON CONFLICT 処理）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- ファクター計算（Momentum / Volatility / Value）と Z スコア正規化
- 戦略シグナル生成（ファクター + AI スコア統合、Bear レジーム抑制、BUY/SELL 判定）
- バックテストフレームワーク（シミュレータ、手数料・スリッページモデル、評価指標）
- ニュース収集（RSS パーサ、SSRF 対策、記事 → 銘柄紐付け）
- 安全性・堅牢性：トランザクション、サイズ上限、XML 脆弱性対策等

必要条件
--------
- Python 3.10+
- 必要パッケージ（主要なもの）
  - duckdb
  - defusedxml
  - （標準ライブラリのみを使うモジュールも多いですが、外部 HTTP/JSON 用に urllib を使用しています）

セットアップ（ローカル開発向け）
----------------------------
1. リポジトリをクローンして開発環境を作成します（pyproject.toml / setup がある想定）:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install -e .    # 開発インストール（pyproject.toml がある場合）

2. 依存パッケージを個別にインストールする場合:
   - pip install duckdb defusedxml

3. 環境変数を用意します（.env または OS 環境変数）
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN  (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD      (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL      (任意) — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN        (必須) — Slack Bot 用トークン（通知用）
     - SLACK_CHANNEL_ID       (必須) — Slack 通知先チャンネル ID
     - DUCKDB_PATH            (任意) — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH            (任意) — デフォルト: data/monitoring.db
     - KABUSYS_ENV            (任意) — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL              (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

  .env 例（簡易）
    JQUANTS_REFRESH_TOKEN=your_refresh_token_here
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=CXXXXXXX
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

初期 DB スキーマの作成
---------------------
DuckDB に必要なテーブルを作成するには schema.init_schema を使います。

Python REPL / スクリプト例:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

インメモリ DB（テスト用）:
  conn = init_schema(":memory:")

主要な使い方（サンプル）
----------------------

1) バックテスト（CLI）
  - 提供されているエントリポイント:
      python -m kabusys.backtest.run --start 2023-01-01 --end 2024-12-31 --db path/to/kabusys.duckdb
  - オプション: --cash / --slippage / --commission / --max-position-pct
  - 前提: 指定した DuckDB に prices_daily, features, ai_scores, market_regime, market_calendar 等が事前に入っている必要があります。

2) スキーマ初期化（スクリプト内呼び出し）
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

3) データ取得（J-Quants）と保存
  from kabusys.data import jquants_client as jq
  conn = init_schema("data/kabusys.duckdb")
  records = jq.fetch_daily_quotes(date_from=..., date_to=...)
  saved = jq.save_daily_quotes(conn, records)

  - fetch_financial_statements / save_financial_statements なども同様。

4) ETL パイプライン（部分的な利用例）
  from kabusys.data.pipeline import run_prices_etl
  result = run_prices_etl(conn, target_date=date.today())  # 関数は差分取得を行います

  （pipeline モジュールは差分更新・バックフィル・品質チェック等を実装する関数群を提供します）

5) 特徴量構築 -> シグナル生成
  from kabusys.strategy import build_features, generate_signals
  count = build_features(conn, target_date=date(2024,1,1))        # features テーブルを作成
  sig_count = generate_signals(conn, target_date=date(2024,1,1)) # signals テーブルを作成

6) ニュース収集
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)

7) バックテスト API の直接呼び出し
  from kabusys.backtest.engine import run_backtest
  result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)

設計・実装上のポイント
--------------------
- 冪等性: データ保存は ON CONFLICT / DO UPDATE / DO NOTHING を用いて冪等保存を実現しています。
- レート制御: J-Quants クライアントは固定間隔スロットリング（120 req/min）を実装。
- トランザクション: 重要な DB 操作はトランザクションで囲み、失敗時は ROLLBACK を試みます。
- セキュリティ: RSS 取得には SSRF 対策、defusedxml による XML 脆弱性対策、受信サイズ上限などを実装。
- Look-ahead bias 対策: 特徴量計算、シグナル生成は target_date 時点の情報のみを使うよう設計されています。
- 環境依存の自動ロード: .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みします。自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py                        # 環境変数・設定読み込み
- data/
  - __init__.py
  - jquants_client.py               # J-Quants API client（取得・保存）
  - news_collector.py               # RSS ニュース収集・保存・銘柄抽出
  - pipeline.py                     # ETL パイプライン（差分更新等）
  - schema.py                       # DuckDB スキーマ定義・初期化
  - stats.py                        # 統計ユーティリティ（z-score 等）
- research/
  - __init__.py
  - factor_research.py              # Momentum/Volatility/Value のファクター計算
  - feature_exploration.py          # IC / forward returns / summary 等の解析ユーティリティ
- strategy/
  - __init__.py
  - feature_engineering.py          # features テーブル作成（正規化・ユニバースフィルタ）
  - signal_generator.py             # シグナル生成ロジック（final_score 計算など）
- backtest/
  - __init__.py
  - engine.py                       # バックテストの全体制御ループ
  - simulator.py                    # ポートフォリオ・擬似約定シミュレータ
  - metrics.py                      # バックテスト評価指標計算
  - run.py                          # CLI エントリポイント
  - clock.py                        # 模擬時計（将来拡張用）
- execution/                         # 発注・実行関連（空パッケージ）
- monitoring/                        # 監視・通知関連（空パッケージ）

開発上の注意
------------
- 環境変数が未設定の場合、Settings プロパティは ValueError を投げます（必須のものを確認してください）。
- DuckDB のバージョン差異や外部 API のレスポンス変更により一部 SQL/パースが影響を受ける可能性があります。
- news_collector は外部ネットワークに依存するため、テスト時は _urlopen 等をモックしてください。
- ETL の差分算出や calendar の利用により、market_calendar が正しく入っていることが重要です。

トラブルシュート（簡易）
-----------------------
- 環境変数エラー: 実行時に "環境変数 'XXX' が設定されていません" のような例外が出たら .env を確認してください。
- DuckDB にテーブルがない: init_schema() を実行してスキーマを作成してください。
- J-Quants API エラー: トークン期限切れ等は自動リフレッシュを試みますが、refresh token が無効な場合は JQUANTS_REFRESH_TOKEN を確認してください。

ライセンス / 貢献
-----------------
（この README では指定されていません。リポジトリの LICENSE を参照してください。）

以上が基本的な README です。必要であれば、各モジュールごとの詳細な使い方、API ドキュメント、実運用（kabuステーション連携・Slack 通知設定）の手順を追加で作成します。どの部分を詳述したいか教えてください。