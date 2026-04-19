KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python ベースのプロジェクトです。本コードベースは以下の主な機能群を含みます:

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理・再整合（reconciliation）を担う
- 監視（Monitoring）: システム状態・注文ログ・リスクの定期チェックとアラート／Kill Switch
- ポートフォリオ構築（Portfolio）: 候補選定、重み計算、ポジションサイズ計算、セクター制限などの純関数群
- リサーチ（Research）: ファクター計算・特徴量探索・IC / 統計サマリ機能（DuckDB を利用）
- AI モジュール: ニュースの NLP スコアリング（OpenAI）や市場レジーム判定
- ユーティリティ: 設定管理、ログ設定、プロセス優先度管理、各種スクリプト
- 運用ツール: Paper Trading の検証レポート生成スクリプト など

主な機能一覧
--------------
- 環境設定ウィザード（kabusys.config_setup）で .env を対話的に作成
- 設定検証ツール（kabusys.validate_config）で環境変数や config/*.yaml の整合性チェック
- Execution 起動スクリプト（kabusys.run_execution）:
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading DB に分離保存
  - 停止フラグ（data/stop_requested.flag）で安全に停止
- Monitoring 起動スクリプト（kabusys.run_monitoring）:
  - SystemMonitor 等を定期ポーリングして monitoring DB に永続化
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能
- Kill Switch（data/kill.flag）: リスク条件で Execution を止める仕組み
- Paper Trading 検証レポート（kabusys.tools.paper_verification_report）: 注文実績・稼働率・レイテンシの要約と PASS/FAIL 判定
- AI 系:
  - kabusys.ai.news_nlp.score_news: OpenAI を用いたニュースセンチメントの銘柄別スコア化（ai_scores へ書き込み）
  - kabusys.ai.regime_detector.score_regime: ETF とマクロ記事を組み合わせて市場レジーム判定

前提・依存
------------
- Python 3.10 以上（型注釈に | を利用しているため）
- 推奨 Python パッケージ（実行環境に合わせてインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML のパース検証に必要、任意）
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワーク: OpenAI API を使う場合は OPENAI_API_KEY

セットアップ手順
----------------
1. リポジトリをクローン / 配布を展開
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を手動作成
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本番運用時は KABUSYS_ENV を "live" に設定（注意して扱ってください）

5. 設定検証（起動前の必須ステップ）
   - python -m kabusys.validate_config
   - --strict オプションで警告も失敗扱いにできます:
     - python -m kabusys.validate_config --strict

6. データディレクトリ / DB ファイル
   - デフォルトの DB 等はプロジェクト内の data/ を使います:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - これらは自動作成されることが多いですが、事前に parent ディレクトリの存在を確認してください

使い方（主要コマンド）
--------------------
- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 失敗時は exit code != 0

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して paper_trading DB に結果を保存します
    - 停止は data/stop_requested.flag を作成することで実施できます（プロセスはフラグ検出後に停止）
    - 実行中は PID が data/execution.pid に書き込まれます

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定（デフォルト 60 秒）
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視用 DB は分離して使われます）
  - 停止は data/stop_requested.flag を作成してください

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI モジュール（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続を渡して指定日分のニュースをスコア化し ai_scores テーブルへ書き込み
    - api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込み

重要な環境変数（抜粋）
----------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ保存先、デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（本番での自動 Kill Flag クリア制御。0/1）

運用上の注意
-------------
- 本番（KABUSYS_ENV=live）では .env の管理に細心の注意を払ってください。LINE 通知設定が未設定だとアラートが届きません。
- Kill Switch（data/kill.flag）は手動または監視ロジックから書き込まれ、Execution を止めるための重要な仕組みです。本番で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアされるため危険です（デフォルトは 0）。
- OpenAI 呼び出しはレートリミットや一時エラーを想定してリトライ実装がありますが、API キーの管理・料金には注意してください。
- logs/ ディレクトリはログローテーションで運用されます（デフォルト 30 日保持）。

ディレクトリ構成
-----------------
（src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・.env 自動読み込みロジックと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 実行エンジン関連（broker, engine, order_manager, risk_manager 等）
  - monitoring/
    - monitoring_db.py       — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
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
    - news_nlp.py            — ニュースを OpenAI でスコアリング
    - regime_detector.py     — 市場レジーム判定
  - data/ (実行時に使用される想定)
    - monitoring.db (SQLite)
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag / stop_requested.flag

補足: DB スキーマ（監視用）
-------------------------
monitoring_db.init_monitoring_db() により以下のテーブルが作成されます（冪等）:
- system_status
- trade_logs（latency_ms カラムを含む）
- positions
- risk_logs
- dashboard（id=1 の 1 レコードを保持）

開発者向けメモ
---------------
- DuckDB を分析用に利用しているため、大規模な時系列クエリを高速に実行できます。
- research モジュールは外部 API に依存せず DuckDB のテーブル（prices_daily, raw_financials など）を参照する設計です。
- AI 呼び出し箇所（news_nlp / regime_detector）はテスト時に _call_openai_api をモックすることを想定しています。
- .env の自動ロードはデフォルトで有効ですがテスト時や特殊な環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。

ライセンス / 貢献
-----------------
（このリポジトリに付随するライセンス情報があればここに明記してください）

以上。セットアップや実行で不明点があれば、実行環境（OS, Python バージョン, インストールしたパッケージ）や実行コマンド・発生したエラーを添えて質問してください。