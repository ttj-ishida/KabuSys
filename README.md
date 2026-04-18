README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした軽量なフレームワークです。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine（発注エンジン）による実売買 / ペーパートレード（分離された DB）
- Monitoring（監視）コンポーネント群によるシステム健全性・注文状況・リスク監視と Kill Switch
- Portfolio 構築（候補選定・重み付け・ポジションサイズ算出・セクター制限など）
- Research（ファクター計算・特徴量探索）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI を用いたスコアリング
- 運用支援ツール（対話式 .env ウィザード、設定検証、Paper Trading 検証レポート生成）

主な設計方針
- 本番とペーパートレードは SQLite DB を分離（PAPER_TRADING_SQLITE_PATH）
- 実行時のログは統一的に設定（logs/<app>.log、日次ローテーション）
- 自動環境読み込み（.env / .env.local）を備え、config_setup で .env を作成可能
- AI 呼び出しは OpenAI API（OPENAI_API_KEY）を利用。API 失敗時はフェイルセーフ設計

機能一覧
--------
- run_execution: ExecutionEngine 起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB に記録
  - 起動時にプロセス優先度を "high" に設定
  - stop flag（data/stop_requested.flag）を検知して安全停止
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視結果は monitoring DB（SQLite）に永続化
- config_setup: 対話式 .env 作成・更新ウィザード
- validate_config: 環境変数や config/*.yaml の前提チェック CLI（--strict あり）
- tools.paper_verification_report: ペーパートレード用の検証レポート生成
- portfolio: 候補選定・等重/スコア重み付け・ポジションサイズ算出・セクターキャップ・レジーム乗数
- research: DuckDB を使ったファクター計算（Momentum/Value/Volatility）と特徴量解析ユーティリティ
- ai: news_nlp（ニュース → センチメント）、regime_detector（マクロ＋ETF MA200 でレジーム判定）
- monitoring: MonitoringDB（永続化層）、SystemMonitor、RiskMonitor、KillSwitch、MonitoringEngine、AlertManager（通知連携は別実装想定）
- utils: ログの統一セットアップ、プロセス優先度 / CPU affinity 管理 等

動作前提 / 推奨
----------------
- Python 3.10 以上
- 必須ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - sqlite3（標準ライブラリ）
  - （オプション）PyYAML: config/*.yaml の構文チェックで利用
- データディレクトリ: data/ に DB や PID/flag ファイルを格納
- ログディレクトリ: logs/（デフォルト。環境変数 LOG_DIR で変更可）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合は .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai
   - （開発用）pip install PyYAML

   ※ 実プロジェクトでは requirements.txt を用意して pip install -r requirements.txt を使ってください。

4. 対話式で .env を作成
   - python -m kabusys.config_setup
   - 作成した .env は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗（exit 1）として扱います。

6. DB 初期化
   - 実行／監視スクリプトは起動時に必要テーブルを作成します（init_monitoring_db が冪等で実施）。

主な環境変数（抜粋）
--------------------
- KABUSYS_ENV: execution モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレードの約定動作（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方（主要コマンド）
--------------------
- 実行用エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH に記録
    - data/stop_requested.flag を検知して停止
    - 起動時に data/execution.pid を使用（設定で変更可）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で秒を指定（例: export MONITOR_POLL_INTERVAL=30）
  - 監視結果は SQLITE_PATH（監視 DB）に書き込まれます

- .env 対話式ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュールの呼び出し（ライブラリ的に使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY が不要な場合は api_key 引数で明示的に渡す

運用上の注意
------------
- Kill Switch: risk_monitor が条件を満たすと data/kill.flag が作成され、ExecutionEngine に停止シグナルを送ります。起動時に KILL_FLAG_CLEAR_ON_START=1 にしていると自動クリアされますが、本番では 0 を推奨します。
- ログ: デフォルトで logs/<app_name>.log に日次で出力されます。LOG_DIR で変更可。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び出します。権限不足等で警告が出る場合がありますが、実行自体は継続します。
- データの整合性: DuckDB/SQLite の書き込みはトランザクションを使って冪等に設計されています。AI 呼び出しで部分失敗しても既存データを不必要に消さないような実装になっています。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / .env ロード・Settings
- config_setup.py          — 対話式 .env ウィザード
- validate_config.py       — 起動前チェック CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

modules / サブパッケージ:
- execution/                — ブローカー、ExecutionEngine、OrderManager 等（発注ロジック）
- monitoring/
  - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py       — システム・データ鮮度チェック
  - risk_monitor.py         — ドローダウン・ポジション数の監視
  - kill_switch.py          — data/kill.flag 操作
  - monitoring_engine.py    — 複数モニタの統合（ポーリング）
  - trade_monitor.py        — 注文滞留・約定異常監視（実装ファイルあり）
  - alert_manager.py        — 通知送信を担う想定（実装参照）
- portfolio/
  - portfolio_builder.py    — 候補選定、重み付け
  - position_sizing.py      — 発注株数計算
  - risk_adjustment.py      — セクター上限・レジーム乗数
- research/
  - factor_research.py      — Momentum / Volatility / Value 計算
  - feature_exploration.py  — 将来リターン、IC、統計サマリ
- ai/
  - news_nlp.py             — ニュース → センチメント（OpenAI 呼出）
  - regime_detector.py      — ETF MA200 + マクロセンチメントでレジーム判定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- utils/
  - logging_setup.py        — ログ初期化ユーティリティ（Stream + TimedRotatingFile）
  - process_priority.py     — プロセス優先度 / CPU affinity 操作

補足
----
- 本 README はコードベースからの要点を抜粋して記載しています。各モジュールの詳細な利用方法や追加の設定は該当ソース内 docstring / コメントを参照してください。
- 開発・テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（ユニットテスト等で有用）。

ライセンス / 責任
-----------------
- 本プロジェクトを運用する際は各外部 API（kabuステーション、J-Quants、OpenAI 等）の利用規約とレート制限に留意してください。
- 実環境での自動売買はリスクが伴います。十分な検証・監視・ガード（Kill Switch 等）を行ってください。