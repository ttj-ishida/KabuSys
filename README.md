README
=====

概要
----
KabuSys は日本株自動売買システムのライブラリおよび起動スクリプト群です。  
このリポジトリには、取引実行エンジン（ExecutionEngine）、監視コンポーネント（MonitoringEngine）、ポートフォリオ構築／ポジションサイズ計算、ファクター計算・調査ツール、AI を用いたニュースセンチメント評価などの主要機能が含まれます。

主な設計方針
- 本番（live）／ペーパートレード（paper_trading）／開発（development）を環境変数で切り替え可能。
- ペーパートレードは本番データベースと分離（専用 SQLite を使用）。
- DuckDB を分析用 DB として利用（prices_daily などの時系列データ保管想定）。
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定をサポート（API キー必須）。
- ログは統一的なセットアップ関数で stdout と日次ローテートファイルに出力。

機能一覧
---------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番と paper_trading を環境変数で切り替え。paper_trading 時は MockBrokerClient を利用し data/paper_trading.db に記録。
  - リスクマネージャ・オーダーマネージャ・リコンシリエータ等を組み立ててセッションを実行。
  - 停止は data/stop_requested.flag / kill.flag を用いたフラグファイルで制御。

- Monitoring（run_monitoring.py / monitoring package）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング監視ループ。
  - system_status / trade_logs / risk_logs / dashboard 等を SQLite に永続化（monitoring_db.py）。
  - KillSwitch による自動停止 (kill.flag) 発動ロジック。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額・スコア加重配分、ポジションサイズ決定、セクターキャップ、レジーム乗数等の純粋関数実装。

- リサーチ（kabusys.research）
  - ファクター計算（Momentum, Volatility, Value 等）、将来リターン計算、IC 計算、統計サマリ。

- AI モジュール（kabusys.ai）
  - news_nlp: raw_news を LLM に送り銘柄ごとにセンチメントを算出して ai_scores テーブルへ保存。
  - regime_detector: ETF（1321）MA200 + マクロ記事センチメントを合成して market_regime を判定・保存。

- ツール
  - 設定ウィザード（config_setup.py）: .env を対話式で作成／更新。
  - 設定検証（validate_config.py）: .env と config/*.yaml を起動前に検証。
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

前提・依存
-----------
- Python 3.10 以上（型アノテーションの | を使用）。
- 必須パッケージ（実行する機能により必要）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- オプション:
  - PyYAML（config/*.yaml の検証に使用。未インストールでも検証はスキップ）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動:

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（推奨）:

   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows

3. 必要なパッケージをインストール（最小）:

   pip install duckdb psutil

   AI 機能を使う場合:

   pip install openai

   config YAML 検証を行う場合:

   pip install PyYAML

4. 環境変数（.env）設定:
   - 対話式ウィザードを使って .env を作成・更新できます:

     python -m kabusys.config_setup

   - 生成された .env の例（重要なキー）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_token_here
     - KABU_API_PASSWORD=your_kabu_password_here
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=sk-...

   - 自動 .env ロードを無効化する場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証:

   python -m kabusys.validate_config
   # 警告もエラー扱いにするには --strict を付ける

使い方
------
主要な実行スクリプトの例を示します。いずれもプロジェクトルートから実行します。

- 実行エンジン（ExecutionEngine）を起動:

  python -m kabusys.run_execution

  動作:
  - KABUSYS_ENV が paper_trading の場合は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録。
  - 起動時に data/stop_requested.flag が存在する場合は起動を中止します。
  - 起動中に data/stop_requested.flag を作成すると実行エンジンを停止します。
  - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）へ書き込み。

- 監視ループを起動:

  python -m kabusys.run_monitoring

  動作:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を用いてログを永続化します（監視 DB は環境に依存しない）。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成すると監視を停止します。

- 設定ウィザード:

  python -m kabusys.config_setup

- 設定検証:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:

  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスは --db で指定するか環境変数 PAPER_TRADING_SQLITE_PATH を使用

運用上の重要ポイント
- paper_trading は本番 DB と完全分離するため、誤って本番に発注しないように注意してください。
- Kill Switch:
  - RiskMonitor 等から条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - Settings.kill_flag_clear_on_start が "1" の場合、起動時に kill.flag を自動削除する挙動になりますが、本番では 0 を推奨します。
- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテートで保存されます（30 日保持）。
  - ログの出力先・レベルは環境変数 LOG_DIR / LOG_LEVEL で変更可能。

Directory 構成
----------------
（コードベースの主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring ポーリングループ起動スクリプト
  - config.py                     — 環境変数 / Settings 管理
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - tools/
    - paper_verification_report.py — Paper Trading レポート
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント取得（OpenAI 使用）
    - regime_detector.py           — 市場レジーム判定（OpenAI 使用）
  - monitoring/
    - monitoring_db.py            — SQLite スキーマ / Persistence
    - system_monitor.py
    - trade_monitor.py            — ※trade_monitor 本体はここにある想定（抜粋で省略）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py            — ※アラート送信の実装想定
  - execution/
    - execution_engine.py         — 実行エンジン（EngineConfig など）
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - monitoring/monitoring_db.py, risk_monitor.py, system_monitor.py, ...（上記参照）

補足（環境変数一覧・説明）
--------------------------
主要な環境変数：
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live
- OPENAI_API_KEY — OpenAI API キー（AI 機能）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
- PID_FILE_PATH — Execution の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効）

ライセンス・バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）。
- ライセンス情報や CONTRIBUTING、CHANGELOG 等はリポジトリルートの該当ファイルを参照してください（存在する場合）。

トラブルシューティング
----------------------
- DuckDB / SQLite のファイルが見つからない、または親ディレクトリがない場合は validate_config が警告します。必要に応じてディレクトリを作成してください（多くの処理は起動時に自動作成されます）。
- OpenAI 呼び出しでレート制限や一時エラーが発生した場合、モジュール内でバックオフ／リトライが仕込まれていますが、API キーの残高や制限を確認してください。
- プロセス優先度設定は OS に依存します。psutil による優先度変更が失敗した場合は警告ログが出力されますが、処理自体は継続します。

以上がこのコードベースの概要と使い方です。README に載せたい追加情報（例: 実運用のデプロイ手順、systemd ユニット例、詳細な DB スキーマ説明など）があれば教えてください。必要に応じて追記・展開します。