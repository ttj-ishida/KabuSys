KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。取引実行エンジン、監視／アラート機構、ポートフォリオ構築・ポジションサイズ計算、リサーチ（ファクター計算・特徴量解析）、および OpenAI を用いたニュース NLP / レジーム判定などの機能を備えています。設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの回避」「外部 API 呼び出しのフェイルセーフ化」を重視しています。

主な特徴
--------
- ExecutionEngine（発注実行）：
  - 本番 / ペーパートレードを環境変数 KABUSYS_ENV で切り替え（paper_trading では MockBroker を使用し DB を分離）
  - リスク管理（Rate limit、ポジション上限、ドローダウン等）
- Monitoring：
  - SystemMonitor / TradeMonitor / RiskMonitor を統合した MonitoringEngine
  - Kill Switch（条件を満たすと data/kill.flag を書き込み Execution を停止）
  - 監視ログを SQLite（デフォルト data/monitoring.db）に永続化
- ポートフォリオ構築モジュール：
  - 候補選定、等金額・スコア重み配分、セクター制限、レジーム乗数、単元株丸め等
- Research：
  - DuckDB 上で動作するファクター計算（モメンタム、ボラティリティ、バリュー等）や IC 計算、特徴量サマリ
- AI（OpenAI）統合：
  - ニュース記事のセンチメントスコアリング（gpt-4o-mini を想定）
  - マクロニュース + ETF（1321）MA乖離を合成した市場レジーム判定
  - API 呼び出しはリトライやフェイルセーフ処理を備える
- ユーティリティ：
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - .env ウィザード（対話式）と設定検証 CLI
- ツール：
  - ペーパートレードの検証レポート生成スクリプト（Paper Trading 検証）

セットアップ手順
---------------
以下は簡易セットアップ手順の例です。実行環境や好みに応じて調整してください。

1. リポジトリをクローン／チェックアウト
   - プロジェクトルートには src/ 配下にパッケージが配置されています。

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - （YAML 検証を行う場合）pip install pyyaml

   ※ requirements.txt がある場合はそちらを使用してください。

4. ディレクトリ作成
   - データ格納先やログディレクトリを作成します（スクリプトでも自動生成されますが事前に用意しておくと安心です）。
     - mkdir -p data logs

5. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を手動で作成してください。

主要な環境変数（例）
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 設定例:
  - KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR
  - OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
  - KILL_FLAG_CLEAR_ON_START: 0（本番では 0 推奨）

使い方（コマンド例）
------------------

- 環境設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit(1)）になります

- 実行エンジン起動（本番 / ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution

  動作メモ:
  - KABUSYS_ENV=paper_trading の場合、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使用し、本番 DB とは分離します。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行エンジンは data/execution.pid に PID を書きます。停止要求は stop_requested.flag を作成することで行えます（監視側とも連携）。

- 監視ループ起動
  - python -m kabusys.run_monitoring

  動作メモ:
  - デフォルトのポーリング間隔は 60 秒。環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視は monitoring DB（Settings.sqlite_path、デフォルト data/monitoring.db）にログを残します。
  - 監視ループの停止は data/stop_requested.flag を作成するか Ctrl+C。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （env PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要です。該当関数は kabusys.ai モジュールを介して呼び出します。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime（プログラムから呼び出す）

運用上のフラグ / ファイル
------------------------
- data/stop_requested.flag
  - run_execution / run_monitoring がポーリングループで検知して終了するためのフラグ（存在すると起動抑止や停止動作を行います）。

- data/kill.flag
  - KillSwitch によって書き込まれると、ExecutionEngine に対して停止を要求するためのファイル（Settings.kill_flag_clear_on_start で起動時に自動クリアする設定あり）。

- data/execution.pid
  - ExecutionEngine が起動時に自身の PID を書き込みます。

ロギング
--------
- 標準でコンソール（stdout）と日次ローテートのファイル出力（logs/<app_name>.log）を行います。
- ログレベルは LOG_LEVEL、ログディレクトリは LOG_DIR 環境変数で変更可能です。
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要モジュールと簡単な説明です。

- run_execution.py
  - ExecutionEngine を起動するエントリポイント（python -m kabusys.run_execution）。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト（python -m kabusys.run_monitoring）。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を指定可能。

- config.py
  - 環境変数の読み出し・検証を行う Settings クラス（.env の自動ロード機能あり）。

- config_setup.py
  - 対話式 .env 生成ウィザード。

- validate_config.py
  - 起動前の設定検証ツール（必須環境変数、YAML ファイル有無、パスの存在チェック等）。

- monitoring/
  - monitoring_db.py: SQLite を用いた監視ログ永続化 API（テーブル作成・読み書き）。
  - system_monitor.py: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス生存チェック。
  - risk_monitor.py: ドローダウン・ポジション上限監視。
  - trade_monitor.py: （発注ログ監視: ファイル内に実装あり）。
  - monitoring_engine.py: 各 Monitor を束ねるエンジン。
  - kill_switch.py: kill.flag の生成／管理。
  - alert_manager.py: 通知送信（LINE など、実装参照）。

- execution/
  - execution_engine.py: 実際の発注ループとセッション管理（EngineConfig 等）。
  - broker_factory.py: 本番/Mock ブローカーを生成。
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py: 発注・注文管理・再突合・リスク制御に関する実装。

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算。
  - position_sizing.py: 発注株数計算（単元丸め・集約キャップ処理等）。
  - risk_adjustment.py: セクター上限・レジーム乗数。

- research/
  - factor_research.py: モメンタム・バリュー・ボラティリティ等のファクター計算（DuckDBベース）。
  - feature_exploration.py: 将来リターン・IC・統計サマリ等。

- ai/
  - news_nlp.py: ニュース記事をまとめて OpenAI に送り、銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込む。
  - regime_detector.py: ETF（1321）MA乖離 + マクロ記事センチメントを合成して日次レジーム判定。

- tools/
  - paper_verification_report.py: ペーパートレード DB から検証レポートを生成。

- utils/
  - logging_setup.py: ログ初期化ユーティリティ。
  - process_priority.py: プラットフォームに依存しないプロセス優先度 / CPU affinity 設定。
  - ほか共通ユーティリティ群。

補足 / 運用注意
----------------
- 本番運用時は KABUSYS_ENV=live を慎重に設定してください（validate_config で警告が出ます）。
- kill_flag（自動クリア等）やログレベル設定などは本番と開発で差をつけることを推奨します。
- OpenAI を使用する機能は API コストとレスポンスの可用性に依存します。API キーの保護と呼び出し制御（バッチサイズ・リトライ設定）に注意してください。
- データベースファイルやログファイルは適宜バックアップ・ローテーションを検討してください（duckdb は大容量データに有効）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）。
- ライセンスや貢献ガイドラインはリポジトリのルートに別途用意してください（本 README には含まれていません）。

この README はコードベースから自動生成された要約です。詳細は各モジュールの docstring / ソースを参照してください。追加で「導入手順の具体的な requirements.txt の作成」「運用 runbook（サービス化 / systemd / supervisor）」などが必要であれば支援します。