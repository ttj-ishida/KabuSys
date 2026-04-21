README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームです。銘柄選定・配分・ポジションサイズ計算、発注実行、監視、研究（ファクター計算・特徴量探索）、および OpenAI を利用したニュース NLP / レジーム判定などのユーティリティを提供します。

主な設計方針
- 本番・ペーパートレードを環境変数（KABUSYS_ENV）で切替可能
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB に利用
- 各種処理は副作用を最小にした純粋関数 / 明確な書き込み API を重視
- OpenAI 呼び出しはリトライやバリデーションを行いフェイルセーフを備える

機能一覧
--------
- Execution
  - ExecutionEngine（発注エンジン）起動スクリプト（run_execution.py）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を利用し、専用 DB（data/paper_trading.db）へログを残す
  - リスクマネージャ、OrderManager、Reconciler 等の組立済みコンポーネント

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた監視エンジン（monitoring_engine.py）
  - システム稼働率、データ鮮度、滞留注文、約定異常、ドローダウンなどの監視とログ化
  - Kill Switch（条件で data/kill.flag を書き込み Execution を停止）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔調整）

- Portfolio Construction
  - 候補選定（select_candidates）
  - 重み算出（等配分 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め・aggregate cap）

- Research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（スピアマンランク）計算、統計サマリー

- AI（OpenAI）
  - ニュース記事を LLM でセンチメント化し ai_scores に格納（kabusys.ai.news_nlp）
  - 市場レジーム判定（ETF MA + マクロニュース LLM 合成）

- ツール
  - 設定ウィザード（config_setup.py）で .env を対話式作成
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

セットアップ手順
----------------

1. リポジトリをクローン（またはパッケージを配置）
   - この README はパッケージ配布済みの構成を前提としています。

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検査を有効にしたい場合、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください）

4. 初期設定 (.env)
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
     - LOG_LEVEL, LOG_DIR 等

   - 自動 .env ロード:
     - 起動時にプロジェクトルートの .env（および .env.local）を自動で読み込みます。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. ディレクトリ作成（必要なら）
   - data/ や logs/ ディレクトリは自動作成されますが、権限等で失敗する場合は手動作成してください。

基本的な使い方
--------------

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗として扱います

- 設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- ExecutionEngine を起動
  - 通常（本番 or 開発）:
    - python -m kabusys.run_execution
  - Paper Trading（仮想発注）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は Broker が MockBroker になり、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。

  実装上のポイント:
  - 起動時に PID ファイル（data/execution.pid）を使用
  - 停止は data/stop_requested.flag を立てるか、kill.flag を外部から書く方式で制御します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると data/kill.flag を自動クリア（本番では 0 推奨）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で秒数を指定（デフォルト 60 秒）
  - 監視は KABUSYS_ENV にかかわらず production の sqlite_path（SQLITE_PATH）を使用して記録します（監視は本番 DB を参照する設計）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成するとループが終了します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数より優先して指定可能）

- OpenAI を使う機能
  - ニュース NLP（kabusys.ai.news_nlp.score_news）や regime_detector は OPENAI_API_KEY が必要
  - ランタイムで環境変数 OPENAI_API_KEY を設定するか、関数引数に渡してください
  - API 呼び出しにはリトライ・バリデーションが含まれますが、API キー未設定時は ValueError を発生します

ロギング
--------
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます
- デフォルト:
  - コンソール出力（stdout）
  - 日次ローテートファイル: logs/<app_name>.log（30 日分保持）
- ログレベルは環境変数 LOG_LEVEL で指定可能（デフォルト INFO）
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用

注意点 / 運用メモ
----------------
- 監視（run_monitoring）は監視用 SQLite（SQLITE_PATH）を常に使用します。監視中は KABUSYS_ENV による DB 切替は行いません。
- run_execution は KABUSYS_ENV=paper_trading のとき PAPER_TRADING_SQLITE_PATH を使用し本番 DB と完全に分離します。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと data/kill.flag を書き、ExecutionEngine の停止を促します。kill.flag は冪等性を持って書き込まれます。
- stop_requested.flag:
  - run_execution / run_monitoring は data/stop_requested.flag の存在でループを安全に終了します（デプロイ時の手動停止などに利用）。

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                   -- 環境変数/設定読み込みロジック
    config_setup.py             -- .env 対話式ウィザード
    validate_config.py          -- 起動前設定検証 CLI
    run_execution.py            -- ExecutionEngine 起動スクリプト
    run_monitoring.py           -- Monitoring 起動スクリプト
    tools/
      paper_verification_report.py
    ai/
      news_nlp.py               -- ニュース NLP（OpenAI）によるスコアリング
      regime_detector.py        -- レジーム判定（MA + LLM）
    monitoring/
      monitoring_db.py          -- SQLite 用永続化 API
      monitoring_engine.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
    execution/
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
    research/
      factor_research.py
      feature_exploration.py
    data/
      pipeline.py                -- prices_daily など取得ユーティリティ（参照）
    utils/
      logging_setup.py
      process_priority.py
    (その他モジュール...)

data/         -- デフォルトの DB / フラグファイル保存先（例: data/monitoring.db, data/paper_trading.db）
logs/         -- ログファイル出力先（デフォルト）

サンプル .env（抜粋）
--------------------
# KABUSYS 環境
KABUSYS_ENV=development

# 必須（実運用時に設定）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here

# DB パス（任意、デフォルトを使用する場合は未設定でも可）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# OpenAI（AI 機能を使う場合）
OPENAI_API_KEY=sk-...

# ログ
LOG_LEVEL=INFO

よくある操作コマンド例
--------------------
- 設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution

- 監視起動（60 秒間隔、環境変数で変更可）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 拡張ポイント
------------------------
- broker の実装（本番 / Mock）の差替えは BrokerClientFactory を参照
- DuckDB スキーマ（prices_daily / raw_financials）に依存するため、データ投入パイプラインは data/pipeline.py を拡張してください
- OpenAI 呼び出しやモデルは設定値で切替可能（実装に合わせて変更）

ライセンス・バージョン
---------------------
- パッケージバージョンは kabusys.__version__ で管理（現行: 0.1.0）
- ライセンス情報はプロジェクトルートの LICENSE を参照してください（存在する場合）

以上がこのコードベースの概要と基本的な使い方です。必要に応じて個別モジュール（monitoring/*、execution/*、ai/*、portfolio/*、research/*）のドキュメントを参照してください。