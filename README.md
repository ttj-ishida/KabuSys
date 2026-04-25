KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買／リサーチ／モニタリングのための内部ライブラリおよび起動スクリプト群です。  
本リポジトリには、実行エンジン（ExecutionEngine）・監視（Monitoring）・ポートフォリオ構築・ファクター計算・AI ベースのニュース評価などの主要コンポーネントが含まれます。ライブラリとして他モジュールから関数を呼び出して利用することも、付属の CLI スクリプトでバッチ実行することもできます。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBroker for paper trading）
  - リスク管理・注文管理・照合（reconciler）統合
- Monitoring（run_monitoring.py / monitoring package）
  - システム稼働状況、データ鮮度、注文・リスクの監視
  - Kill Switch（条件により ExecutionEngine を停止するフラグ）
  - アラート送信（LINE 等に通知可能）
- Portfolio（portfolio package）
  - 候補選定、重み付け、ポジションサイズ計算、セクター上限・レジーム補正
- Research（research package）
  - ファクター計算（Momentum / Volatility / Value）、将来リターン、IC 計算、統計サマリー
  - DuckDB を利用した高速な分析パイプライン
- AI モジュール（ai package）
  - ニュース記事の LLM によるセンチメントスコアリング（OpenAI）
  - マクロニュースと ETF MA を使った市場レジーム判定
- ユーティリティ
  - 環境設定ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成ツール
  - ロギング・プロセス優先度設定ユーティリティ

前提
----
- Python 3.9+ を推奨（typing の記載と依存ライブラリ互換性を考慮）
- 主要依存ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の検証に任意）
  - （pip の要件ファイルがある場合はそちらを利用してください）

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存関係をインストールします（例）。
   - pip install duckdb psutil openai PyYAML

   ※ 実運用では requirements.txt / Poetry 等を用いて依存管理してください。

3. .env の作成
   - 対話式ウィザードを使う（推奨）:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動作成
   - 自動ロード:
     - config.py はプロジェクトルート（.git または pyproject.toml）を起点に .env を自動で読み込みます。
     - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 設定検証（起動前に実行することを推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合は --strict を付与します。

重要な環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: MockBroker を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（ai モジュール利用時に必要）
- LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（0/1、本番では 0 推奨）

使い方
------

基本的な起動例
- ExecutionEngine（実行エンジン）を起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、data/paper_trading.db に記録します。
  - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は pid ファイル（デフォルト data/execution.pid）が作成されます。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は環境にかかわらず production 用の sqlite_path（Settings.sqlite_path）を使用します。
  - 停止させるにはプロジェクトルートの data/stop_requested.flag を作成するか、KeyboardInterrupt（Ctrl+C）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定可能）

Kill Switch / 停止フロー
- KillSwitch（監視側）によって data/kill.flag が書き込まれると ExecutionEngine 側は停止シグナルとして参照できます。
- KillSwitch は drawdown やポジション上限などの条件で flag を書き込みます。
- ExecutionEngine 側は起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を自動クリアします（本番では 0 推奨）。

ログ
- デフォルトでコンソール出力（stdout）と日次ローテートされたファイルログ（logs/<app_name>.log）を使用します。
- ログ周りは kabusys.utils.logging_setup.setup_logging を通して統一的に設定されます。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト logs/ を使用します。

ライブラリとしての使い方（抜粋）
- 研究系関数（DuckDB 接続を渡す）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - conn = duckdb.connect("data/kabusys.duckdb")
  - calc_momentum(conn, target_date)
- ポートフォリオ関数
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- AI（ニューススコアリング）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")

設定検証とトラブルシュート
- 必須環境変数や設定ファイル（config/*.yaml）の存在は python -m kabusys.validate_config で事前に検証してください。
- .env の初期化は python -m kabusys.config_setup で対話的に作成できます。
- DuckDB / SQLite のパスが親ディレクトリごと存在しない場合は警告が出ますが、起動時に自動作成されることがあります。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys の主要なファイル・ディレクトリ（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / 設定読み込みロジック
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリング起動スクリプト
    - monitoring/
      - __init__.py
      - monitoring_db.py        — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - ai/
      - news_nlp.py
      - regime_detector.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py
    - tools/
      - paper_verification_report.py
      - __init__.py

補足（実装上の注意）
- 設定自動読み込み: config.py はプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数を保護）。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_execution は KABUSYS_ENV=paper_trading 時に paper_trading 用 DB を使用し、本番 DB と分離します。
- run_monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用します（監視ログを一元管理するため）。
- OpenAI を利用する AI モジュールは API の失敗に対してリトライ・フォールバックを組み込んでいますが、API キー未設定時は例外を投げます。

ライセンス・貢献
----------------
（ここにライセンスや contrib 方針を追記してください）

以上が本リポジトリの概要・セットアップ・使い方の要点です。詳細は各モジュールの docstring を参照してください。README に含めてほしい追加情報（依存関係の固定方法、CI 設定例、運用手順など）があれば指示してください。