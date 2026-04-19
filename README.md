KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・モニタリングを目的とした小規模なフレームワークです。
主要機能群は以下を含みます:

- ExecutionEngine（発注・注文管理・リスク制御）
- Monitoring（システム稼働状況・注文状況・リスク監視と Kill Switch）
- Portfolio Construction（銘柄選定・重み計算・ポジションサイジング）
- Research（ファクター計算、特徴量解析）
- AI モジュール（ニュースセンチメント / 市場レジーム判定：OpenAI を利用）
- ユーティリティ（設定ウィザード、設定検証、Paper Trading 検証レポート）

本リポジトリはライブラリ群と CLI 風の起動スクリプト（python -m kabusys.xxx）で構成されています。

主な機能一覧
--------------
- 環境設定ウィザード（kabusys.config_setup）
  - 対話式で .env を生成・更新
- 設定検証ツール（kabusys.validate_config）
  - .env と config/*.yaml の基本チェック（--strict あり）
- Execution 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し paper_trading DB に分離
  - PID / stop フラグの監視で安全に停止可能
- Monitoring 起動スクリプト（kabusys.run_monitoring）
  - 定周期で System/Trade/Risk Monitor を実行、SQLite にログ保存
  - MONITOR_POLL_INTERVAL でポーリング間隔上書き可能（デフォルト 60 秒）
- MonitoringEngine（監視ループ）
  - KillSwitch 評価、AlertManager 連携ポイント（AlertManager 実装は別）
- AI:
  - kabusys.ai.news_nlp: ニュースを OpenAI に送り銘柄ごとにセンチメントを算出して ai_scores に保存
  - kabusys.ai.regime_detector: ETF の MA200 比とマクロニュースで市場レジーム判定
- Research:
  - factor_research（momentum / volatility / value）
  - feature_exploration（forward returns / IC / 統計サマリ）
- Portfolio:
  - 銘柄選定、等重・スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- ツール:
  - paper_verification_report: ペーパートレード DB から検証レポート生成

前提 / 必要環境
----------------
- Python >= 3.10
- 推奨パッケージ（プロジェクトによって必要なもの）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (validate_config の YAML 検証を行う場合)
- （任意）仮想環境: venv / pyenv など

セットアップ手順
----------------
1. リポジトリをクローンしてプロジェクトルートへ移動
   - 例:
     - git clone <repo>
     - cd <repo>

2. 仮想環境の作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 例（最低限）:
     - pip install duckdb psutil
   - AI 機能を使う場合:
     - pip install openai
   - validate_config の YAML 検証を使う場合:
     - pip install PyYAML

4. 環境変数 (.env) の作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - ウィザードは .env を生成します。生成後は以下のコマンドで検証してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があればメッセージに従い .env を修正
   - 警告を FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用関連:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- データベース:
  - DUCKDB_PATH: 分析用 DuckDB（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- AI:
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- その他:
  - PID_FILE_PATH: 実行エンジンの PID ファイルパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag パス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"0"/"1"、デフォルト 0）
- 一時上書き:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方（起動方法・主要コマンド）
--------------------------------
- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Monitoring（監視プロセス）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は data/stop_requested.flag を検知するとループを終了します。
  - 監視は環境にかかわらず Settings.sqlite_path（通常 data/monitoring.db）を使用します。

- Execution（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 停止は data/stop_requested.flag を作成するとエンジンに検知されて停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ関係
  - kabusys.ai.score_news / regime_detector.score_regime は DuckDB 接続と OPENAI_API_KEY を必要とします。
  - OpenAI API キーが設定されていない場合は例外になります（呼び出し側で捕捉してください）。

ログ・ファイル
--------------
- ログ設定は kabusys.utils.logging_setup によって行われます。
- デフォルトログディレクトリ: logs/
- ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
- ログは日次ローテーション、30 日分を保持します。

停止・Kill Switch
-----------------
- 実行中エンジンの停止はファイルフラグ方式を採用しています:
  - 停止要求（エンジンへ）: data/stop_requested.flag を作成
  - Kill Switch（リスク検出時に ExecutionEngine を止める）: data/kill.flag を作成
  - KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に kill.flag を自動クリアします（本番では 0 推奨）

ディレクトリ構成（主要ファイルと簡単な説明）
--------------------------------------------
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動読み込み）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化層
    - system_monitor.py — システム稼働・データ鮮度チェック
    - trade_monitor.py —（注文監視: 実装参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるループ
    - kill_switch.py — Kill Switch ロジック
    - alert_manager.py — アラート送信ロジック（実装が別にある想定）
  - execution/ — ExecutionEngine 周りの実装（broker, order_manager, risk_manager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算 / 投下資金制御
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/value/volatility の計算（DuckDB を利用）
    - feature_exploration.py — forward returns / IC / 統計
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書込む
    - regime_detector.py — マクロ + MA200 による市場レジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - data/ （ランタイム・データ保存場所、デフォルト）
    - monitoring.db (SQLITE_PATH)
    - kabusys.duckdb (DUCKDB_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - execution.pid, stop_requested.flag, kill.flag など

注意事項 / 運用上のヒント
------------------------
- .env は絶対にリポジトリにコミットしないこと（config_setup のヘッダにも明記あり）。
- KABUSYS_ENV=live の場合は特に LINE 通知・ Kill Switch 周りの設定を確認してください（validate_config が警告を出します）。
- Monitoring は run_monitoring が使用する SQLite DB を用いており、run_monitoring は KABUSYS_ENV にかかわらず設定された sqlite_path（デフォルト data/monitoring.db）を使用します。一方、Execution は paper_trading 時に別 DB を使います（PAPER_TRADING_SQLITE_PATH）。
- AI 機能は OpenAI API に依存します。キー管理・レート制限に注意してください。news_nlp / regime_detector はレート・エラーを考慮したリトライロジックを備えていますが、コスト管理は利用者の責任です。
- Python の型ヒントや union 演算子 (|) を用いているため Python 3.10 以上の使用を推奨します。

FAQ（よくある質問）
------------------
Q: どの DB にログ/注文が残りますか？
A: 監視ログは SQLITE_PATH（デフォルト data/monitoring.db）へ保存。ペーパートレード時は Execution は PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）へ分離します。

Q: モニターやエンジンのポーリング間隔は？
A: run_monitoring のデフォルトは 60 秒。MONITOR_POLL_INTERVAL 環境変数で変更可能です。

Q: 強制停止 (Kill) のトリガーは？
A: RiskMonitor が閾値超過（例: ドローダウン）を検出すると KillSwitch が data/kill.flag を書き、ExecutionEngine を停止させます（実際のシグナル送出ではなくフラグ検知方式）。

サポート / 変更履歴
-------------------
- この README はソースコード（src/kabusys 以下）を基に作成されています。各モジュールの詳細は該当 .py ファイルの docstring / コメントを参照してください。
- バージョンは kabusys.__version__（デフォルト "0.1.0"）で管理されています。

--- 
必要な追加情報（例：requirements.txt、実運用向けの systemd ユニット例、AlertManager の実装など）があれば追記します。必要ならどの情報が欲しいか教えてください。