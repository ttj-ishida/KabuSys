KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買フレームワークです。システム監視、注文実行（ExecutionEngine）、ポートフォリオ構築、ファクター計算、LLMベースのニュースNLP / レジーム判定などのモジュールを含みます。

主な特徴
--------
- ExecutionEngine（実売買 / ペーパートレード切替対応）
  - KABUSYS_ENV に応じて paper_trading（MockBroker を利用）と live を切替
  - paper_trading は本番 DB と分離（data/paper_trading.db 等）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による安全停止（Kill Switch）
  - 停止用フラグ stop_requested.flag によるループ終了
- ポートフォリオ構築・リスク調整
  - 候補選定、重み計算、ポジションサイズ算出、セクター上限制御、レジーム乗数
- 研究用（Research）
  - DuckDB を使ったファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン、IC（Information Coefficient）などの解析ユーティリティ
- AI モジュール（OpenAI を利用）
  - ニュースのセンチメントスコアリング（news_nlp）
  - 市場レジーム判定（regime_detector）
  - API 呼び出しは冪等／フェイルセーフ設計（リトライ・部分書き込み）
- ユーティリティ
  - ロギング設定、プロセス優先度・CPU affinity ユーティリティ
  - .env ウィザード（対話式）と設定検証 CLI
- ツール
  - Paper Trading 検証レポート生成スクリプト

クイックスタート（前提）
-----------------------
- Python 3.10+
- SQLite（組み込み）
- 推奨パッケージ（例）:
  - duckdb, psutil, openai
  - 開発時に YAML の検証を使うなら PyYAML
- 例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
---------------
1. リポジトリをクローン／展開
2. 仮想環境を作る（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
3. 依存ライブラリをインストール
   pip install duckdb psutil openai pyyaml
4. 環境変数ファイルを作成
   - 対話式ウィザードで作る:
     python -m kabusys.config_setup
   - もしくは .env を手動作成（プロジェクトルートに .env を置く）
     必須（最低限）:
       JQUANTS_REFRESH_TOKEN=...
       KABU_API_PASSWORD=...
     推奨／使用例:
       KABUSYS_ENV=development|paper_trading|live
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       OPENAI_API_KEY=...
       LOG_LEVEL=INFO
       LOG_DIR=logs
       KILL_FLAG_CLEAR_ON_START=0
5. 設定検証（起動前に推奨）
   python -m kabusys.validate_config
   --strict を付けると警告も失敗（exit 1）扱いになります

基本的な使い方
-------------

- ExecutionEngine 起動（本番または paper_trading）
  - 実行:
    python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存され、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - エンジンは execution.pid（デフォルト data/execution.pid）に PID を書く設計です。
    - KILL フラグ（data/kill.flag）により外部から停止指示が出せます（Settings.kill_flag_clear_on_start により起動時に自動クリア可：開発用）。

- 監視プロセス起動
  - 実行:
    python -m kabusys.run_monitoring
  - 動作:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定可能（デフォルト 60 秒）
    - 監視は Settings.sqlite_path（monitoring DB）を使用します（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を用いることに注意）
    - 監視ループは data/stop_requested.flag の存在を検知すると終了

- Paper Trading 検証レポート
  - レポート生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラム的に呼ぶ）
  - OpenAI API キー（環境変数 OPENAI_API_KEY）が必要
  - 例（DuckDB 接続を渡す）:
    from kabusys.ai.news_nlp import score_news
    count = score_news(duckdb_conn, target_date, api_key=None)  # api_key None → 環境変数参照
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date)

ログと監視
----------
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一しているため、各起動スクリプトは同様のログ出力になります。
- デフォルトログディレクトリ: logs/
- ログレベルは環境変数 LOG_LEVEL で制御（デフォルト INFO）
- ローテーション: 日次、30 日分保持

重要なファイル・フラグ
---------------------
- data/kill.flag            — Kill Switch（ExecutionEngine 停止トリガ）
- data/stop_requested.flag  — run_* スクリプトのループ停止（手動停止用）
- data/execution.pid        — ExecutionEngine の PID 保存先（起動時）
- data/monitoring.db        — 監視用 SQLite（デフォルト）
- data/paper_trading.db     — ペーパートレード専用 SQLite（paper_trading 時）
- data/kabusys.duckdb       — DuckDB（分析用、デフォルト data/kabusys.duckdb）

設定（主要な環境変数）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト data/paper_trading.db)
- OPENAI_API_KEY (AI 機能を使う場合に必須)
- LOG_LEVEL (例: DEBUG, INFO)
- LOG_DIR (ログ保存先ディレクトリ)
- MONITOR_POLL_INTERVAL (run_monitoring でポーリング間隔を秒で上書き、デフォルト 60)
- PAPER_FILL_MODE (paper_trading の MockBroker 挙動: instant | partial | never | reject)

ディレクトリ構成（主要ファイル）
------------------------------
ここでは src/kabusys 以下を示します（プロジェクトルートに pyproject.toml/.git がある想定）。

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数/設定読み込みロジック
    - config_setup.py                — .env 対話式ウィザード
    - validate_config.py             — 設定検証 CLI
    - run_execution.py               — ExecutionEngine 起動スクリプト
    - run_monitoring.py              — Monitoring 起動スクリプト
    - utils/
      - logging_setup.py             — ログ設定ユーティリティ
      - process_priority.py          — 優先度 / CPU affinity
    - execution/                      — 注文実行関連（Engine, BrokerFactory, OrderManager 等）
    - monitoring/
      - monitoring_db.py             — 監視 DB 永続化レイヤ
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py                   — ニュースの LLM スコアリング
      - regime_detector.py            — 市場レジーム判定（LLM + MA）
    - data/ (実行時に作成されることが多い)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
    - tools/
      - paper_verification_report.py

設計上の注意点 / 運用メモ
-----------------------
- run_monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。監視 DB を別にしたい場合は設定を調整してください。
- ペーパートレードは本番 DB と完全に分離されることを想定しています（PAPER_TRADING_SQLITE_PATH）。
- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。API 呼び出しはリトライ／バックオフ／部分書き込み等の保護が組み込まれていますが、APIキーとコストに注意してください。
- ログディレクトリ作成に失敗した場合はコンソールログのみになります（設定関数内でハンドリングあり）。
- プロセス優先度・CPU affinity は psutil を使って設定します。権限不足や未対応 OS ではスキップされます。
- .env は絶対に Git にコミットしないでください（config_setup.py にも注記あり）。

開発 / テスト
--------------
- 設定の自動ロードはデフォルトで .env / .env.local をプロジェクトルートから読み込みます。テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを抑制できます。
- validate_config により起動前の基本チェックが可能です（YAML の解析は PyYAML がある場合のみ実施）。

貢献
----
バグ報告、改善提案、機能追加のプルリクエスト歓迎です。コードベースの慣習に従いユニットテストとドキュメントを追加してください。

---
必要であれば README に次の項目も追加できます:
- 具体的な .env の雛形（.env.example）
- 詳細な ExecutionEngine の挙動フロー図
- 各モジュール（AI / Monitoring / Execution）の API 使用例スニペット（小さなコード例）