README
=====

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのサンプル実装です。  
主な目的は以下の通りです。

- シグナル生成・ポートフォリオ構築（portfolio モジュール）
- 発注実行エンジン（execution）
- 監視（monitoring）／Kill Switch による安全停止
- 研究用ファクター計算・特徴量解析（research）
- ニュース NLP によるセンチメント評価・レジーム判定（ai）
- ペーパートレード検証ツール（tools）

このリポジトリは、実行スクリプト・ユーティリティ・純粋関数群に分離された設計で、テスト・拡張がしやすいように構成されています。

主な機能一覧
--------------
- 環境設定ウィザード（python -m kabusys.config_setup）で .env を対話式に作成
- 起動前に設定検証（python -m kabusys.validate_config）
- ExecutionEngine（実際の発注 or Mock 発注）起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し DB は data/paper_trading.db に分離
- 監視プロセス（run_monitoring.py）
  - システム状態・データ鮮度・約定やリスクを定期的にチェック
  - kill.flag による Execution 停止判定、stop_requested.flag による監視停止
- Monitoring DB 層（SQLite）によるログ永続化（system_status, trade_logs, risk_logs, positions, dashboard）
- ポートフォリオ構築ユーティリティ
  - 候補選定（select_candidates）、等重/スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）／セクター制限やレジーム乗数（risk_adjustment）
- 研究向けファクター計算（DuckDB を用いた calc_momentum / calc_volatility / calc_value）
- ニュース NLP（OpenAI）を利用した銘柄別センチメント評価と market regime 判定
- ペーパートレード検証レポート生成（tools/paper_verification_report.py）

セットアップ手順
----------------

前提
- Python 3.9+（コードは型ヒントや一部モダンな標準機能を使っています）
- SQLite（標準ライブラリ）、DuckDB（Python パッケージ）、psutil、openai などが必要

1. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   必要な主要パッケージ（例）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config の YAML 検証を行いたい場合）
   例:
   - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合:
   - pip install -r requirements.txt

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   ウィザードは J-Quants / kabuAPI / DB パス 等の設定を手助けします。

   重要な環境変数（最低限設定が必要なもの）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD

   その他（例）
   - KABUSYS_ENV             (development | paper_trading | live) — デフォルト: development
   - DUCKDB_PATH             (例: data/kabusys.duckdb)
   - SQLITE_PATH             (監視 DB; 例: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB; 例: data/paper_trading.db)
   - OPENAI_API_KEY          (ai 機能を利用する場合必須)
   - LOG_LEVEL, LOG_DIR

   自動ロードを無効にしたい場合:
   - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合は --strict を付与

5. ログ / データディレクトリ
   - デフォルトの DB/ログ保存先はプロジェクト内の data/ や logs/ です。必要に応じて .env で上書きしてください。
   - ログは kabusys.utils.logging_setup により logs/<app_name>.log に日次ローテーションで出力されます。

使い方（起動コマンド例）
------------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- ExecutionEngine（本番／ペーパートレード）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading 用 DB に記録
    - 起動前に data/stop_requested.flag が存在すれば起動せず終了
    - 停止は data/stop_requested.flag を作成するか、ExecutionEngine が kill.flag を検出することで行われます

- Monitoring（常駐監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します
  - 停止: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI（ニュース NLP / レジーム判定）
  - AI 機能は OPENAI_API_KEY が必要です。
  - これらはライブラリ関数として提供されています（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）ので、スクリプトやスケジューラから呼び出して使います。

主な環境変数（要点）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD     (必須)
- KABUSYS_ENV           development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH           data/kabusys.duckdb（分析 DB）
- SQLITE_PATH           data/monitoring.db（監視 DB）
- PAPER_TRADING_SQLITE_PATH data/paper_trading.db（paper_trading 用 DB）
- OPENAI_API_KEY        OpenAI を使う場合に必須
- MONITOR_POLL_INTERVAL 監視ポーリング間隔（秒）
- LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_PATH など

運用上の注意
-------------
- 本番運用時は KABUSYS_ENV=live に設定しますが、live 設定では特に LINE 通知や Kill Switch の設定を確認してください（validate_config で一部警告が出ます）。
- monitoring は環境にかかわらず settings.sqlite_path を使用します（監視ログは本番 DB に記録されます）。
- paper_trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI 呼び出しは API エラーやレート制限に対してリトライを行いますが、API キーの管理（料金等）に注意してください。
- ローカルや CI で自動的に .env をロードしたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ディレクトリ構成
----------------
以下は src/kabusys 以下の主要ファイル／モジュールの一覧（抜粋）です。

- src/kabusys/
  - __init__.py                      パッケージ定義（__version__ 等）
  - config.py                         環境変数/設定読み込みロジック（Settings）
  - config_setup.py                   .env 対話式ウィザード
  - validate_config.py                起動前の設定検証 CLI
  - run_execution.py                  ExecutionEngine 起動スクリプト
  - run_monitoring.py                 Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py    ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py                     ニュース NLP による銘柄別スコアリング
    - regime_detector.py              マーケットレジーム判定（ma200 + マクロ NLP）
  - portfolio/
    - portfolio_builder.py            候補選定・重み計算
    - position_sizing.py              株数決定・資金配分・丸め
    - risk_adjustment.py              セクター上限・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py              momentum/volatility/value 等のファクター計算（DuckDB）
    - feature_exploration.py          将来リターン・IC 計算・統計サマリー
    - __init__.py
  - monitoring/
    - monitoring_db.py                SQLite ベースの永続化層（初期化・CRUD）
    - system_monitor.py               システム状態・データ鮮度チェック
    - trade_monitor.py               （trade ログ監視ロジック）
    - risk_monitor.py                 ドローダウン・ポジション上限監視
    - kill_switch.py                  kill.flag 管理
    - monitoring_engine.py            各 Monitor を束ねるエンジン
    - alert_manager.py                （外部通知管理）
  - execution/
    - execution_engine.py             Execution エンジン本体
    - broker_factory.py               ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - monitoring/ (上記)
  - utils/
    - logging_setup.py                統一ログ設定ユーティリティ
    - process_priority.py             プロセス優先度・CPU affinity 設定
    - __init__.py

付録：よくあるコマンド例
-----------------------
- .env を対話的に作る:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config

- 実行エンジン起動（デーモン化等は外部で対応）:
  - python -m kabusys.run_execution

- 監視プロセス起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

トラブルシューティング
-----------------------
- DuckDB や psutil、openai が import エラーになる場合: 依存パッケージがインストールされているか確認してください。
- .env が自動ロードされない場合: KABUSYS_DISABLE_AUTO_ENV_LOAD を確認。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
- YAML 検証を行いたいが PyYAML が無い場合: validate_config は YAML チェックをスキップします。PyYAML をインストールしてください。

ライセンス / バージョン
-----------------------
- バージョン: src/kabusys/__init__.py の __version__ を参照してください（デフォルト "0.1.0"）。

お問い合わせ
------------
実装・拡張・運用に関する質問があれば、具体的な実行ログや .env（シークレットを除く）を添えて問い合わせてください。