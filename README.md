# KabuSys

日本株向け自動売買システムのコードベース（ライブラリ＋起動スクリプト群）。  
このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・リサーチ・AI 補助機能を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を備えた日本株向けの自動売買フレームワークです。

- ファクター計算（Momentum / Volatility / Value など）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ算出）
- ExecutionEngine（発注管理・注文リポジトリ・リスク管理）
- Monitoring（システムヘルス、取引・リスク監視、Kill Switch）
- AI 補助（ニュースのセンチメント解析、レジーム判定）
- Paper Trading 用の分離 DB と Mock ブローカー対応
- 設定ウィザード・検証 CLI、検証レポートツール

設計方針として、DB（SQLite / DuckDB）や OpenAI 等の外部依存は明示的な設定で切り替えられ、フェイルセーフ（API 失敗時のフォールバック等）を考慮しています。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine を起動。`KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）に記録します。
- run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。監視は本番 sqlite_path を参照します（環境に依存せず本番 DB を使用）。
- config_setup.py
  - .env を対話式に作成 / 更新するウィザード。
- validate_config.py
  - .env や config/*.yaml の設定検証。`--strict` フラグで警告も FAIL 扱いにできます。
- tools/paper_verification_report.py
  - Paper Trading の検証レポート出力（稼働率・注文成功率・レイテンシ等を評価）。
- ai/
  - news_nlp: ニュースを LLM でセンチメント評価して ai_scores に書き込む。
  - regime_detector: マーケットレジーム（bull/neutral/bear）判定を行い DB に保存。
- monitoring/
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch 等で監視・アラート・Kill Switch を実装。
- portfolio/
  - 候補選定、重み計算、ポジションサイズ決定、セクター制限、レジーム乗数などの純関数群。
- research/
  - ファクター計算・将来リターン・IC 計算・統計サマリーなど DuckDB ベースのリサーチ用関数群。
- utils/
  - logging_setup（統一ログ設定）、process_priority（プロセス優先度設定）等。

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。

2. 必要なパッケージをインストールします（最小例）:

   pip install duckdb psutil openai

   追加推奨 / 実用的:
   - PyYAML（config YAML の検証に使用）
     pip install pyyaml

   注: requirements.txt がある場合はそちらを利用してください（本リポジトリには含まれていない想定）。

3. プロジェクトルートに移動し、.env を作成します。対話式ウィザード推奨:

   python -m kabusys.config_setup

   ウィザードを使わない場合は .env を手動作成してください（サンプルは .env.example を参照）。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）

   その他（デフォルトあり）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB。デフォルト data/paper_trading.db）
   - LOG_LEVEL（デフォルト: INFO）
   - OPENAI_API_KEY（AI 機能を使う場合は必須）

5. 設定検証（任意）:

   python -m kabusys.validate_config
   # --strict を付けると警告があると exit 1 になります
   python -m kabusys.validate_config --strict

6. ログディレクトリ・DB ディレクトリは自動作成が試みられますが、必要に応じて事前に作成してください（デフォルト logs/, data/）。

---

## 使い方

- ExecutionEngine を起動する（MODULE 実行）:

  # 通常（デフォルト KABUSYS_ENV=development）
  python -m kabusys.run_execution

  # Paper trading モードで起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  特記事項:
  - Paper Trading では MockBrokerClient が使われ、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番 DB と分離されます。
  - 起動前に data/stop_requested.flag が存在する場合エンジンは起動しません。
  - エンジン停止（外部から）: data/stop_requested.flag を書き込むと実行スレッドは停止します。
  - Kill Switch（監視側が書き込む kill.flag）によって ExecutionEngine に停止シグナルを送る仕組みがあります。flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）で変更可能。

- Monitoring を起動する:

  # デフォルトは 60 秒間隔
  python -m kabusys.run_monitoring

  ポーリング間隔を変更する:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  停止:
  - 管理用の stop フラグファイル data/stop_requested.flag を作成すると監視ループが終了します。

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数で提供）。
  - ニューススコア付与:
    - プログラム内部 API: kabusys.ai.score_news
    - コマンドラインスクリプトがある場合はそれを利用（現状はライブラリ関数として提供）
  - 注意: API 呼び出しはリトライ・フォールバック（失敗時は安全側の値）を行います。

- Paper Trading 検証レポート:

  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB は --db で指定、または環境変数 PAPER_TRADING_SQLITE_PATH を使用

---

## 重要なファイル / フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring の外部停止・起動チェックに用いられるファイル。
- data/kill.flag
  - Monitoring 側の KillSwitch が設定した場合、ExecutionEngine 停止のトリガーとして使用。
- data/execution.pid
  - ExecutionEngine の PID 保存先（デフォルト pid_file）。
- .env, .env.local
  - 設定ファイル。config_setup.py で作成・更新。自動読み込みはデフォルトで有効。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う / 推奨:
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- OPENAI_API_KEY: AI 機能を利用する場合に必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（Settings クラスで参照）

設定の自動読み込み:
- ルートに .env がある場合、起動時に自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / Settings 管理（.env 自動ロード含む）
    - config_setup.py            — .env 対話式ウィザード
    - validate_config.py         — 設定検証 CLI
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - run_monitoring.py          — Monitoring 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py (存在を前提：監視全体で使用)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py (存在を前提：通知管理)
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - execution/                  — Execution 関連モジュール群（Engine, broker_factory, order_manager 等）
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - data/                       — データパイプライン / stats 等（prices_daily 等の DuckDB テーブル管理）

（注）上記は主要ファイルの抜粋です。プロジェクト全体の実装はこの構成を拡張することで機能を追加します。

---

## ログ

- ログはデフォルトで stdout と logs/<app_name>.log（日次ローテーション）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging() で統一されます。
- ログディレクトリは環境変数 LOG_DIR や setup_logging の引数で変更可能です。

---

## 開発上の注意 / ベストプラクティス

- 本番起動時は KABUSYS_ENV=live を慎重に設定してください（validate_config で警告が出ます）。
- 本番では KILL_FLAG_CLEAR_ON_START を `0`（デフォルト）にしておくことを推奨します（自動クリアは危険）。
- Paper Trading は本番 DB と分離されています。誤って本番 DB を上書きしないよう .env を管理してください。
- OpenAI を使う AI 機能は外部 API 呼び出しのためレート制限や費用に注意してください。API エラー時のフォールバックロジックが組まれていますが、運用ルールを定めてください。
- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db() などで一部自動マイグレーションが実装されていますが、重要変更は慎重に扱ってください。

---

README はプロジェクトの最小限の導入ガイドです。詳細なアーキテクチャ（各モジュールの仕様、Engine の挙動、ブローカー実装、戦略設計ドキュメント等）は別ドキュメント（PortfolioConstruction.md、StrategyModel.md など）を参照してください。必要であればそれらのドキュメントも本 README にリンクすることを検討してください。