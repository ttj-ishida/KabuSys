KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株の自動売買システム（KabuSys）のコア部分を実装した Python パッケージです。  
本 README はコードベースの主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
---------------
KabuSys は以下の主要機能を持つモジュール群で構成されています。

- 注文執行エンジン（ExecutionEngine） — ブローカークライアントを通じた発注、注文管理、リスク管理、再整合処理
- 監視（Monitoring） — システム稼働状況、データ鮮度、注文ログ、リスク（ドローダウン・保有上限）を定期チェックし、必要に応じて Kill Switch を発動
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、単元株丸め、リスク調整（セクター上限、レジーム乗数等）
- リサーチ（Research） — ファクター計算（モメンタム、バリュー、ボラティリティ）、将来リターン・IC 計算、特徴量探索
- AI 補助（AI） — ニュースの NLP スコアリング（OpenAI）や市場レジーム判定（LLM を利用）
- ユーティリティ群 — ロギング設定、プロセス優先度設定、設定読み込みウィザード、設定検証ツール 等
- ツール群 — ペーパートレード検証レポート等の CLI スクリプト

機能一覧
--------
主な機能と該当ファイル（抜粋）:

- 設定管理
  - 自動 .env 読み込み / Settings クラス: src/kabusys/config.py
  - 対話式設定ウィザード: src/kabusys/config_setup.py
  - 設定検証 CLI: src/kabusys/validate_config.py

- 実行・運用
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading.db に記録
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
  - Kill Switch（data/kill.flag）により Execution を停止可能: src/kabusys/monitoring/kill_switch.py

- 監視（Monitoring）
  - 監視 DB 初期化・永続化: src/kabusys/monitoring/monitoring_db.py
  - System / Trade / Risk モニタ, MonitoringEngine: src/kabusys/monitoring/*.py
  - アラート送信管理（LINE など）: alert_manager（実装箇所参照）

- ポートフォリオ構築
  - 候補選定・重み計算: src/kabusys/portfolio/portfolio_builder.py
  - リスク調整（セクターキャップ、レジーム乗数）: src/kabusys/portfolio/risk_adjustment.py
  - ポジションサイズ計算（単元丸め・aggregate cap）: src/kabusys/portfolio/position_sizing.py

- リサーチ
  - ファクター計算（momentum/value/volatility）: src/kabusys/research/factor_research.py
  - 特徴量探索・IC 計算等: src/kabusys/research/feature_exploration.py

- AI（OpenAI）
  - ニュース NLP によるセンチメントスコアリング（ai_scores へ書込）: src/kabusys/ai/news_nlp.py
  - マクロニュース＋ETF MA200 を用いた市場レジーム判定: src/kabusys/ai/regime_detector.py

- ツール
  - Paper Trading 検証レポート生成: src/kabusys/tools/paper_verification_report.py

セットアップ手順
----------------
前提
- Python 3.9+（実行環境に合わせて）
- ネットワーク接続（OpenAI API 利用時）
- システム依存ライブラリ: duckdb, psutil, openai, PyYAML（任意） 等

推奨インストール手順（例）
1. 仮想環境作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 公式の requirements.txt がない場合は最低限以下を pip で入れてください:
     - pip install duckdb psutil openai PyYAML
   - 実際の依存は実行する機能によって異なります（AI 機能は openai、YAML 検証は PyYAML）。

3. プロジェクトルートに移動し、初期ディレクトリ/ファイルを作成
   - mkdir -p data logs
   - （必要に応じて）touch data/stop_requested.flag を利用してプロセス停止検査を行うことができます（通常は存在しない状態）。

4. .env を用意
   - 対話式で .env を生成:
     - python -m kabusys.config_setup
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - OPENAI_API_KEY （AI 機能を使う場合）
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗として扱い exit(1)

使い方
------
実行スクリプト（モジュール実行）

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は settings.sqlite_path（デフォルト data/monitoring.db）に接続し、monitoring DB テーブルを初期化します。
  - 監視ループは data/stop_requested.flag の存在を検知すると終了します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（default: data/paper_trading.db）へ記録します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
  - 実行中は data/execution.pid に PID を書きます。

- 設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を生成・更新します。

- 設定検証
  - python -m kabusys.validate_config
  - 起動前に必要な環境変数や config/*.yaml の妥当性チェックを行います（PyYAML があると YAML のパース検証も行います）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill Switch
- 監視/実行プロセスの外部停止:
  - run_monitoring / run_execution はプロジェクトルートの data/stop_requested.flag をチェックして終了します。停止させたい場合はそのファイルを作成してください（実運用では別の安全な方法で制御することを推奨）。
- Kill Switch:
  - RiskMonitor 等が条件を満たすと data/kill.flag を作成します。ExecutionEngine はこのファイルを検知して安全に停止する設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では危険なので 0 を推奨）。

ログ
- ログはデフォルトで標準出力と logs/<app_name>.log（日次ローテーション、30日保持）へ出力されます。
- 環境変数 LOG_DIR / LOG_LEVEL を指定可能。ロガー初期化は各スクリプトで setup_logging(app_name=...) を呼び出しています。

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合に必須
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- LOG_DIR: ログ保存先（デフォルト: logs）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

ディレクトリ構成（抜粋）
---------------------
リポジトリ内の主要ファイル・ディレクトリ構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — 監視ループ起動スクリプト
  - run_execution.py          — 実行エンジン起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py        — monitoring DB 初期化 + 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （実装に依存）
  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

補足・注意事項
--------------
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は起動時にテーブルと必要なカラムを作成／マイグレートします（冪等性あり）。
- AI 機能:
  - OpenAI API を呼ぶコードはリトライ・バックオフやレスポンスのバリデーションを行う設計ですが、API キーの管理や利用料に注意してください。
- 本番運用時の注意:
  - KABUSYS_ENV=live の場合は十分なガード（LINE 通知、kill flag の扱い、リスク設定）を確認してください。
  - KILL_FLAG_CLEAR_ON_START=1 は本番での自動クリアは危険です（0 を推奨）。
- テスト・デバッグ:
  - development / paper_trading モードでは発注をモックする等の配慮がされています。コード内のモック実装や factory を確認してください。

最後に
-------
この README はコードベースの主要点をまとめたものです。詳細な実装や補助スクリプト、各モジュールの追加設定・運用手順は該当モジュールの docstring やコードコメントを参照してください。質問や追加のドキュメント化が必要であれば教えてください。