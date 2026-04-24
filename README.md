README
=====

概要
----
KabuSys は日本株の自動売買・研究プラットフォーム用のモジュール群です。  
以下の主要機能を持ち、ローカル開発・ペーパートレード・本番（live）に対応する設計になっています。

主な設計方針:
- DuckDB を用いたファクター計算／研究用処理
- SQLite を用いた監視・発注ログの永続化
- 環境変数 / .env による設定管理（対話式ウィザード有り）
- OpenAI（gpt-4o-mini 等）を利用したニュース NLP / レジーム判定（任意）
- ペーパートレード時は本番 DB と分離（data/paper_trading.db）

機能一覧
--------
- 環境設定
  - 対話式 .env ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
- 実行エンジン起動
  - 実際の ExecutionEngine を起動する run_execution スクリプト
  - KABUSYS_ENV=paper_trading 時は MockBroker を利用して paper_trading DB を使用
- 監視（Monitoring）
  - System / Trade / Risk モニタを束ねる監視ループ（run_monitoring）
  - Kill Switch（閾値超過時に data/kill.flag を書き込み、Execution を停止）
- ポートフォリオ構築（純粋関数群）
  - 候補選定、重量計算、ポジションサイズ計算、セクター制約、レジーム乗数
- 研究モジュール
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC 計算、統計サマリー
- AI 関連
  - ニュースの NLP スコア化（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

必須 / 主な環境変数（抜粋）
-------------------------
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な任意 / デフォルト（Settings を参照）:
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db (paper_trading 時に使用)
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 0 or 1（デフォルト 0）
- OPENAI_API_KEY: OpenAI を使う処理で必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の振る舞い）

セットアップ手順
--------------
1. リポジトリをクローンし、Python 仮想環境を作成:
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール（プロジェクトに requirements.txt がない場合は主要ライブラリを個別に）:
   - pip install duckdb psutil openai
   - 任意: pip install PyYAML（validate_config の YAML 検証に使用）

3. 環境変数ファイル（.env）を作成:
   - 対話式ウィザードで作成: python -m kabusys.config_setup
   - もしくは .env.example を参照して手動作成

4. 設定を検証（オプション）:
   - python -m kabusys.validate_config
   - 厳格モード（警告もエラー扱い）: python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）:
   - mkdir -p data logs

基本的な使い方
-------------
起動・運用に関する主なコマンド例を示します。

- ExecutionEngine を起動する（本番 / 開発 / paper_trading に依存）:
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が既に存在する場合は起動を行わず終了します。
  - 実行中、停止したい場合はデータディレクトリに stop ファイルを置くか ExecutionEngine の API を利用する運用を行ってください（run_execution は data/stop_requested.flag を監視して停止します）。

- Monitoring を起動する:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）
  - 監視は本番の sqlite_path（Settings.sqlite_path）を使用してログを残します（環境に関係なく）。

- Paper Trading 検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定する例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュールの実行（プログラム的に呼ぶ方法）:
  - ニューススコア算出:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="your_openai_key")
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="your_openai_key")

ログとファイル
--------------
- ログ:
  - ログは kabusys.utils.logging_setup.setup_logging により統一管理されます。
  - デフォルトのログディレクトリ: logs/
  - 起動スクリプトごとに logs/<app_name>.log に日次ローテートで保存されます（例: logs/execution.log, logs/monitoring.log）。
  - ログレベルは環境変数 LOG_LEVEL または setup_logging の引数で制御できます。

- DB:
  - DuckDB（分析用）: data/kabusys.duckdb（DUCKDB_PATH）
  - SQLite（監視用）: data/monitoring.db（SQLITE_PATH）
  - Paper Trading 専用 SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）

- 制御フラグ類:
  - data/stop_requested.flag: run_* スクリプトがこのファイルの有無を見てループを終了します（run_monitoring, run_execution がチェック）。
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止指示を与える（Execution 起動時に読み取り、オプションで自動クリア設定あり）。

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では LINE トークン等の通知設定を必ず確認してください（validate_config で警告が出ます）。
- KILL_FLAG_CLEAR_ON_START は本番で 1 を設定すると危険です（自動クリアされるため）。デフォルトは 0。
- Paper Trading モードでは本番 DB と完全分離されるため、実際の発注は行われませんが挙動は検証できます。
- OpenAI を利用する処理は API キーとコストが必要です。API キーは OPENAI_API_KEY 環境変数で設定します。

ディレクトリ構成
----------------
（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings クラス（.env 自動ロード機能あり）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に格納
    - regime_detector.py — マクロ + ETF MA で市場レジーム判定
  - monitoring/
    - monitoring_db.py — SQLite 監視 DB 初期化＋永続化レイヤ
    - system_monitor.py — システム状態 / データ鮮度監視
    - trade_monitor.py — （発注ログ監視／コード参照）
    - risk_monitor.py — ドローダウンやポジション上限監視
    - kill_switch.py — kill.flag の作成・管理
    - monitoring_engine.py — 各 Monitor を束ねる実行エンジン
    - alert_manager.py — （LINE など通知ロジック）※実装参照
  - execution/
    - execution_engine.py — ExecutionEngine 本体（起動・セッション管理）
    - broker_factory.py — BrokerClient の生成（実ブローカ / モック切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注／リスク管理周り
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算
    - feature_exploration.py — IC 計算等の解析ユーティリティ
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定

補足情報 / よくある質問
-----------------------
- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml の存在）を基に行われます。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- validate_config は PyYAML がある場合に config/*.yaml の内容もチェックします。インストールされていない場合は YAML の検証をスキップして警告を出します。
- run_monitoring は監視ログ用の sqlite DB の初期化（テーブル作成・マイグレーション）を自動で行います（init_monitoring_db）。

問い合わせ / 開発
-----------------
コード内のドキュメント文字列（docstring）に多くの仕様・設計意図が書かれています。各モジュールを参照して用途や API を確認してください。Issue や PR を通じて改善を歓迎します。

以上。