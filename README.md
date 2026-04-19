README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン（本番 / ペーパートレード対応）
- Monitoring：システム稼働状況・注文ログ・リスク監視と Kill Switch（停止フラグ）の管理
- Portfolio Construction：銘柄選定・重み計算・株数決定ロジック（純粋関数）
- Research：DuckDB を用いたファクター計算・特徴量解析ユーティリティ
- AI モジュール：ニュース NLP（OpenAI）によるセンチメントスコアリング、および市場レジーム判定
- ユーティリティ：設定ウィザード、設定検証、ペーパートレード検証レポート等

この README は開発者／運用者向けの導入・実行手順と各コンポーネントの使い方をまとめたものです。

主な機能一覧
--------------
- 実行環境切替（KABUSYS_ENV: development / paper_trading / live）
  - paper_trading モードでは MockBroker を用い、発注は専用 DB に記録（本番 DB と分離）
- Execution エンジン：
  - ブローカークライアント、OrderManager、RiskManager、Reconciler などを組み合わせて発注処理を実行
  - PID ファイル出力・停止フラグ検知（data/execution.pid / data/stop_requested.flag）
- Monitoring：
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / Execution プロセスを監視
  - TradeMonitor / RiskMonitor: 注文の滞留やドローダウン、ポジション上限を監視しリスクログを記録
  - KillSwitch: 閾値超過時に data/kill.flag を書き込み、Execution の停止をトリガー
  - Monitoring DB（SQLite）への永続化と簡易マイグレーション
- Portfolio：
  - 候補選定、等重・スコア加重、リスクベースのポジションサイズ計算、セクターキャップ適用
- Research：
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC 計算、要約統計
- AI：
  - news_nlp: OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントの収集と ai_scores への書き込み
  - regime_detector: ETF とマクロニュースを用いた日次レジーム判定（market_regime テーブルに書き込み）
- ツール：
  - 環境ウィザード（.env 作成）: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

セットアップ手順
----------------
1. Python とパッケージのインストール（例）
   - 推奨: Python 3.10+
   - 必要パッケージ（主要なもの）:
     - duckdb, psutil, openai, pyyaml（YAML 検証はオプション）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ 実際の requirements.txt がある場合はそちらを使用してください。

2. プロジェクトルートの配置
   - repo をクローン/配置すると、src/kabusys 以下がルートパッケージになります。
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出します。

3. .env の作成
   - 対話式ウィザードで .env を作成できます:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（一部、デフォルト値を持つ）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — Paper Trading専用 DB（paper_trading のとき）
     - OPENAI_API_KEY — AI モジュールを使う場合に必須
     - LOG_LEVEL — デフォルト: INFO
     - PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject、デフォルト instant）
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1、デフォルト 0)

4. 設定検証（任意だが強く推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

5. 初回ディレクトリ作成
   - logs/ や data/ ディレクトリはコードが自動作成しますが、パーミッション等で失敗する場合は手動作成してください。

使い方
------
起動スクリプト
- Monitoring を起動する（ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き（デフォルト 60）
  - run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視 DB は一元管理）

- Execution を起動する（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します
  - 起動時に data/stop_requested.flag が存在する場合は起動しません
  - 実行中は data/execution.pid に PID を書き込みます。停止は stop フラグ（data/stop_requested.flag）で指示できます

停止・フラグ類
- 停止要求（全体停止／デバッグ向け）
  - プロセスを即時終了させたい場合は data/stop_requested.flag を作成（空ファイルでも可）。スクリプトは定期的にこのファイルをチェックし安全に終了します。
- Kill Switch（自動停止トリガー）
  - Monitoring 内の条件（ドローダウン超過・ポジション上限超過等）で data/kill.flag が書かれます
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動クリアされます（本番環境では推奨されません）
- PID ファイル
  - Execution は data/execution.pid を出力します。外部から停止させる際に参照してください。

ツール・ユーティリティ
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI 関連
- news_nlp と regime_detector は OpenAI API（モデル: gpt-4o-mini 想定）を使用します。実行には OPENAI_API_KEY が必要です。
- 外部 API 失敗時はフェイルセーフ（デフォルトスコアや0.0で継続）する設計です。

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。
- コンソール（stdout）にもログを出力します。
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御できます。

ディレクトリ構成
----------------
（抜粋: 主要なファイル・フォルダ）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・マイグレーション含む）
    - system_monitor.py      — システム状態監視
    - risk_monitor.py        — ドローダウン・ポジション監視
    - kill_switch.py         — Kill Switch ロジック
    - monitoring_engine.py   — 各 Monitor のオーケストレーション
    - ...（TradeMonitor / AlertManager 等）
  - execution/
    - execution_engine.py    — 実行エンジンの実装（EngineConfig など）
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
  - ai/
    - news_nlp.py            — ニュース NLP / スコアリング
    - regime_detector.py     — マーケットレジーム判定
  - tools/
    - paper_verification_report.py
  - data/                    — データファイル（例: monitoring.db, paper_trading.db, kill.flag 等）※git 管理外推奨
  - logs/                    — ログ出力先（デフォルト）

環境変数一覧（代表）
--------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の fill モード（instant|partial|never|reject、デフォルト instant）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、デフォルト 0）

運用上の注意
-------------
- .env は機密情報を含むため Git 管理してはいけません（config_setup のヘッダにも注意書きがあります）。
- 本番環境（KABUSYS_ENV=live）では Kill Switch 設定、LINE 通知設定等を十分に確認してください。validate_config により設定漏れや注意点を事前に検出可能です。
- Monitoring は常に本番の監視 DB（SQLITE_PATH）を参照します。paper_trading の発注ログは専用の PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と分離）。
- OpenAI 連携は API レート制限やコストが発生します。運用ルール（呼び出し頻度、バッチサイズ）を検討してください。

トラブルシューティング
----------------------
- Logging のファイルハンドラが作れない場合はコンソール出力のみで継続します（警告が出ます）。logs/ ディレクトリのパーミッションを確認してください。
- SQLite / DuckDB のファイルパスは .env で変更可能です。パスの親ディレクトリが存在しない場合は起動時に自動作成されることがありますが、パーミッションに注意してください。
- OpenAI 呼び出しで 5xx やタイムアウトが発生した場合、内部で指数バックオフ・リトライする実装です。致命的な失敗はログに出力され、フェイルセーフ挙動（スコア 0.0 等）になります。

ライセンス・貢献
----------------
この README はコードベースから自動生成したドキュメントの概要です。実際のライセンスや貢献方法はリポジトリのルートにある LICENSE / CONTRIBUTING ファイルを参照してください。

付録 — よく使うコマンド例
-------------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Monitoring 起動（デフォルト 60 秒間隔）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。運用や開発で追加したいドキュメント項目（例: 詳細設計書、API 仕様、システムアーキテクチャ図など）があれば教えてください。必要に応じて README を拡張します。