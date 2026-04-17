README
======

概要
----
KabuSys は日本株の自動売買と研究を支援する Python パッケージです。本リポジトリは以下の主要機能を持ちます。

- 発注・実行エンジン（ExecutionEngine）とそれを監視する Monitoring 周りのコンポーネント
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- ファクター計算・特徴量探索などのリサーチ用モジュール（DuckDB を使用）
- ニュースの NLP スコアリングおよび市場レジーム判定（OpenAI API 利用）
- Paper Trading 用ログ集計・検証レポート出力ユーティリティ
- .env の対話式ウィザードと設定検証ツール

この README はソース内の主要モジュールに基づく使用法・セットアップ手順・ディレクトリ構成を日本語でまとめたものです。

主な機能
--------
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB（data/paper_trading.db）へ記録する。
  - プロセス優先度を設定し、デーモン化されたスレッドで ExecutionEngine を実行する。
  - 停止は data/stop_requested.flag を検出してエンジンに stop() を送る仕組み。

- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングして system 状態・データ鮮度・リスクなどを記録。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト: 60 秒）。
  - 監視ログは SQLite（Settings.sqlite_path）に永続化。monitoring は環境に依らず本番 sqlite_path を使用する仕様。

- Monitoring Engine（monitoring_engine.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ね、KillSwitch 評価やアラート送出を行う。

- 監視・ログ永続化（monitoring.monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard のテーブル管理とマイグレーション処理。

- ポートフォリオ構築（portfolio/*）
  - 候補選定（select_candidates）
  - 等金額・スコア加重の重み計算
  - ポジションサイズ計算（risk_based / equal / score）
  - セクター上限やレジーム乗数の適用

- リサーチ（research/*）
  - momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ai/*）
  - ニュース NLP による銘柄センチメントスコアリング（OpenAI）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（OpenAI）

- ツール
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

必要条件（依存）
----------------
最低限のランタイム依存（推奨インストール例）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定検証で config/*.yaml の読み込み検査を行う場合、任意）

例:
pip install duckdb psutil openai pyyaml

※requirements.txt がある場合はそれを利用してください。

セットアップ手順
----------------
1. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

2. 依存パッケージをインストール
   pip install duckdb psutil openai pyyaml

3. .env の作成（対話式ウィザード推奨）
   python -m kabusys.config_setup
   - ウィザードは .env ファイルを生成／更新します。
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合は OPENAI_API_KEY を環境に設定してください（ウィザードでは OPENAI_API_KEY を直接扱いません）。

4. 設定検証
   python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

環境変数（主なもの）
-------------------
- KABUSYS_ENV: execution 動作モード
  - development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用監視 DB（paper_trading）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視や Kill Switch の制御

使い方（コマンド例）
-------------------

- .env ウィザード（対話式）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine の起動（通常実行）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使って data/paper_trading.db に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag を作成すると安全停止します。

- Monitoring の起動（ポーリング監視）
  python -m kabusys.run_monitoring
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で調整可（デフォルト 60 秒）。
  - データベースは Settings.sqlite_path を使用（環境にかかわらず本番 sqlite_path を参照）。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を優先）。

- AI 実行（プログラム的に）
  - ニュース NLP:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

注意点・運用メモ
----------------
- Paper Trading と本番 DB は完全に分離されています（Settings.paper_sqlite_path）。
- run_monitoring は監視ログに本番の sqlite_path を使用します（環境にかかわらず）。
- 停止制御:
  - data/stop_requested.flag: run_* スクリプトがループ停止に使うフラグファイル
  - data/kill.flag: KillSwitch が書き込むと ExecutionEngine に停止信号を送る（ExecutionEngine 起動時の設定に依存）
- プロセス優先度: 起動時に psutil を使って優先度を "high" に設定しようとします。権限や OS により設定失敗する場合がありますが、その場合は警告を出してスキップします。
- OpenAI 関連:
  - OPENAI_API_KEY が未設定の場合、AI 機能は ValueError を投げます（score_news / score_regime 等）。
  - API 呼び出しはリトライとバックオフを実装していますが、呼び出しコストが発生します。運用時は API レートと課金に注意してください。

主要なパブリック API（プログラム的利用）
---------------------------------------
（一部抜粋）
- kabusys.portfolio:
  - select_candidates, calc_equal_weights, calc_score_weights
  - calc_position_sizes
  - apply_sector_cap, calc_regime_multiplier

- kabusys.research:
  - calc_momentum, calc_volatility, calc_value
  - calc_forward_returns, calc_ic, factor_summary, rank

- kabusys.ai:
  - score_news（ニュース NLP）、score_regime（市場レジーム）

- kabusys.monitoring:
  - MonitoringDB、MonitoringEngine、各 Monitor（SystemMonitor / TradeMonitor / RiskMonitor）、KillSwitch、AlertManager（アラート連携用）

ディレクトリ構成
----------------
以下は src/kabusys 以下の主なファイル／モジュール（抜粋）です。

- __init__.py
- config.py                — 環境変数と Settings 管理（.env 自動読み込み含む）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

- ai/
  - news_nlp.py            — ニュースの LLM スコアリング
  - regime_detector.py     — 市場レジーム判定

- monitoring/
  - monitoring_db.py       — SQLite 永続化層（テーブル作成・操作）
  - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
  - system_monitor.py      — システム状態・データ鮮度監視
  - trade_monitor.py       — 注文滞留・約定異常監視
  - risk_monitor.py        — ドローダウンやポジション上限監視
  - kill_switch.py         — kill.flag 制御
  - alert_manager.py       — アラート送出（LINE 等への送信機能を想定）

- execution/               — Execution エンジン関連（OrderManager, BrokerFactory 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- tools/
  - paper_verification_report.py

- utils/
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

補足: DB 初期化・マイグレーション
------------------------------
- monitoring_db.init_monitoring_db(conn) はテーブル作成を冪等で行い、既存 DB に対して必要なカラム追加（例: peak_value, latency_ms）を行います。

ライセンス・貢献
----------------
この README はコードベースの説明用です。実運用にあたっては各自のライセンス・内部規約に従ってください。バグ修正や機能追加の貢献は Pull Request を受け付ける形で進めてください。

お問い合わせ
------------
実装や使い方に関する質問があれば、リポジトリの Issue を作成してください。