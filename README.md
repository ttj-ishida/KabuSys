KabuSys — 日本株自動売買システム
==============================

本リポジトリは日本株向けの自動売買／リサーチ／監視フレームワークです。
モジュール設計は小さな責務に分離されており、以下の主要機能を提供します。

主な特徴
--------
- ExecutionEngine：発注・注文管理・リスク管理（paper_trading モードで Mock ブローカーを利用可）
- Monitoring：システム状態・注文・リスクを定期観測し、Kill Switch（停止フラグ）や通知を発動
- Portfolio construction：銘柄選定、重み付け、ポジションサイズ算出（等配分・スコア加重・リスクベース）
- Research：DuckDB を用いたファクター計算（Momentum/Value/Volatility 等）および特徴量解析ユーティリティ
- AI 支援モジュール：OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）・市場レジーム判定
- ツール群：ペーパートレード検証レポート生成スクリプトなど
- 設定管理：.env ウィザード（config_setup）、起動前チェック（validate_config）
- ログ設定ユーティリティ・プロセス優先度制御など運用向けユーティリティ

セットアップ（開発環境向け）
---------------------------
1. リポジトリをクローンして working directory をプロジェクトルートにする（pyproject.toml / .git が想定）。
2. Python 仮想環境を作成・有効化。
   - 例（Unix/macOS）:
     python -m venv .venv
     source .venv/bin/activate
3. 依存パッケージをインストール。
   - 例:
     pip install duckdb psutil openai
   - 追加（任意）:
     pip install pyyaml
   - 注: sqlite3 は標準ライブラリに含まれます。
4. .env を作成（推奨: ウィザード使用）。
   - 対話的に作る:
     python -m kabusys.config_setup
   - 必須環境変数（最低限設定するもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要オプション:
     - KABUSYS_ENV (development | paper_trading | live) — 実行モード
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL, LOG_DIR, KILL_FLAG_CLEAR_ON_START など
5. 設定検証（起動前チェック）:
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

主な実行方法
------------
- ExecutionEngine（エンジン起動）:
  - 実行:
    python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録されます（本番 DB とは分離）。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid を作成します。
    - 停止指示は data/stop_requested.flag を作ることで行えます（monitoring からのシグナル等）。

- Monitoring（監視プロセス）:
  - 実行:
    python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60。
  - 動作:
    - sqlite（monitoring DB）と DuckDB に接続し各種モニタを定期実行。
    - stop フラグ（data/stop_requested.flag）があるとループを終了します。

- 設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 関連（ライブラリ関数として利用）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols を集約し OpenAI でスコアリングして ai_scores テーブルへ書込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA とマクロニュースを組み合わせて market_regime を判定・書込む
  - いずれも OPENAI_API_KEY を環境変数または引数で指定する必要があります。

運用 / 運転上の注意
------------------
- Kill Switch:
  - RiskMonitor の評価により KillSwitch が data/kill.flag を作成すると ExecutionEngine に停止シグナルを送れます。
  - KILL_FLAG_CLEAR_ON_START が 1 の場合、起動時に kill.flag を自動でクリアします（本番では 0 推奨）。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます。psutil の権限により失敗する場合は警告でスキップされます。
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を使い、コンソール (stdout) と logs/<app>.log（日次ローテーション）へ出力します。
  - 環境変数 LOG_LEVEL / LOG_DIR を利用できます。
- DB:
  - DuckDB（分析用）と SQLite（監視・注文履歴）を使います。デフォルト:
    - DUCKDB_PATH: data/kabusys.duckdb
    - SQLITE_PATH: data/monitoring.db
    - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード）
- モジュール設計はフェイルセーフを多用しており、API 失敗時はスキップ/フォールバックして継続する設計です。

ディレクトリ構成（主要ファイル）
-------------------------------
src/kabusys/
- __init__.py
- config.py               — 環境変数/.env の読み込み・Settings 定義
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 起動前の設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

subpackages:
- ai/
  - news_nlp.py           — ニュースセンチメント（OpenAI 呼び出し・DB 書込）
  - regime_detector.py    — 市場レジーム判定（MA + LLM）
- monitoring/
  - monitoring_db.py      — SQLite テーブル定義・簡易永続化 API
  - system_monitor.py     — システム状態・データ鮮度チェック
  - risk_monitor.py       — ドローダウン / ポジション上限監視
  - kill_switch.py        — kill.flag 制御
  - monitoring_engine.py  — 各 Monitor を束ねる実行エンジン
  - alert_manager.py      — （通知管理。コード参照）
  - trade_monitor.py      — （取引監視。コード参照）
- portfolio/
  - portfolio_builder.py  — 銘柄候補選定・重み計算
  - position_sizing.py    — 株数決定・集約キャップ・単元丸め
  - risk_adjustment.py    — セクターキャップ・レジーム乗数
- research/
  - factor_research.py    — Momentum/Value/Volatility ファクター計算（DuckDB 使用）
  - feature_exploration.py— 将来リターン、IC、統計サマリ
- utils/
  - logging_setup.py      — ログ初期化ユーティリティ
  - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/ (上記)
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート

デフォルトのファイルパス（実行時に参照）
-------------------------------------
- data/kabusys.duckdb          — DuckDB（分析）
- data/monitoring.db           — SQLite（監視 DB）
- data/paper_trading.db        — SQLite（ペーパートレード用）
- data/execution.pid           — ExecutionEngine の PID ファイル
- data/stop_requested.flag     — stop フラグ（存在で監視/実行を終了）
- data/kill.flag               — Kill Switch（Execution 停止シグナル）
- logs/<app>.log               — 日次ローテートされるログファイル（LOG_DIR で変更可）

開発者向けメモ
---------------
- DuckDB クエリは prices_daily / raw_financials / raw_news 等のテーブル構造を前提としています（テーブルは外部取り込みパイプラインで用意する想定）。
- unit テストや CI では環境変数自動ロードを無効化できます:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- AI 呼び出し部分（news_nlp/regime_detector）は OpenAI SDK に依存します。テスト時は内部の _call_openai_api をモックしてください。
- 設定や DB パスの存在チェックは validate_config で簡易検出できます。起動前に必ず実行することを推奨します。

ライセンス・貢献
----------------
- 本 README はコードベースに基づく概要ドキュメントです。ライセンスや貢献ルールはリポジトリのトップレベル（LICENSE / CONTRIBUTING.md 等）を参照してください。

補足
----
- 本 README はリポジトリ内の主要スクリプト・モジュールからの情報に基づく要約です。詳細な実装・追加オプションは各モジュール（例: ai/news_nlp.py, monitoring/*.py, portfolio/*.py）内の docstring を参照してください。

必要であれば、README に使い方の具体的なコマンド例や .env.example のサンプル、よくあるトラブルシュート（例: OpenAI API エラー対策、psutil の権限問題）を追記します。どの情報を優先して追加しますか？