README
======

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤のプロジェクトです。本コードベースは以下の主要機能を含みます。

- 発注・実行エンジン（ExecutionEngine）
- 監視（Monitoring）：システム状態・注文・リスク監視と Kill Switch
- ポートフォリオ構築（銘柄選定・配分・ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）
- 運用補助ツール（.env ウィザード、設定検証、ペーパートレード検証レポート など）

主に Python で実装され、SQLite / DuckDB をデータ永続化に使用します。OpenAI API を用いた NLP 機能も一部に含まれます。

主な機能一覧
-------------
- Execution
  - 実際のブローカーまたは MockBroker による発注処理
  - リスク管理、注文管理、再整合処理（reconciler）
  - paper_trading モードでは paper_trading DB に完全分離して記録
- Monitoring
  - CPU / メモリ / ディスクの監視、Execution プロセス死活監視
  - 注文の滞留や約定異常、ドローダウン・ポジション数の監視
  - Kill Switch（条件を満たせば data/kill.flag を作成して Execution を停止）
  - アラート送信フック（LINE 等の通知設定を想定）
- Portfolio（純粋関数群）
  - 銘柄選定（スコア順）、等金額／スコア加重配分
  - セクターキャップ適用、レジーム乗数、ポジションサイジング（単元丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等のツール
- AI
  - ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に書き込み
  - マクロニュース + 価格 MA200 に基づく市場レジーム判定
  - バッチ・リトライ・レスポンス検証等の堅牢な実装
- 工具類
  - 環境設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.10+（型ヒントの union 型（|）等を使用）
- 必要な外部ライブラリ（下記参照）

推奨パッケージ（代表）
- duckdb
- psutil
- openai
- PyYAML (設定検証で YAML を検査する場合)
- （必要に応じて）その他発注用クライアント依存パッケージ

インストール例（仮）
- requirements.txt がある場合:
  pip install -r requirements.txt
- 手動:
  pip install duckdb psutil openai PyYAML

環境変数 / .env
- .env / .env.local をプロジェクトルートに置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- 必須環境変数
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- よく使う変数（一部）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視 DB デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（paper_trading モード時）
  - LOG_LEVEL: ログレベル（INFO 等）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時必須）
  - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）

.env 作成支援
- 対話式ウィザード: python -m kabusys.config_setup
  → .env を初期作成 / 更新できます。

設定検証
- python -m kabusys.validate_config
- --strict を付けると警告も失敗扱い（exit 1）

データファイル・フラグ
- デフォルトDB・ログ・PID 等:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - PID ファイル: data/execution.pid（Settings.pid_file_path で上書き可）
  - Kill flag: data/kill.flag（KillSwitch が作成）
  - Stop request flag: data/stop_requested.flag（run_monitoring/run_execution が監視）

ログ
- デフォルトログディレクトリ: logs/
- ログはコンソール (stdout) と日次ローテートファイル（logs/<app_name>.log）に出力
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging

使い方
------
主要なエントリポイント（コマンド例）

- 環境設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient と paper_trading DB を使用
  - 実行中に data/stop_requested.flag を作成すると安全に停止する
  - PID ファイルは data/execution.pid（デフォルト）に書かれる

- 監視ループ起動（SystemMonitor のポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60）
  - 監視は本番 sqlite_path を使用（環境に依存せず監視 DB は一貫して本番パス）

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD  開始日
    --to   YYYY-MM-DD  終了日
    --db PATH           DB ファイルパス（環境変数 PAPER_TRADING_SQLITE_PATH で代替可）

- AI モジュール（プログラム的呼び出し）
  from kabusys.ai import score_news
  # DuckDB 接続を渡して target_date と API キーを指定
  # score_regime（レジーム判定）は kabusys.ai.regime_detector.score_regime を使用

Kill Switch / 停止制御
- KillSwitch は監視結果に応じて data/kill.flag を作成して ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動削除できます（本番は 0 推奨）。
- run_monitoring / run_execution は data/stop_requested.flag を検知するとループを抜け安全終了します（運用用の停止フラグ）。

運用上の注意
- KABUSYS_ENV が live の場合は十分に設定を確認してください（validate_config にて警告あり）。
- OpenAI API を使う機能は API キーと通信コストを要します。API エラー時のフォールバック挙動が組み込まれていますが、運用ポリシーに合わせて設定してください。
- ログディレクトリ / DB ディレクトリのパーミッションに注意してください。ログファイル作成に失敗するとファイル出力は無効になりコンソール出力のみになります。

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル・パッケージ）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 読み込みと Settings クラス
  - config_setup.py           — .env 対話式ウィザード（CLI）
  - validate_config.py        — 起動前の設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py             — ニュースの LLM スコアリング
    - regime_detector.py      — レジーム判定（MA200 + マクロセンチメント）
    - __init__.py

  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（テーブル定義・CRUD）
    - system_monitor.py       — CPU/メモリ/データ鮮度監視
    - trade_monitor.py        — （注文監視ロジック）
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - kill_switch.py          — kill.flag 制御
    - monitoring_engine.py    — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py        — （通知送信ロジック）

  - execution/
    - execution_engine.py     — エンジン本体（セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py       — ブローカクライアント生成（本番 / Mock 切替）

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - monitoring/               # 既出（重複表示：監視系）
  - monitoring_db.py

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py        — 共通ログ設定
    - process_priority.py     — プロセス優先度 / CPU affinity
    - __init__.py

付録: 最小 .env 例
------------------
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxx  # AI機能利用時に設定

最後に
------
この README はコードベースから抽出した使用法・設計意図の要約です。詳細な内部設計や戦略の仕様（PortfolioConstruction.md や StrategyModel.md 等）は別ドキュメントを参照してください。もし README に追加したい実行例や運用手順（systemd/unit ファイル、コンテナ化、バックアップ手順など）があれば指示をください。