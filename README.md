README
=====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のサンプル実装です。  
システムは主に以下の責務を持ちます。

- 市場データ・ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング）
- ExecutionEngine（ブローカー接続 / 発注ロジック / リスク管理）
- 監視（プロセス/リソース/データ鮮度の定期チェック、Kill Switch）
- AI 補助（ニュース NLP によるセンチメント評価、レジーム判定）
- ツール類（ペーパートレード検証レポート等）

本リポジトリはライブラリモジュール群（kabusys.*）と、起動用のスクリプト/CLI を含みます。

主な機能
--------
- ポートフォリオ構築関数
  - 候補選定、等重・スコア重み付け、ポジションサイズ算出（lot 単位 / リスク制約）
- リスク調整
  - セクター集中キャップ、レジームに基づく投下資金乗数
- リサーチ
  - Momentum / Volatility / Value などのファクター計算（DuckDB 経由）
  - 将来リターン、IC（スピアマン）計算、統計サマリー
- AI 機能（OpenAI）
  - ニュース記事の銘柄別センチメントスコアリング（ai_scores テーブルへ保存）
  - マクロニュース＋ETF MA を用いた市場レジーム判定（market_regime へ保存）
  - API 呼び出しはリトライやフェイルセーフを備えています
- 監視（Monitoring）
  - system_status / trade_logs / positions / risk_logs / dashboard を保存
  - SystemMonitor, TradeMonitor, RiskMonitor をまとめる MonitoringEngine
  - KillSwitch による flag ファイルでの ExecutionEngine 停止
- 実行スクリプト
  - 実行エンジン起動 run_execution.py、監視ポーリング run_monitoring.py
- ユーティリティ
  - .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）

前提条件
--------
- Python 3.9+（typing の記法などに依存）
- 推奨/利用ライブラリ（環境に応じてインストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の内容検証を行いたい場合）
- OS: Linux / macOS / Windows（プロセス優先度などで挙動差分あり）

セットアップ手順
----------------
1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリのインストール（プロジェクトに requirements.txt があればそれを利用）
   - pip install duckdb psutil
   - AI 機能を使うなら: pip install openai
   - YAML 検証を行うなら: pip install PyYAML

3. .env の作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
     - デフォルトの .env はプロジェクトルートに作成されます
   - または .env.example を参照して手動作成

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

5. DB 等の初期化
   - monitoring 用 SQLite（デフォルト: data/monitoring.db）は起動スクリプトが接続時に必要なテーブルを作成します（init_monitoring_db）。
   - DuckDB（デフォルト: data/kabusys.duckdb）はデータロードの準備が必要（prices_daily / raw_financials 等のテーブルを用意してください）。

主要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (monitoring) ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 環境時に使用）
- PAPER_FILL_MODE: paper_trading の MockBroker の約定挙動（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動でクリアするか（"1" でクリア）

使い方
------

起動スクリプト
- 監視プロセス（SystemMonitor を使ったポーリング）
  - python -m kabusys.run_monitoring
  - 動作: data/stop_requested.flag を監視。存在するとループを終了します。
  - MONITOR_POLL_INTERVAL で間隔を上書き可能（秒）

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
  - 起動時に既に data/stop_requested.flag が存在すると起動を中止します
  - 実行中は data/stop_requested.flag により安全停止をトリガできます

設定ウィザード / 検証
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い

Paper Trading 検証レポート
- tools/paper_verification_report を使ってペーパートレード結果のサマリを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH を使う場合は不要）
  - 出力: 稼働率 / 注文成功率 / レイテンシ等を表示し PASS/FAIL 判定を行います

AI 機能（プログラムからの呼び出し例）
- ニュース NLP（銘柄別スコアを ai_scores に書き込む）
  - from openai import OpenAI を導入済みで、OPENAI_API_KEY を環境変数にセット
  - 例:
    - import duckdb
      from datetime import date
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, target_date=date(2026, 4, 1), api_key=None)  # api_key None → 環境変数参照

- レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,4,1), api_key=None)

監視・停止（Kill Switch）
- KillSwitch はデータベースのリスク判定により data/kill.flag を書き込みます（実行停止は実行エンジン側で kill.flag を監視しているわけではなく、run_execution/run_monitoring は stop_requested.flag を用いています）
- 実行停止をリクエストしたい場合はプロジェクトルートの data/stop_requested.flag を作成してください（run_execution/run_monitoring が検知して安全停止します）
- ExecutionEngine 側の Kill Switch（risk による自動停止）は monitoring 側が kill.flag を書いてアラートを出す仕組みになっています
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では注意）

ログ
----
- 共通のログ設定を使用（kabusys.utils.logging_setup.setup_logging）
- デフォルト: logs/<app_name>.log に日次ローテーションで保存（30 日分保持）
- コンソール出力は stdout に出ます

ディレクトリ構成（主要ファイル）
----------------------------
src/
  kabusys/
    __init__.py
    config.py                     # 環境変数 / Settings の読み取り・自動ロード
    config_setup.py               # .env 対話ウィザード
    validate_config.py            # 設定検証 CLI
    run_monitoring.py             # SystemMonitor ポーリングループ起動スクリプト
    run_execution.py              # ExecutionEngine 起動スクリプト
    utils/
      logging_setup.py            # 共通ログ設定
      process_priority.py         # プロセス優先度・CPU affinity 設定ユーティリティ
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    ai/
      news_nlp.py                 # ニュース NLP（OpenAI）
      regime_detector.py          # レジーム判定（OpenAI）
      __init__.py
    monitoring/
      monitoring_db.py            # SQLite 永続層
      system_monitor.py
      trade_monitor.py            # （省略: trade 関連監視）
      risk_monitor.py
      kill_switch.py
      monitoring_engine.py
      alert_manager.py            # （通知管理、省略）
    execution/
      execution_engine.py         # ExecutionEngine（本体、省略部分あり）
      broker_factory.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
    tools/
      paper_verification_report.py
    research/                      # 研究用モジュール群（上記）
    portfolio/                     # ポートフォリオ構築群（上記）

（上記は抜粋。実装ファイルは src/kabusys 以下にまとまっています）

主要な挙動メモ
----------------
- Settings（kabusys.config.Settings）は .env と環境変数を読み、デフォルトを提供します。自動ロードはプロジェクトルート（.git か pyproject.toml）を基準に行いますが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- run_monitoring は MONITOR_POLL_INTERVAL でポーリング間隔を制御できます（デフォルト 60 秒）。
- run_execution は KABUSYS_ENV=paper_trading の際に paper_trading 用 DB を使用して本番 DB と分離します。
- DuckDB コネクションを受け取り SQL ベースで大規模データ処理を行う設計です（prices_daily / raw_financials 等の準備が必要です）。
- AI 機能は OpenAI API を利用するため API キー・コスト管理に注意してください。API 呼び出し部分はリトライやエラーハンドリングを備えていますが、料金/レート制限は別途管理してください。

トラブルシュート
----------------
- .env が読み込まれない / 設定が足りない場合:
  - python -m kabusys.config_setup で再作成
  - python -m kabusys.validate_config でチェック
- ログファイルが作成されない:
  - logs ディレクトリの作成権限を確認
  - 環境変数 LOG_DIR で別ディレクトリを指定可能
- OpenAI 呼び出しで失敗が多い:
  - OPENAI_API_KEY の設定確認、料金 / レート制限を確認
  - AI 関連は失敗時にフェイルセーフで処理継続する設計（部分的にスコアが得られないことがあります）

開発者向けメモ
----------------
- モジュールは内部で duckdb.Connection / sqlite3.Connection を受け取る形で設計されており、ユニットテストではモック接続や一時 DB を使って検証できます。
- ロギングは setup_logging で統一しており、ユニットテストでログレベルを変更することが可能です。
- OpenAI API 呼び出し箇所は _call_openai_api を patch すれば外部アクセスを行わずにテストできます。

ライセンス等
------------
- 本リポジトリのライセンス情報はここに記載されていません。配布/利用の際は著者に確認してください。

以上。必要であれば README に追記すべき実行例や .env の例テンプレート、セットアップスクリプト（requirements.txt 等）のサンプルを作成します。どの情報を詳しく掲載したいか教えてください。