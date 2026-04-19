# KabuSys

日本株向けの自動売買／リサーチ支援ライブラリ群および起動スクリプト群です。  
本リポジトリには、実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター算出、AI を用いたニュース評価などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような関心事を分離して実装した自動売買システムのコードベースです。

- 実行エンジン（発注・注文管理・リスク管理）
- 監視サブシステム（システム状態、注文状況、リスク監視、Kill Switch）
- ポートフォリオ構築（シグナル選定・重み算出・単元丸め）
- リサーチ（ファクター計算、特徴量解析）
- AI 関連（ニュースセンチメント、レジーム判定）
- 運用補助スクリプト（.env 作成ウィザード、設定検証、ペーパートレード検証レポートなど）

設計上の留意点：
- 環境変数を .env / .env.local から自動読み込み（プロジェクトルートを検出）します。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離して data/paper_trading.db を利用します。
- 監視は環境にかかわらず本番 sqlite_path を使用します（monitoring 用 DB の永続化）。

---

## 主な機能一覧

- run_execution.py: ExecutionEngine を起動（実際の発注/モック発注を設定に従って切替）
  - Paper trading 時は MockBrokerClient を用い、paper_trading DB に記録
  - PID ファイル管理／stop フラグ検出による停止処理
- run_monitoring.py: SystemMonitor のポーリングループ起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き（デフォルト 60 秒）
  - システムリソース監視（CPU/メモリ/ディスク）、データ鮮度チェック、プロセス生存チェック
- monitoring モジュール群:
  - MonitoringDB（SQLite を利用した永続化）
  - RiskMonitor（ドローダウン・ポジション数監視）
  - TradeMonitor / SystemMonitor / KillSwitch / MonitoringEngine / AlertManager（アラート送信は設定に応じて実装）
- portfolio モジュール:
  - 候補選定、重み算出、ポジションサイズ算出、セクターキャップ適用、レジーム乗数
- research モジュール:
  - momentum / volatility / value 等のファクター計算、将来リターン計算、IC（スピアマン）等
- ai モジュール:
  - news_nlp.score_news: ニュースを LLM（OpenAI）でセンチメント評価して ai_scores に保存
  - regime_detector.score_regime: ETF の MA200 とマクロニュースで市場レジーム判定
- tools:
  - paper_verification_report: ペーパートレード DB から検証レポートを出力
- 設定支援:
  - config_setup.py: .env を対話式で作るウィザード
  - validate_config.py: 起動前に環境変数・config/*.yaml を検証

---

## セットアップ手順

1. Python 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必須パッケージ（例）
   - pip install duckdb psutil openai
   - （YAML 検証を行う場合）pip install pyyaml

   補足:
   - sqlite3 は標準ライブラリに含まれます。
   - OpenAI API を使う機能を利用する場合は openai パッケージが必要です。
   - logging 用のファイル出力先ディレクトリ（logs）や DB 用ディレクトリ（data）は自動作成されますが、必要に応じて手動で作成できます。

3. 初期設定
   - python -m kabusys.config_setup
     - 対話式に .env を作成します（生成された .env は絶対に Git にコミットしないでください）。
   - 作成後、設定検証:
     - python -m kabusys.validate_config
     - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

4. ディレクトリ書き込み許可
   - data/ および logs/ に対して実行ユーザーが書き込み可能であることを確認してください。

---

## 主要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な設定:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
  - paper_trading の場合、発注はモック・DB は data/paper_trading.db
- OPENAI_API_KEY: AI 機能（news_nlp / regime_detector）で使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログファイル保存先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: paper trading の約定モード（instant / partial / never / reject）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行制御関連

自動読み込み:
- プロジェクトルートに .env/.env.local があれば自動で読み込まれます（CWD ではなく当該パッケージ位置を基準に検出）。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方（実行例）

- .env を生成・編集:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジンを起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使い MockBroker を利用します。
    - 実行はデーモンや systemd / supervisor などで管理する想定です。
    - 停止方法: プロジェクトルートの data/stop_requested.flag を作成すると起動中のループが検知して停止します。

- 監視プロセスを起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL（秒）でポーリング。例: export MONITOR_POLL_INTERVAL=30
    - 監視は本番 sqlite_path を使用します（環境に依らず同じ監視 DB を参照）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db で指定可能。

- AI 関連（プログラム内呼び出し例）
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="...")

  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意:
- OpenAI 呼び出しは API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。
- AI 呼び出しは外部 API 呼び出しのため、失敗時はフォールバックが入る設計ですが、API 利用料およびレート制限に注意してください。

---

## 停止・Kill Switch の仕組み

- 軽い停止要求:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring は次回ループで検知して終了します。

- Kill Switch:
  - monitoring の評価により条件を満たすと data/kill.flag が書き込まれます（ExecutionEngine に対する停止シグナル）。
  - ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定に従い kill.flag を消去することがあります（本番では自動クリアは推奨されない）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル例です。

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数 / 設定管理
    - config_setup.py            # .env 対話式ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py          # SystemMonitor ポーリング起動スクリプト
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py

プロジェクトルートには以下のような補助ファイル/ディレクトリが想定されます:
- .env, .env.local （環境変数）
- config/*.yaml（各種設定テンプレート）
- data/（SQLite・PID・フラグファイルなど）
- logs/（ログファイル）

---

## 開発上の注意点

- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブル作成と簡単なカラム追加マイグレーションを行います。
- モジュール設計: 多くの関数は副作用を持たない純粋関数として設計されています（特に portfolio / research）。
- ロギング: 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出して統一的にログ出力します。ログは stdout と日次ローテーションされるファイルの両方へ出力されます。
- プロセス優先度: 起動時に set_process_priority("high") を試行します（アクセス権がない場合は警告を出してスキップ）。
- セキュリティ: .env は機密情報を含むため Git に含めないでください。

---

もし README に追記したい実行例や、各モジュールの API ドキュメント（関数の使い方や引数の詳細）があれば、その箇所を書いていただければ追補いたします。