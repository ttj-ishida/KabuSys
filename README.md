KabuSys — 日本株自動売買システム（README）
=================================

このドキュメントは、提供されたコードベース（src/kabusys 以下）に対する README です。
基本的な概要、機能、セットアップ、使い方、ディレクトリ構成を日本語でまとめています。

1. プロジェクト概要
------------------
KabuSys は日本株向けの自動売買・研究フレームワークです。主な役割は次のとおりです。

- データ基盤（DuckDB を利用した時系列データ参照）
- ファクター計算 / 研究ユーティリティ（momentum, volatility, value 等）
- ポートフォリオ構築（候補選定・重み付け・数量算出）
- ExecutionEngine（発注ロジック、リスク管理、注文履歴）
- Monitoring（システム状態・注文の監視、Kill Switch）
- AI モジュール（ニュース NLP を用いたセンチメント評価、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、Paper Trading 検証レポート）

設計方針の要点:
- 本番/ペーパートレードの分離（paper_trading モード時は専用 DB を使用）
- ルックアヘッドバイアス対策（日時参照を慎重に行う）
- フェイルセーフ（API 失敗時は安全なフォールバック）
- ユニット化された純粋関数群（portfolio, research 等）

2. 機能一覧
-----------
主要な機能（モジュール）と概要:

- kabusys.config / config_setup / validate_config
  - 環境変数・設定の管理、対話式 .env 生成ウィザード、起動前の設定検証 CLI。

- Execution
  - Broker クライアントの抽象化（BrokerClientFactory）を用いた発注実装。
  - ExecutionEngine：発注セッション、OrderManager、Reconciler、RiskManager。

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスクの監視、データ鮮度、PID チェック。
  - TradeMonitor：注文の滞留・約定異常検出（実装参照）。
  - RiskMonitor：ドローダウン監視、ポジション上限監視。
  - KillSwitch：kill.flag による ExecutionEngine の停止シグナル生成。
  - MonitoringDB：SQLite による監視ログ永続化。

- Portfolio
  - 候補選定（select_candidates）、重み計算（等分 / スコア加重）、ポジションサイズ算出、セクター上限適用、レジーム乗数。

- Research
  - ファクター計算（momentum / volatility / value）、将来リターン計算、IC（Information Coefficient）、統計サマリ。

- AI
  - news_nlp: OpenAI（gpt-4o-mini）を用いたニュースのセンチメント集約・ai_scores 書き込み。
  - regime_detector: ETF（1321）MA とマクロニュースの LLM スコアを合成して市場レジーム判定。

- Tools
  - paper_verification_report: ペーパートレード DB から検証レポートを生成する CLI。

- Utils
  - logging_setup：統一ログ設定（stdout + 日次ローテートファイル）。
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ。

3. 必要条件（概略）
------------------
- Python 3.10+（typing の現代機能を使用）
- 推奨パッケージ（主要な依存）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml (validate_config の YAML 検証は任意だがあると詳細検証が可能)
- SQLite（Python 標準 sqlite3 を使用）
- ネットワーク接続（OpenAI / broker API を使う場合）

（本リポジトリに requirements.txt が無い場合は、プロジェクトに合わせて作成してください）

4. セットアップ手順
------------------
1) リポジトリをクローン:
   git clone <repo-url>
   cd <repo-root>

2) 仮想環境作成（例）:
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows

3) 必要パッケージをインストール（例）:
   pip install duckdb psutil openai pyyaml

4) .env の準備（推奨: ウィザードで作成）:
   python -m kabusys.config_setup
   - 対話式で必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定します。
   - .env は絶対に Git にコミットしないでください。

5) 設定の検証:
   python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いになります:
     python -m kabusys.validate_config --strict

6) データディレクトリなどの作成:
   - デフォルトの DB/ログ/フラグは data/ や logs/ を使用します。必要に応じて手動で作成してくださいが、多くは起動時に自動作成されます。

5. 使い方（起動例）
-------------------

環境変数の代表例（.env）:
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- KABUSYS_ENV=development|paper_trading|live
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- OPENAI_API_KEY=（AI を使う場合）
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

主要なコマンド:

- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 実行中に data/stop_requested.flag を作成すると安全に停止します。
  - 実行時は data/execution.pid が書かれます（PID ファイル）。

- 監視プロセスを起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）。
    例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は settings.sqlite_path（デフォルト data/monitoring.db）を使用してログを永続化します（KABUSYS_ENV に依存しません）。
  - 監視中に data/stop_requested.flag が作成されるとループを終了します。

- .env 対話ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report
  期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

ログ:
- デフォルト: logs/<app_name>.log（日次ローテーション、30 日分保持）
- 関数 setup_logging により stdout とファイルにログを出力します。
- LOG_DIR 環境変数、または setup_logging の引数で出力先を変更できます。

Kill Switch / 停止フラグ:
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止を促します（実行側はその存在を確認して停止する実装にしてください）。
- run_execution/run_monitoring は data/stop_requested.flag を監視して終了します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

AI 機能（news_nlp, regime_detector）:
- OpenAI を使用するため OPENAI_API_KEY が必要です（引数で API キーを渡すことも可能）。
- API 呼び出しはリトライやフェイルセーフを備えていますが、キーの設定と利用制限に注意してください。

6. ディレクトリ構成（抜粋）
-------------------------
以下は src/kabusys 配下のおおまかなファイル構成と簡単な説明です。

- kabusys/
  - __init__.py                 — パッケージ定義
  - config.py                   — 設定管理（.env 自動読み込み、Settings クラス）
  - config_setup.py             — .env 対話ウィザード CLI
  - validate_config.py          — 起動前設定検証 CLI
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py           — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py      — 候補選定・重み計算
    - position_sizing.py        — 株数決定（ロット丸め・cap 適用）
    - risk_adjustment.py        — セクター上限、レジーム乗数
  - research/
    - factor_research.py        — ファクター計算（momentum, volatility, value）
    - feature_exploration.py    — 将来リターン、IC、統計サマリ
  - ai/
    - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py        — レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py          — SQLite スキーマ初期化・永続化層
    - system_monitor.py         — CPU/メモリ/ディスク・データ鮮度監視
    - trade_monitor.py          — 注文監視（滞留・異常等）
    - risk_monitor.py           — ドローダウン・ポジション上限監視
    - kill_switch.py            — kill.flag 制御
    - monitoring_engine.py      — 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py          — （アラート送信ラッパー、実装参照）
  - execution/
    - execution_engine.py       — ExecutionEngine（セッション実行）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py         — Broker クライアント生成（本番/Mock の切替）
  - monitoring/monitoring_db.py — 監視 DB の定義（テーブル / マイグレーション）
  - utils/
    - logging_setup.py          — ログ初期化ユーティリティ
    - process_priority.py       — プロセス優先度設定ユーティリティ

（上記は主要ファイルの抜粋です。実際のリポジトリを参照してください）

7. 開発・運用上の注意
--------------------
- .env は機密情報を含むため絶対に Git にコミットしないこと。
- KABUSYS_ENV を "live" にする際は validate_config の警告を必ず確認してください（LINE 通知などの設定漏れで重要なアラートが届かない可能性があります）。
- Paper Trading 用 DB は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH を使用）。
- AI 機能は API コストが発生します。バッチサイズやトークン量に注意してください。
- プロセス優先度設定や CPU affinity 設定は psutil の権限に依存します。権限不足時は警告が出てスキップされます。
- DuckDB / SQLite のバージョンや実装差異により executemany などで制約があるため、コード中に互換性確保のためのワークアラウンドがあります。

8. よく使うコマンドまとめ
------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

付録: 問い合わせ・拡張
--------------------
- 新しい Broker 実装を追加する場合は execution/broker_factory.py を拡張してください。
- AI モデルやプロンプトを変える場合は ai/news_nlp.py / ai/regime_detector.py を編集します（API キー管理に注意）。
- 設定項目追加は config_setup.py と config/*.yaml（必要なら）および validate_config.py を合わせて更新してください。

以上。README の雛形として必要に応じて追記・調整してください。