KabuSys — 日本株自動売買システム
================================

このリポジトリは、日本株向けの自動売買システムのコアライブラリです。  
ポートフォリオ構築、ポジションサイジング、監視・キルスイッチ、ペーパートレード検証、ニュースNLP / レジーム判定など、取引ロジックと運用周りのユーティリティが含まれます。

主な特徴
--------
- 環境設定管理 (.env 読み込み・対話式ウィザード)
- ExecutionEngine（発注実行エンジン）と Monitoring（監視） の起動スクリプト
- Paper Trading（ペーパートレード）用の分離された SQLite DB サポート
- モニタリング：システム状態 / 注文監視 / リスク監視 / キルスイッチ
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算・セクター制限）
- 研究用モジュール（ファクター計算・IC 計算・特徴量解析）
- AI モジュール（ニュースセンチメント評価・市場レジーム判定） — OpenAI を利用
- レポート生成ツール（Paper Trading 検証レポート）

セットアップ手順
----------------
1. リポジトリをクローン:
   - git clone <repository-url>

2. Python 環境を作成（推奨: venv）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール:
   - pip install duckdb psutil openai
   - 任意: PyYAML（config 検証で YAML 検査を有効にする場合）: pip install PyYAML

   ※ 実運用用の requirements.txt がある場合はそれを使用してください。

4. 初期設定 (.env) を作成:
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を手動作成（.env.example を参照）

5. 設定検証:
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合: python -m kabusys.validate_config --strict

6. データディレクトリ:
   - デフォルトで data/ に DB 等が作られます。必要なら事前に作成してください。
   - デフォルトパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

使い方（主要スクリプト）
-----------------------

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用して本番 DB と分離します。
    - 起動時に data/stop_requested.flag を検知していれば起動をスキップします。
    - 実行中に stop フラグを検出するとエンジンを停止します。
    - PID ファイル（デフォルト data/execution.pid）を管理します。

- Monitoring（監視ポーリング）起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL（秒、デフォルト 60）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず）。
  - 停止フラグ: プロジェクト内 data/stop_requested.flag を置くとループを終了します。

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - 対話式に .env を作成 / 更新します。

- 設定検証
  - python -m kabusys.validate_config
  - .env と config/*.yaml（存在すれば）を検証します。PyYAML がない場合は YAML 検証をスキップします。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - 指標（稼働率、注文成功率、送信率、レイテンシ等）を計算して PASS/FAIL を出力します。

- AI モジュール（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）。
  - ニュース NLP:
    - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores テーブルを使用します。
  - レジーム判定:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - prices_daily / raw_news / market_regime テーブルを参照します。
  - どちらも API 失敗時はフェイルセーフ（スコア 0.0 など）で継続する設計です。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール用）
- KABUSYS_ENV: 実行環境（development | paper_trading | live。デフォルト: development）
  - paper_trading: 発注は MockBrokerClient、専用 DB を使用
  - live: 実際に発注を行う（注意して使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動消去するか（0/1、デフォルト 0）

運用上の注意
------------
- .env は機密情報を含むため Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）の確認や KILL_FLAG_CLEAR_ON_START を 0 にする等の安全確認を行ってください。
- Execution 起動時・監視時の停止はフラグファイル（data/kill.flag / data/stop_requested.flag）で制御されます。これらのファイル操作によりプロセスの起動／停止を外部から制御できます。
- OpenAI 利用箇所は API レート制限やコストに注意してください。失敗時はフェイルセーフで継続する実装ですが、運用方針に合わせて制御してください。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                   — 環境変数/.env 読み込みと Settings クラス
- config_setup.py             — 対話式 .env ウィザード
- validate_config.py          — 起動前設定検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — Monitoring ポーリング起動スクリプト

サブパッケージ:
- ai/
  - __init__.py
  - news_nlp.py               — ニュースセンチメント（OpenAI）
  - regime_detector.py        — 市場レジーム判定（OpenAI）
- monitoring/
  - monitoring_db.py          — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
  - system_monitor.py         — システム状態・データ鮮度監視
  - trade_monitor.py          — 注文滞留・約定異常監視
  - risk_monitor.py           — ドローダウン・ポジション上限監視
  - kill_switch.py            — kill.flag の管理と評価
  - monitoring_engine.py      — 各 Monitor を束ねる実行エンジン
  - alert_manager.py          — （アラート通知の管理 — 実装ファイルは同ディレクトリに存在）
- execution/                   — 発注エンジン周り（order_manager, broker_factory 等、主要ロジック）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py        — momentum/value/volatility ファクター計算（DuckDB）
  - feature_exploration.py    — 将来リターン / IC / 統計サマリー
  - __init__.py
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - process_priority.py       — プロセス優先度 / CPU affinity 設定（psutil ベース）

開発者向け情報
----------------
- settings: kabusys.config.Settings を通してアプリケーション全体で環境設定を参照します。
- DB マイグレーション: monitoring_db.init_monitoring_db() は起動時にテーブルと必要なカラムを冪等に作成します。
- テスト: 各モジュールは副作用を最小化する設計（純粋関数群や外部依存注入）を心がけています。AI 呼び出し等はテスト時にモック化可能です。
- ログレベルやプロセス優先度は utils.process_priority を使用してプラットフォーム差分を吸収します。

よくあるコマンド例
-----------------
- .env 作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config

- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- 実行エンジン起動（開発/ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 監視プロセス起動（ポーリング間隔 30 秒に設定）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ニュース NLP を直接実行（Python REPL / スクリプト内）:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026,4,11), api_key="sk-...")

最後に
------
この README はコードベースの主要な役割と運用方法をまとめたものです。実運用前に必ず python -m kabusys.validate_config で設定検証を行い、.env の値や DB パス、OpenAI キー等を適切に設定してください。必要に応じて各モジュールのドキュメント文字列（docstring）を参照してください。