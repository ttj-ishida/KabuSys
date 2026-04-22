KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視のための内部モジュール群です。本リポジトリは以下の主要機能を持ちます。

- 発注エンジン（ExecutionEngine） — 実際の発注 / ペーパートレード切替
- 監視（Monitoring） — システム稼働状況・注文状況・リスク監視・Kill Switch
- ポートフォリオ構築（候補選定・配分・ポジションサイズ計算・リスク調整）
- 研究（ファクター計算、将来リターン、IC 等）
- AI 関連（ニュース NLP によるセンチメント / レジーム判定）
- ツール（ペーパートレード検証レポート、設定ウィザード、設定検証 CLI）
- 共通ユーティリティ（ロギング設定、プロセス優先度設定、設定読み込み等）

主な特徴
--------
- 本番 / 開発 / ペーパートレードの切替（KABUSYS_ENV）
- Paper Trading 時は実アカウントと完全分離された SQLite を利用
- DuckDB を用いた時系列データ（prices_daily, raw_financials 等）の解析機能
- OpenAI を用いたニュース評価（ai.news_nlp）／レジーム判定（ai.regime_detector）
- 監視用 SQLite（monitoring.db）への永続化、アラート発行のフック
- ログはコンソール + 日次ローテートファイル出力（logs/*.log）

動作要件
--------
- Python 3.10+
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 標準ライブラリ: sqlite3, threading, logging 等

推奨インストール例
------------------
（仮想環境を使用することを推奨します）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

セットアップ手順
----------------

1. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークンや kabu API パスワード、DB パス、KABUSYS_ENV 等を設定します。
   - .env を絶対にリポジトリにコミットしないでください。

2. 設定の検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

3. データディレクトリ作成（必要であれば）
   - デフォルトの DB・ログ保存先はプロジェクト配下の data/ と logs/ です。config で変更可能。
   - 例: mkdir -p data logs

4. OpenAI API を使う場合
   - 環境変数 OPENAI_API_KEY を設定
   - あるいは ai.score_regime / score_news の呼び出し時に api_key を渡す

主要な環境変数（概要）
---------------------
以下は主な環境変数とデフォルト値の抜粋。詳細は config.py と config_setup.py を参照してください。

- JQUANTS_REFRESH_TOKEN — （必須）J-Quants API リフレッシュトークン
- KABU_API_PASSWORD — （必須）kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db（paper_trading 用 DB）
- PAPER_FILL_MODE — instant|partial|never|reject（デフォルト: instant）
- KABUSYS_ENV — development|paper_trading|live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI 利用時に必要
- PID_FILE_PATH — デフォルト: data/execution.pid
- KILL_FLAG_PATH — デフォルト: data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 0/1（デフォルト: 0。1 は起動時に kill.flag を自動クリア）

使い方
-----

設定関連
- 対話式 .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - 成功時は exit code 0、エラーありは 1（--strict で警告も失敗扱い）

監視（Monitoring）
- 監視プロセス起動:
  - python -m kabusys.run_monitoring
  - ログ: logs/monitoring.log（デフォルト）
- ポーリング間隔を環境変数で変更:
  - MONITOR_POLL_INTERVAL 秒（デフォルト: 60）
- 監視は KABUSYS_ENV にかかわらず production sqlite_path（SQLITE_PATH）を使用します（設計上の注意）。
- 停止方法:
  - data/stop_requested.flag ファイルを作成するとループが検知して終了します。

実行エンジン（Execution）
- エンジン起動:
  - python -m kabusys.run_execution
  - 実行時 KABUSYS_ENV により挙動が変わります:
    - paper_trading: MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH を使用（本番 DB と分離）
    - live/development: 設定に従って実ブローカー/設定を使用
- 停止方法:
  - data/stop_requested.flag を作成すると実行エンジンへ停止シグナルを送ります（スレッドを停止）
  - Kill Switch（監視側）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止を要求します
- PID:
  - 実行中は PID_FILE_PATH（デフォルト data/execution.pid）を使用します

ツール
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

ライブラリ呼び出し（開発用途）
- ニューススコア生成:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key=None)
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)
- ポートフォリオ機能:
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes 等

DB・マイグレーション
- 監視 DB の初期化/マイグレーションは init_monitoring_db が行います（冪等）。起動時に自動実行されます。
- monitoring DB（SQLITE_PATH）は system_status, trade_logs, positions, risk_logs, dashboard 等のテーブルを持ちます。

ログ
---
- ログはコンソール（stdout）とファイルに出力されます（logs/<app_name>.log、日次ローテート、30 日保持）。
- ロギング設定は kabusys.utils.logging_setup.setup_logging で統一管理されています。

停止・Kill Switch の仕組み
-------------------------
- 停止フラグ（グローバル停止）:
  - data/stop_requested.flag が存在すると run_execution / run_monitoring のメインループが検知して終了します（安全なシャットダウン）。
- Kill Switch（リスク基づく強制停止）:
  - monitoring の KillSwitch が条件を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動時にこれを検出・監視しているため、kill.flag によってトレードを停止します。

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定読み込み
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py           — レジーム判定（ma200 + macro sentiment）
  - monitoring/
    - monitoring_db.py             — monitoring 用 SQLite 永続化層
    - system_monitor.py            — システム / データ鮮度監視
    - trade_monitor.py             — 注文滞留 / 約定異常等の監視（実装ファイルあり）
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag 操作ユーティリティ
    - monitoring_engine.py         — 各 Monitor を束ねる実行ループ
    - alert_manager.py             — アラート通知（実装ファイルが提供されている想定）
  - execution/
    - execution_engine.py          — 発注エンジン本体（実装ファイルがある想定）
    - broker_factory.py            — ブローカークライアント生成（Mock/実ブローカー切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

開発者向けメモ
---------------
- 型ヒント: Python 3.10 の新しい union 型（A | B）表記を使用しているため、Python 3.10 以上を推奨します。
- DuckDB を内部分析用に利用しています。prices_daily / raw_financials 等のテーブルに依存する関数は DuckDB 接続を引数に取ります。
- OpenAI 呼び出しは openai パッケージ（現行コードは OpenAI クライアント呼び出しラッパー）を使っています。テスト時は _call_openai_api をモックする設計になっています。
- ローカルでペーパートレードを試す場合は KABUSYS_ENV=paper_trading に設定し、paper_trading 用 DB を利用してください。

トラブルシューティング
----------------------
- .env を読み込まない / テストで自動ロードを抑制したい:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロード処理をスキップします。
- ログファイルの出力に失敗する場合:
  - logs/ ディレクトリの書き込み権限を確認、または環境変数 LOG_DIR で書き込み先を変更してください。
- OpenAI エラーやレート制限:
  - ニュース NLP / レジーム判定はリトライロジックを持ちますが、APIキー・クォータを確認してください。

最後に
------
本 README はコードベースの主要点をまとめた簡易ドキュメントです。各モジュール（monitoring, execution, ai, portfolio, research）にはドキュメント文字列と設計コメントが豊富にありますので、詳細は該当ファイルを参照してください。問題や改良点があればリファクタ・テストの追加を歓迎します。