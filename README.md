README — KabuSys (日本株自動売買システム)
=====================================

概要
----
KabuSys は日本株自動売買／リサーチ用のライブラリ兼実行コンポーネント群です。本コードベースは下記の主要機能を持ち、ローカル開発からペーパートレード・本番運用までを想定しています。

主な設計方針:
- 分析用データは DuckDB、監視・発注ログは SQLite を使用
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と分離
- 設定は .env ファイル／環境変数で管理。対話式ウィザードで .env を生成可能
- 監視（Monitoring）コンポーネントで実行プロセス・データ鮮度・リスクを監視し、Kill Switch（flagファイル）で Execution を停止可能
- AI（OpenAI）を用いたニュースセンチメント評価や市場レジーム判定機能を提供

機能一覧
--------
- 環境設定ウィザード: .env を対話式で生成/更新（kabusys.config_setup）
- 設定検証 CLI: .env / config/*.yaml の事前検証（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、data/paper_trading.db に記録
- Monitoring 起動スクリプト（run_monitoring.py）
  - 定期ポーリングで System / Trade / Risk を監視し、監視ログを SQLite に永続化
- Kill Switch: リスク発生時に data/kill.flag を書き込み ExecutionEngine を停止
- Portfolio 構築ユーティリティ: 候補選定・重み付け・ポジションサイズ計算、セクター制限など
- Research: ファクター計算（momentum/value/volatility）、特徴量探索（IC 等）
- AI モジュール:
  - ニュース NLP（news_nlp.score_news）: OpenAI を使った銘柄別センチメントスコアリング
  - レジーム判定（regime_detector.score_regime）: MA + LLM 結合で市場レジームを判定
- ツール: ペーパートレード検証レポート出力スクリプト（kabusys.tools.paper_verification_report）

前提条件（推奨）
--------------
- Python 3.10+
  - ソース中で型注釈に「|」演算子（Union）を使っているため Python 3.10 以上が必要です
- pip（仮想環境推奨）
- 主要依存ライブラリ:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config YAML 検証を行う場合、任意）
- デフォルトのファイルパス（必要に応じて .env で上書き可能）
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db
  - ログディレクトリ: logs/
  - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

セットアップ手順
--------------
1. リポジトリをクローン / チェックアウトし、プロジェクトルートへ移動
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - YAML検証を使う場合: pip install pyyaml
   - （プロジェクトに requirements.txt があればそれを利用してください）
4. 環境変数 / .env の準備
   - 対話式ウィザードで作成（推奨）:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番環境用の重要変数:
     - KABUSYS_ENV = development | paper_trading | live
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH など
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

使い方（主要コマンド）
--------------------

- 実行 (ExecutionEngine)
  - 開始:
    - KABUSYS_ENV=paper_trading を使う例（ペーパートレード専用 DB を使用）:
      - export KABUSYS_ENV=paper_trading
      - python -m kabusys.run_execution
    - 本番/開発も同様に KABUSYS_ENV を設定して起動
  - 動作:
    - 起動時に PID ファイルを書き込み、別スレッドで engine.run_session を実行
    - data/stop_requested.flag があれば起動を停止、実行中に出現した場合はエンジン停止を試みる
  - ペーパートレードのデータは settings.paper_sqlite_path（デフォルト data/paper_trading.db）へ記録され、本番 DB と分離されます

- 監視 (Monitoring)
  - 起動:
    - MONITOR_POLL_INTERVAL を使ってポーリング間隔を上書きできます（秒、デフォルト 60）
      - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor を初期化し定期的に check を実行して監視ログを SQLite に保存
    - stop_requested.flag を検知するとループを終了
    - 監視は設定にかかわらず「本番用 sqlite_path」を使用して監視ログを記録します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db --from 2026-04-01 --to 2026-04-11

AI 機能（OpenAI）について
-------------------------
- ニューススコアリング: kabusys.ai.news_nlp.score_news（DuckDB 接続と target_date を渡して呼び出す）
- レジーム判定: kabusys.ai.regime_detector.score_regime
- いずれも OPENAI_API_KEY を環境変数で設定するか、関数引数で API キーを渡す必要があります
- API 呼び出しは再試行ロジックを持ち、失敗時は安全側のデフォルト値で継続します

運用上のファイル / フラグ
------------------------
- data/kill.flag: Kill Switch による実行停止シグナル（kill.flag が存在すると ExecutionEngine を停止させる設計の補助）
- data/stop_requested.flag: run_* スクリプトがループ中に検知して自プロセスを終了するための外部停止フラグ
- data/execution.pid: ExecutionEngine が起動時に書き込む PID ファイル
- logs/<app_name>.log: 各アプリケーション（execution, monitoring 等）の日次ローテートログ（logs/ に保存）

設定項目（代表的な環境変数）
----------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
- OPENAI_API_KEY — LLM 機能利用時に必要
- LOG_LEVEL — DEBUG/INFO/…
- LOG_DIR — ログ出力先ディレクトリ
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードのフィルモード（instant|partial|never|reject）

ディレクトリ構成（抜粋）
----------------------
プロジェクトの主要なモジュールと役割:

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env の読み込み・管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前チェック CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py           — ニュースセンチメント（OpenAI）処理
    - regime_detector.py    — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py      — SQLite の監視テーブル定義 + DB ラッパ
    - system_monitor.py     — CPU/メモリ/データ鮮度監視
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - trade_monitor.py      — （発注ログ等の監視: 実装参照）
    - kill_switch.py        — kill.flag の管理
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — （通知管理: 実装参照）
  - execution/
    - execution_engine.py   — ExecutionEngine の本体（起動・セッション管理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (上記)
  - utils/
    - logging_setup.py      — 共通ログ設定
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (実行時に生成される想定)
    - kill.flag
    - stop_requested.flag
    - execution.pid
    - monitoring.db
    - paper_trading.db
  - config/ (テンプレート YAML 等)
    - *.yaml                — 各種設定ファイル（system_config.yaml 等）

開発・運用上の注意
-----------------
- .env は絶対にリポジトリにコミットしないこと（config_setup にも明示）
- KABUSYS_ENV=live の場合は特に kill flag / LINE 通知設定などを慎重に確認すること
- AI 機能（OpenAI）を利用する際は API 利用料・レートリミットに留意すること
- 実行時にプロセス優先度を "high" に設定する処理があるため（set_process_priority）、権限や OS によっては警告が出ますが動作継続します

トラブルシューティング
-----------------------
- 設定検証でエラーが出る場合: python -m kabusys.validate_config を実行して出力を確認
- ログ出力先の作成に失敗するとコンソールのみのログになるので、LOG_DIR 設定と権限を確認
- OpenAI 呼び出しで失敗してもフェイルセーフで動作を継続する設計ですが、API キーやネットワークを確認してください

ライセンス / バージョン
-----------------------
- パッケージ版のバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 "0.1.0"）。

問い合わせ / 追加情報
--------------------
- 各モジュールの docstring に仕様・設計上の注意が多数記載されています。実装の詳細や拡張ポイントは該当ファイルを参照してください。

以上。README に書かれている手順で初期セットアップと主要なコマンド実行が行えます。必要であればサンプル .env テンプレートや system_config.yaml の雛形を生成するスクリプトの使用法（scripts/ 配下がある場合）についても追記します。