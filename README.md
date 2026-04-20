README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームの小規模実装です。
主な目的は以下のとおりです。

- 戦略・ポートフォリオ構築のためのファクター計算・特徴量探索機能（DuckDB ベース）
- ExecutionEngine による発注ロジック（実環境 / ペーパートレード切替）
- 監視（Monitoring）・アラート・Kill Switch による安全運用
- ニュースの LLM（OpenAI）によるセンチメント評価・レジーム判定
- ペーパートレード検証レポート生成

設計方針の要点:
- DB は DuckDB（分析用）と SQLite（監視・注文ログ）を併用
- 環境差（development / paper_trading / live）を Settings 経由で制御
- 実運用を想定したフェイルセーフ（API失敗時のフォールバック、ログ・ローテーション等）

主な機能一覧
----------------
- 環境設定ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- 監視コンポーネント
  - SystemMonitor（プロセス生存、CPU/MEM/DISK、データ鮮度）
  - TradeMonitor（発注ログ監視、滞留注文チェック 等）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringEngine（各 Monitor を束ねる）
  - KillSwitch（条件に応じて data/kill.flag を書き込み Execution を停止）
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・株数計算・セクター制限）
- 研究用モジュール（ファクター算出、Forward return、IC 等）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- ペーパートレード検証レポート生成ツール

依存関係（代表的なもの）
-----------------------
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に必要）
- sqlite3（標準ライブラリ）

requirements.txt が無い場合は上のパッケージをインストールしてください。
例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. リポジトリをクローンし、仮想環境を作成・有効化します。
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（上記参照）。
   - pip install -r requirements.txt   （requirements がある場合）
   - または: pip install duckdb psutil openai pyyaml

3. .env を作成します（対話式ウィザード推奨）。
   - python -m kabusys.config_setup
   ウィザードは .env を生成します。生成後は必ず内容を確認してください。
   注意: .env は絶対に Git にコミットしないでください（APIキー等を含むため）。

4. 設定検証を実行します。
   - python -m kabusys.validate_config
   --strict を付けると警告も FAIL 扱いになります。

主要な環境変数（Settings 参照）
--------------------------------
以下は重要な環境変数とデフォルト値の抜粋です（Settings クラスに実装あり）。

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- OPENAI_API_KEY: OpenAI を使う機能で必要（ai.score_news, regime_detector 等）
- DUCKDB_PATH: 分析用 DB（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（ペーパートレードでの約定挙動）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- PID_FILE_PATH / KILL_FLAG_PATH 等: デフォルト data/ 以下のファイルを参照

実行方法（代表例）
------------------

一般的にパッケージをモジュールとして起動します（パッケージが PYTHONPATH にある状態）。

1) 監視ループ起動（Monitoring）
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（秒、デフォルト 60）
   - python -m kabusys.run_monitoring
   特記事項:
     - 監視は Settings.env にかかわらず sqlite_path（本番監視 DB）を使用します。
     - 停止: data/stop_requested.flag を作成するとループが安全に停止します。

2) ExecutionEngine 起動（発注エンジン）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録して本番 DB と完全分離
   - python -m kabusys.run_execution
   特記事項:
     - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
     - 実行中は data/execution.pid にプロセス情報を保存します。

3) 環境設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

4) ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   オプション:
     --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
   環境変数: PAPER_TRADING_SQLITE_PATH を使えます（--db が優先）。

5) 研究・AI 機能（コード呼び出し）
   - kabusys.research.calc_momentum 等は DuckDB 接続を受け取って処理します。
   - AI 関連（kabusys.ai.news_nlp.score_news, kabusys.ai.regime_detector.score_regime）は OPENAI_API_KEY が必要です。

運用上のファイル・フラグ
-----------------------
- data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ
- data/kill.flag: KillSwitch が書き込むファイル。ExecutionEngine 停止トリガー
- data/execution.pid: Execution 起動時に書かれる PID ファイル
- logs/<app_name>.log: 日次ローテートされるログファイル（デフォルト logs/ ディレクトリ、30日分保持）

注意事項（安全・運用）
--------------------
- .env に秘密情報を含めるため、絶対に Git 等にコミットしないでください。
- KABUSYS_ENV=live は本番動作です。validate_config の警告・設定を厳重に確認してください。
- Kill Switch（KILL_FLAG）や stop_requested.flag は本番での緊急停止のため重要です。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（既存の Kill Switch を自動クリアしてしまうため）。
- OpenAI API 呼び出しはコストがかかります。テストはモック化して行うことを推奨します。

開発・テストに関するヒント
-------------------------
- テスト時には KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます。
- AI 呼び出しや外部 API 呼び出しは unittest.mock.patch で _call_openai_api 等をモックできます（コード内にその意図が明記されています）。
- DuckDB を使った関数は副作用を最小限にする設計です。ローカルの小さなデータセットで動作確認してください。

ディレクトリ構成（抜粋）
----------------------
以下は主要ファイルのツリー（src/kabusys を基準）。実際のリポジトリには他にもファイルが含まれる可能性があります。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・Settings
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_monitoring.py        # Monitoring ポーリング起動スクリプト
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       # ログ設定ユーティリティ
    - process_priority.py    # プロセス優先度 / CPU affinity
  - monitoring/
    - __init__.py
    - monitoring_db.py       # SQLite スキーマ・永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/                     # デフォルトの DB・フラグ配置（runtime に生成）
  - tools/
    - paper_verification_report.py

（注）上記は概観です。実際のファイルはリポジトリを参照してください。

付録: 便利なコマンド例
---------------------
- .env 作成:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 監視起動（デフォルト 60s 間隔）:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（ペーパートレード）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

おわりに
--------
本 README はコードベースの主要機能・運用方法をまとめたものです。実際の運用前に必ず validate_config による検証と小規模なドライランを行ってください。追加の質問やドキュメント化してほしい個別モジュールがあれば教えてください。