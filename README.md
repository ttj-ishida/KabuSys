README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を持つコンポーネントで構成されています。

- 実行エンジン（ExecutionEngine）: 注文送信、注文管理、リスク管理を実行
- モニタリング（Monitoring）: システム健全性・注文・リスクの監視、Kill Switch 発動
- ポートフォリオ構築（Portfolio）: 候補選定・重み付け・ポジション算出ロジック
- リサーチ（Research）: ファクター計算、特徴量探索、将来リターン / IC 計算
- AI モジュール（AI）: ニュースの NLP スコアリング / レジーム判定（OpenAI）
- ユーティリティ: ログ設定、プロセス優先度設定、環境設定ウィザード、設定検証、解析ツール等

設計方針の要点:
- DuckDB / SQLite を用いたオンディスクデータ操作（分析用と監視用で分離）
- 実行 & 監視はプロセス分離。flag ファイルによる停止制御（data/kill.flag / stop_requested.flag）
- 環境変数 / .env による設定管理。config_setup と validate_config で導線を提供
- OpenAI を使う処理は API キーを外部から与える（環境変数 OPENAI_API_KEY）

主な機能一覧
-------------
- 環境セットアップ:
  - .env 対話式ウィザード: kabusys.config_setup.run_wizard
  - 設定検証 CLI: kabusys.validate_config
- 実行系:
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading モードと live を切替）
    - paper_trading の場合は MockBroker を使用し、data/paper_trading.db に記録
  - BrokerClientFactory によりブローカークライアントを抽象化
- 監視系:
  - run_monitoring.py: SystemMonitor ポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System / Trade / Risk モニタを束ね、KillSwitch・Alert を管理
  - kill_switch.py: 条件に応じて data/kill.flag を書き込むことで ExecutionEngine を停止
- ポートフォリオ構築:
  - 候補選定（select_candidates）、等金額 / スコア重み（calc_equal_weights / calc_score_weights）
  - セクターキャップ適用（apply_sector_cap）、レジーム乗数（calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）
- リサーチ:
  - ファクター計算（momentum / value / volatility）
  - 将来リターン、IC、統計サマリ（feature_exploration）
- AI:
  - news_nlp.score_news: raw_news を OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.score_regime: ETF MA とマクロニュースを組み合わせレジーム判定
- ツール:
  - tools.paper_verification_report: ペーパートレード DB を解析して検証レポートを生成

前提条件（依存）
----------------
最低限必要なパッケージ（一部は機能により任意）:
- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config *.yaml の検証をする場合）
インストール例:
- pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
     （requirements.txt が無ければ下記を個別インストール）
   - pip install duckdb psutil openai PyYAML

3. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成
   - 注意: .env は機密情報を含むため絶対に Git にコミットしないこと

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告でもエラー扱いで終了する:
     - python -m kabusys.validate_config --strict

5. データ・ログディレクトリ作成（必要なら）
   - デフォルト DB / ログパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
   - 必要に応じてディレクトリを作る:
     - mkdir -p data logs

基本的な使い方
--------------
- 実行エンジン（本番/ペーパー）の起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV が paper_trading の場合、MockBroker を使用して data/paper_trading.db を利用します
    - プロセス優先度を high に設定し、PID ファイル（デフォルト data/execution.pid）を管理します
    - 停止は data/stop_requested.flag を作成するか、kill.flag による停止が行われます（Kill Switch）

- 監視ループの起動
  - python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は共通）
    - 監視中に data/stop_requested.flag を作成するとループを終了します

- 環境設定ウィザード
  - python -m kabusys.config_setup
    - .env を対話式に生成 / 更新します

- 設定検証
  - python -m kabusys.validate_config
    - 必須環境変数や config/*.yaml の存在・パースをチェックします

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db または 環境変数 PAPER_TRADING_SQLITE_PATH で指定

主要な環境変数
----------------
（主要なものを抜粋）

必須（起動前に設定が必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / 任意:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB の保存先（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1）

安全上の注意
-------------
- .env に機密情報（API キー、パスワード）を保存します。絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は特に注意: validate_config は警告を出します。LINE 通知の設定等を確認してください。
- KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に既存の kill.flag が削除されます。運用上危険なため本番では 0 を推奨します。
- run_monitoring は監視 DB に対して常に本番 sqlite_path を使います（環境に依存しない設計）。テスト時は DB パスを切り替えてください。

トラブルシューティング
---------------------
- ログディレクトリ作成失敗:
  - 権限問題で logs/ の作成に失敗した場合はコンソール出力のみになります。LOG_DIR を調整してください。
- DuckDB / SQLite ファイル作成エラー:
  - 指定パスの親ディレクトリが存在しない場合は警告が出ます。事前に data/ を作成してください。
- OpenAI 関連エラー:
  - OPENAI_API_KEY が未設定だと AI 機能は失敗して例外を投げる設計です。テストではモック可能です。
- psutil 関連:
  - process priority / cpu affinity の設定は権限が必要な場合があります。失敗すると警告ログでスキップされます。

ディレクトリ構成
-----------------
リポジトリの主要なファイル/フォルダ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env ウィザード CLI
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングループ
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (存在する場合)
    - execution/                — Execution 関連（Broker, Engine, OrderManager 等）
    - portfolio/
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - data/ (runtime)
      - monitoring.db (SQLite, 監視ログ)
      - paper_trading.db (SQLite, ペーパートレード)
      - kabusys.duckdb (DuckDB)
      - execution.pid / stop_requested.flag / kill.flag
- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  （テンプレートは scripts/ 等で生成される想定）

開発・拡張メモ
---------------
- テスト:
  - 各モジュールは純粋関数や副作用を最小化する設計になっているため、ユニットテストが書きやすいです。OpenAI 呼び出しや psutil 呼び出しは patch / monkeypatch で差し替えてください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成と簡易マイグレーションを行います。将来的なスキーマ変更はここに反映します。
- ログ:
  - setup_logging は stdout と 日次ローテートファイルを設定します。ログレベル・出力先は環境変数で制御できます。
- AI:
  - news_nlp と regime_detector は外部 API に依存するため、レート制限や失敗時のフォールバック（0.0）を実装しています。バッチサイズやリトライ戦略は定数で調整可能です。

ライセンス
----------
（プロジェクトのライセンス情報をここに記載してください）

以上。必要であれば、各モジュールの使用例や設定例（.env のサンプル）を追加で作成します。どの部分を詳細化したいか教えてください。