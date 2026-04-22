KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株を対象とした自動売買システムのコアライブラリです。本リポジトリには以下の主要コンポーネントが含まれます。

- ExecutionEngine: 発注処理・オーダー管理・リスク管理を担う実行系
- Monitoring: システム稼働監視、トレード監視、リスク監視、Kill Switch（停止フラグ）制御
- Portfolio: 銘柄選定・重み計算・枚数決定（ポジションサイジング）
- Research: DuckDB を使ったファクター計算・特徴量解析
- AI モジュール: ニュースの NLP スコアリング、レジーム判定（OpenAI を利用）
- Tools: ペーパートレード検証レポート生成などのユーティリティ
- Utils: ロギング設定・プロセス優先度設定など実行補助

本 README では機能一覧、セットアップ、使い方、ディレクトリ構成を記載します。

主な機能
--------
- 実行エンジン（ExecutionEngine）による発注フロー（paper_trading モードでの MockBroker 対応）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と MonitoringEngine による定期チェック
- Kill Switch（data/kill.flag）による安全停止（閾値超過時に Execution を停止）
- 監視ログ永続化（SQLite）および分析用 DuckDB のサポート
- ポートフォリオ構築（候補選定、等重/スコア重み、リスクベース発注量計算、セクター制約等）
- リサーチ機能（モメンタム、ボラティリティ、バリューファクター、IC 計算 等）
- OpenAI を用いたニュースセンチメント評価（ai.news_nlp）とレジーム判定（ai.regime_detector）
- ペーパートレード用検証レポート生成スクリプト（tools/paper_verification_report.py）
- 開発用の .env ウィザード（config_setup.py）と設定検証 CLI（validate_config.py）
- ログ設定ユーティリティ（TimedRotatingFileHandler、コンソール出力）

前提 / 依存関係
---------------
最低限の推奨環境（例）
- Python 3.10+
- SQLite（標準ライブラリで利用）
- 必須 Python パッケージ（プロジェクトの requirements.txt がある場合はそちらを使用）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config/*.yaml の構文チェックを行う validate_config で推奨）
- OS: Linux / macOS / Windows（プロセス優先度の設定はプラットフォーム差分あり）

セットアップ手順
----------------
1. リポジトリをクローンしてチェックアウト
   - 例: git clone <repo-url>

2. Python 仮想環境を作成し有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai
   - （PyYAML を入れる場合）pip install pyyaml
   - ※ プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用

4. 環境変数 / .env の準備
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成してプロジェクトルートに置く
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（例: data/monitoring.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（paper_trading 時のフィルモード: instant | partial | never | reject）
   - .env は機密情報を含むため Git にコミットしないでください。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います:
     - python -m kabusys.validate_config --strict

6. データディレクトリ・ログディレクトリの作成（必要に応じて）
   - data/ ディレクトリ（SQLite DB や pid/flag 保存用）
   - logs/ ディレクトリ（ログファイル保存用）
   - 多くのコードは起動時に自動作成されますが、権限等の確認はしておいてください。

使い方（実行例）
----------------

- 実行エンジン（ExecutionEngine）を起動
  - Python モジュール実行:
    - python -m kabusys.run_execution
  - 挙動
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、紙(データ)は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）に記録
    - 起動時に data/stop_requested.flag が存在すると起動を中止します
    - 実行中に data/stop_requested.flag を作成するとエンジンが停止します
    - PID ファイルは data/execution.pid（設定で変更可能）に出力されます

- 監視プロセスを起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は Settings.sqlite_path（monitoring DB）に書き込みします（環境に関わらず本番 sqlite_path を使用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db PATH または 環境変数 PAPER_TRADING_SQLITE_PATH を利用

- AI 関連関数（コード呼び出し例）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を省略すると環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

運用に関する注意
----------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live の設定では実際に発注が行われます。十分に検証してから運用してください。
- Kill Switch（data/kill.flag）は ExecutionEngine の停止トリガーです。KILL_FLAG_CLEAR_ON_START が 1 のときは起動時に自動削除されますが、本番では 0 を推奨します。
- OpenAI API を利用する機能は API キーと利用コスト、レート制限に注意してください。リトライやフェイルセーフは実装されていますが、過度な呼び出しは避けてください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの権限・容量を監視してください。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要モジュール・ファイル構成（抜粋）です。

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - execution/               — 実行系 (Engine, OrderManager, BrokerFactory, RiskManager, Reconciler 等)
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 利用）
    - regime_detector.py     — レジーム推定（OpenAI 利用）
  - tools/
    - paper_verification_report.py

補足（よく使うファイル / フラグ）
- data/monitoring.db            — 監視用 SQLite（デフォルト）
- data/paper_trading.db         — ペーパートレード用 DB（paper_trading モード）
- data/execution.pid            — ExecutionEngine の PID ファイル（設定可能）
- data/stop_requested.flag      — 起動しない / 停止要求用フラグ（run_execution / run_monitoring が参照）
- data/kill.flag                — Kill Switch 用フラグ（ExecutionEngine 停止トリガー）
- logs/                         — ログ出力先（デフォルト）

トラブルシューティング
----------------------
- .env が読み込まれない場合:
  - プロジェクトルートが .git または pyproject.toml を基準に検出されないと自動読み込みをスキップします。config_setup で直接ファイルを書き出すか、環境変数を手動で設定してください。
- OpenAI 関連で認証エラーが出る場合:
  - OPENAI_API_KEY を確認してください。API キーの形式・権限・課金状況も確認してください。
- ログファイルが作成されない場合:
  - logs/ ディレクトリへの書き込み権限とディスク容量を確認してください。logging_setup は作成に失敗した場合にコンソール出力のみで継続します。

ライセンス・貢献
----------------
本 README にライセンス情報は含めていません。実際のライセンス・貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

最後に
-----
この README はコードベース（src/kabusys）から読み取れる主要な機能・利用方法をまとめたものです。追加の実行スクリプトや設定ファイル（config/*.yaml、scripts/generate_config.py 等）がある場合は、それらのドキュメントも合わせて参照してください。質問や追加のドキュメント化が必要であればお知らせください。