README
====

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤です。本リポジトリはトレード実行エンジン、監視 (Monitoring)、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM を用いたセンチメント評価）などのコンポーネントを含みます。設計方針として「本番とテスト（ペーパートレード）の分離」「ルックアヘッドバイアス回避」「外部 API 呼び出しは明示制御」などを採用しています。

主な機能
--------
- ExecutionEngine：ブローカークライアント経由の注文管理（本番 / ペーパートレード切替対応）
- Monitoring：システム稼働状況、注文ログ、リスク監視、Kill Switch の自動評価と通知
- Portfolio Construction：候補選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数
- Research：DuckDB を使ったファクター計算（モメンタム / バリュー / ボラティリティ）や特徴量解析
- AI：OpenAI API を用いたニュースのセンチメントスコアリング・市場レジーム判定
- ツール：Paper Trading 検証レポート生成スクリプトなど
- 設定支援：対話式 .env ウィザード（config_setup）と起動前検証 CLI（validate_config）
- 統一ログ設定ユーティリティ（ログはコンソール + 日次ローテートファイル出力）

動作環境 / 必要条件
------------------
- Python 3.10+
- SQLite（標準ライブラリ）
- DuckDB Python パッケージ
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の内容チェックを行う場合、必須ではない）

推奨パッケージ（例）
- duckdb
- psutil
- openai
- pyyaml

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml

   （requirements.txt があれば pip install -r requirements.txt を使用）

4. .env の初期作成（対話型ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや kabu API パスワード、KABUSYS_ENV 等を入力して .env を作成します。

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリ / ログディレクトリ
   - デフォルトで data/ と logs/ を使用します（存在しない場合は自動作成されます）。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / LOG_DIR を変更してください。

使い方
------
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録します。本番と完全に分離されます。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。監視は環境に関係なく本番 sqlite_path を使用します。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可）

- AI / Research の呼び出し（ライブラリとして）
  - Python コード内でモジュールをインポートして使用可能です。
  - 例: from kabusys.ai.news_nlp import score_news
  - DuckDB 接続を渡して関数を呼ぶ設計になっています（外部から DB 接続を渡してください）。

環境変数（主要）
----------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — default: development
  - paper_trading: 実際の発注を行わず MockBroker を使用
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db（Monitoring 用、本番 DB）
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db（ペーパートレード時の DB）
- LOG_LEVEL — default: INFO
- LOG_DIR — default: logs/
- OPENAI_API_KEY — AI 機能を使う場合のキー
- PAPER_FILL_MODE — ペーパートレード時のフィルモード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0|1）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

停止 / Kill Switch / フラグ
--------------------------
- 監視スレッド・実行スレッドの停止:
  - プロセスはプロジェクトルート/data/stop_requested.flag の存在を監視しています（run_monitoring.py / run_execution.py）。このファイルを作成するとループが検知して正常終了します。
- Kill Switch:
  - リスク条件（ドローダウンやポジション上限）に応じて monitoring の KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KILL_FLAG_CLEAR_ON_START=1 により起動時に自動クリアする設定が可能（本番では 0 推奨）。
- PID ファイル:
  - 実行エンジンは data/execution.pid を使います（Settings.pid_file_path で変更可能）。

ログ
---
- ログはコンソールに出力され、デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日分保持）。
- setup_logging(app_name="execution" など) を各起動スクリプトで呼び出しています。

コード構成（主要ファイル）
------------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数の読み込み・Settings
- config_setup.py          — .env 対話型ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）によるスコアリング
  - regime_detector.py     — マーケットレジーム判定（AI + MA）
- monitoring/
  - monitoring_db.py       — Monitoring 用 SQLite 永続化層
  - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py       — （発注ログ監視関連）
  - risk_monitor.py        — ドローダウン・ポジション上限チェック
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - kill_switch.py         — Kill Switch 実装
  - alert_manager.py       — （通知ラッパー）
- execution/                — 注文実行に関するモジュール群（BrokerFactory, Engine, OrderManager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定
- data/ (実行時に使用)
  - stop_requested.flag, kill.flag, monitoring.db, paper_trading.db など

補足 / 運用上の注意
------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live のときは特に注意が必要です。validate_config は本番向けの追加警告を出します。
- AI 機能は OpenAI API を利用します。料金・レート制限に注意し、API キーの管理を行ってください。
- DuckDB / SQLite ファイルのパスは .env で変更可能です。監視用 DB とペーパートレード DB は分離する設計です。

問い合わせ / 貢献
----------------
- バグ報告や改善提案は Issue を立ててください。
- 開発に参加する場合はブランチを切り、Pull Request を送ってください。テストや static type チェックの追加を歓迎します。

以上。README に不明な点や追加してほしいドキュメント（API 使用例、設定テンプレート、運用手順書など）があれば教えてください。