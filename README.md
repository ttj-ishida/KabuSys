README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python ベースのプロジェクトです。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine: 発注ロジック（本番 / ペーパートレード切替）
- Monitoring: システム稼働監視・アラート・Kill Switch
- Portfolio 建設ロジック（候補選定・重み付け・ポジションサイズ決定）
- Research: ファクター計算・特徴量探索ユーティリティ（DuckDB 利用）
- AI 補助モジュール: ニュース NLP によるセンチメント評価・レジーム判定（OpenAI）
- 運用ツール: .env ウィザード、設定検証、ペーパートレード検証レポート生成 など

動作の前提として DuckDB、SQLite、およびいくつかの外部ライブラリ（psutil, openai 等）を利用します。

主な機能一覧
-------------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV により本番/ペーパートレードを切替。
  - ペーパートレード時は専用 SQLite（data/paper_trading.db）へ記録し、本番 DB と分離。
  - プロセス優先度（High）設定、pid ファイル出力、stop_flag による安全停止。
- run_monitoring.py
  - SystemMonitor（CPU/メモリ/ディスク・プロセス生存・データ鮮度）を定期ポーリングし
    SQLite にログを残す。ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で変更可（秒）。
- monitoring パッケージ
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine。
  - KillSwitch（data/kill.flag）や監視用 DB（monitoring_db）を提供。
- portfolio パッケージ
  - 銘柄選定（select_candidates）、重み計算（等金額・スコア重み）、ポジションサイズ計算、
    セクター上限適用、レジーム乗数などの純関数群。
- research パッケージ
  - DuckDB 上の prices_daily / raw_financials を用いたファクター計算（momentum/value/volatility）、
    将来リターン計算、IC（スピアマン）や統計サマリ等。
- ai パッケージ
  - news_nlp: raw_news から銘柄ごとにニュースを集め OpenAI でセンチメントを評価し ai_scores に書き込む。
  - regime_detector: ETF MA とマクロニュースの LLM スコアを合成して market_regime に書き込む。
- tools
  - paper_verification_report: ペーパートレード DB を解析し検証レポートを標準出力に生成。

セットアップ手順
----------------

1. Python 環境準備
   - 推奨: Python 3.10+（実際の互換性はコードベースに応じて調整してください）
   - 仮想環境を作成・有効化（例）
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール
   - requirements.txt は付属していない場合があります。最低限必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクト設定 (.env)
   - 対話式ウィザードで .env を生成/更新:
     - python -m kabusys.config_setup
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定例:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY: OpenAI を使用する場合
     - DUCKDB_PATH: DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（例: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（オプション）
     - LOG_LEVEL / LOG_DIR
     - KILL_FLAG_CLEAR_ON_START（本番では 0 推奨）
   - 自動ロードについて:
     - プロジェクトルートの .env / .env.local は自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

4. 設定検証
   - 起動前に検証スクリプトで設定の整合性を確認:
     - python -m kabusys.validate_config
     - 警告を厳密に扱う場合: python -m kabusys.validate_config --strict

5. データディレクトリ
   - ログディレクトリ（デフォルト: logs/）と DB 保存先（data/）は自動作成されますが、パーミッションなどに注意してください。

使い方（コマンド例）
-------------------

- 実行（ExecutionEngine）
  - 本番 / ペーパートレードを .env の KABUSYS_ENV で切替:
    - python -m kabusys.run_execution
  - 停止: data/stop_requested.flag を作成すると起動中のループが検知して停止します（または kill.flag を用いて ExecutionEngine 停止シグナルを送る運用もあります）。
  - PID ファイル: data/execution.pid（設定により変更可）

- 監視（Monitoring）
  - ポーリング監視を起動:
    - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    - ポーリング間隔（秒）は MONITOR_POLL_INTERVAL 環境変数で上書き可能（デフォルト 60s）
  - 停止: data/stop_requested.flag を作成すると監視ループが終了します。

- 設定ウィザード / 検証
  - .env を作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を直接指定: --db /path/to/paper_trading.db
  - 簡易基準（稼働率・成功率・レイテンシ等）に基づく PASS/FAIL 判定を出力します。

- AI / リサーチ関数の利用（ライブラリ呼び出し）
  - ai の関数はライブラリ API で利用します（例: kabusys.ai.score_news）。
  - これらは DuckDB 接続と API キー（OPENAI_API_KEY）を必要とします。スクリプトとして直接起動するエントリは実装に依存しますので、ライブラリとしてインポートして利用してください。

運用上の注意
------------
- Kill Switch / stop フラグ
  - data/kill.flag: KillSwitch が書き込むファイルで、ExecutionEngine に対する停止要求を示します。
  - data/stop_requested.flag: サービス全体（監視・実行ループ）を停止させるための外部フラグ（run_* スクリプトが検知）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なので 0 を推奨します。

- ログ
  - 共通ログ設定関数 setup_logging() により logs/<app_name>.log に日次ローテーションでログ出力されます。
  - LOG_LEVEL / LOG_DIR を環境変数で調整可能。

- DB
  - monitoring 用 SQLite は settings.sqlite_path（デフォルト data/monitoring.db）
  - DuckDB は分析用（デフォルト data/kabusys.duckdb）
  - ペーパートレードDB は settings.paper_sqlite_path（デフォルト data/paper_trading.db）

ディレクトリ構成（主要ファイル・モジュール）
-------------------------------------------
以下は src/kabusys 以下の主要ファイル構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py         — ロギング設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py         — 監視 DB テーブル定義・永続化 API
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （取引監視、コードベースに実装有り） 
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — kill.flag 書き込みロジック
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
    - alert_manager.py         — （アラート送信を担う想定コンポーネント）
  - execution/
    - execution_engine.py      — ExecutionEngine 本体（起動 / セッション管理）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI 依存）
    - regime_detector.py      — レジーム判定（MA + マクロニュース LLM）
    - __init__.py
  - data/                      — 実行時生成される DB / フラグ / PID ファイルの格納先（想定）
    - monitoring.db (default)
    - paper_trading.db (paper)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/                      — ログファイル出力先（デフォルト）

追加情報 / 開発者向けメモ
-----------------------
- .env は絶対にリポジトリにコミットしないでください（README 内の .env.example を参照してください）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）から行います。パッケージ配布後もファイル起点で動くよう実装されています。
- AI モジュールは OpenAI API の呼び出しを伴い、失敗時は安全にフォールバックするよう設計されています（429/5xx などはリトライ/フォールバック処理あり）。
- DuckDB / SQLite のスキーマはコードで管理されており、init_monitoring_db() が必要なテーブル作成とマイグレーションを行います。
- テスト時には環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って自動 .env ロードを抑制できます。

問い合わせ / 貢献
----------------
バグ報告や機能改善の提案は issue を立ててください。コード改修の際は README と .env.example（プロジェクトに含める場合）を更新し、ドキュメントの整合性を保つようにお願いします。

以上が本コードベースの概要と起動手順です。必要があれば、特定のモジュール（例: ExecutionEngine の設定、AI スクリプトの具体的な使い方、DB スキーマ詳細）のドキュメントを追加で作成します。どの項目を詳述しますか？