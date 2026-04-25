KabuSys
=======

日本株向け自動売買システムのライブラリ／起動スクリプト群です。  
バックテスト／リサーチ、ポートフォリオ構築、発注エンジン（本番／ペーパートレード切替）、監視・アラート、LLM を使ったニュースセンチメント評価などの機能を含みます。

この README ではプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
- モジュール群として構成され、ライブラリ API（例: kabusys.portfolio, kabusys.research, kabusys.ai）を提供します。
- 実際に稼働させるための起動スクリプトを含み、処理はローカル SQLite / DuckDB を用いて永続化・分析を行います。
- ペーパートレード環境と本番環境を分離して運用でき、監視エンジンやキルスイッチで安全性を担保します。

機能一覧
--------
- 環境設定ウィザード（.env の対話式作成）: kabusys.config_setup
- 設定検証 CLI（.env、config/*.yaml、パス等チェック）: kabusys.validate_config
- 発注エンジン起動スクリプト（ExecutionEngine）: run_execution.py
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、専用 DB に記録
- 監視プロセス起動スクリプト（Monitoring）: run_monitoring.py
  - システム状態・データ鮮度・注文ログ等を定期ポーリングして永続化・アラート
- 監視永続化層（SQLite）: monitoring_db.py
- リスク監視（ドローダウン、ポジション上限）: risk_monitor.py
- キルスイッチ（ファイル書き込みで ExecutionEngine 停止）: kill_switch.py
- モニタリング統合エンジン: monitoring_engine.py
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイジング等）
  - kabusys.portfolio: select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier
- リサーチ用モジュール（DuckDB 経由でファクター計算、IC 計算、特徴量解析）
  - kabusys.research: calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- AI 関連
  - ニュースのセンチメント評価（OpenAI）: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定（ma200 + マクロニュース LLM）: kabusys.ai.regime_detector.score_regime
- ツール
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report

前提・依存関係（主なもの）
-------------------------
- Python 3.9+（コードは型注釈を含むため 3.9+ を推奨）
- pip でインストールが必要な外部ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config YAML の内容検証を行う場合、なくても動作するがチェックはスキップされます）
- SQLite（標準ライブラリで利用）
（プロジェクト配布時に requirements.txt があればそちらを利用してください）

セットアップ手順
----------------

1. リポジトリをクローン / 展開
   - 本 README の前提はリポジトリルートに src/kabusys ディレクトリが存在する構成です。

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参照して .env を用意する（本リポジトリに例ファイルがあれば参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱いたい場合:
     - python -m kabusys.validate_config --strict

6. DB / ディレクトリ準備
   - デフォルトでは以下のファイルパスを使用します（変更は .env で可）:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/（デフォルト）
   - 起動時に必要なディレクトリは自動で作成される場合がありますが、権限に注意してください。

主な環境変数
--------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境
  - KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
- DB / ログ
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
  - LOG_LEVEL (例: INFO, DEBUG)
  - LOG_DIR
- AI
  - OPENAI_API_KEY (AI 機能を使う場合必須)
- 監視関連
  - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒、デフォルト 60)
  - PID_FILE_PATH (ExecutionEngine の pid ファイルパス、デフォルト data/execution.pid)
  - KILL_FLAG_PATH（Kill Switch の flag path、デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START (0/1)
  - PAPER_FILL_MODE (ペーパートレード時の fill 振る舞い: instant/partial/never/reject)

使い方（主要 CLI / 実行例）
--------------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告で失敗）:
    - python -m kabusys.validate_config --strict

- 監視プロセス起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  注意:
  - run_monitoring は KABUSYS_ENV にかかわらず production (settings.sqlite_path) の監視 DB を使用します。
  - 停止はプロジェクトルート/data/stop_requested.flag ファイルを作成することで安全にループを抜けます。

- 発注エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、data/paper_trading.db に書き込まれます（本番 DB と分離）。
  - 停止は data/stop_requested.flag により実行中エンジンに伝達されます。
  - 実行時は execution.pid（デフォルト data/execution.pid）に PID が書かれます。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- ライブラリ API の例
  - ポートフォリオ関数:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - AI スコアリング (ニュース):
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key="...")  # DuckDB 接続と target_date（date オブジェクト）を渡す
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

停止・キルスイッチ・ログ
-----------------------
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが安全に終了します（プロセスはこのフラグをポーリングして確認します）。
- キルスイッチ:
  - KillSwitch（data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを与えます（リスク閾値等により自動的に書き込まれることがあります）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 を強く推奨）。
- ログ:
  - デフォルトで logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）に日次ローテーションで出力されます。
  - コンソール出力は stdout に出ます。

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主要ファイル / モジュールです（完全な一覧はリポジトリ参照）。

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / 設定読み込みユーティリティ
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_monitoring.py        — 監視プロセス起動スクリプト
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py       — ログ初期化ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py       — SQLite 永続化層
      - system_monitor.py      — システム状態監視
      - trade_monitor.py       — 注文ログ監視（該当ファイルあり）
      - risk_monitor.py        — リスク監視（ドローダウン等）
      - kill_switch.py         — kill.flag 管理
      - monitoring_engine.py   — 複数モニタ束ねるエンジン
      - alert_manager.py       — 通知管理（LINE など）※実装ファイル参照
    - execution/
      - execution_engine.py    — 発注エンジン本体（EngineConfig, ExecutionEngine）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py            — ニュースセンチメント評価（OpenAI）
      - regime_detector.py     — 市場レジーム判定（ma200 + LLM）
    - tools/
      - paper_verification_report.py

補足事項・運用上の注意
--------------------
- 本番運用時は KABUSYS_ENV=live とし、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を適切に行ってください（validate_config にて注意喚起あり）。
- .env は絶対にバージョン管理にコミットしないでください（config_setup のヘッダにも記載あり）。
- AI 機能を用いる場合、OPENAI_API_KEY と API 利用のための費用に注意してください。API エラーは基本的にフェイルセーフ（スコア=0 など）で扱う実装になっていますが、運用監視は必須です。
- run_monitoring は監視 DB に対して常に（環境に関わらず） settings.sqlite_path を使用する点に注意してください（監視は実際の稼働情報を参照します）。

問題が発生した場合
------------------
- ログ（logs/）を確認してください。ログレベルは LOG_LEVEL 環境変数で調整できます。
- 設定の検証を行ってください: python -m kabusys.validate_config
- kill.flag / stop_requested.flag の存在を確認してください（これらのファイルでプロセスの挙動が変わります）。

ライセンス／貢献
----------------
- 本 README にはライセンス情報は含めていません。実際のリポジトリに LICENSE ファイルがある場合はそちらを参照してください。

以上が本リポジトリの概要と運用ガイドです。必要があれば README に載せるサンプル .env のテンプレートや詳細な運用手順（systemd 起動例、Docker 化のヒント等）を追加で作成します。希望があれば教えてください。