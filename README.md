KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本コードベースは以下の主要コンポーネントを含みます。

- ExecutionEngine: 発注・注文管理・リスク管理・約定再構成などの実行系
- Monitoring: システム稼働監視、注文監視、リスク監視、Kill Switch（フラグファイル）等
- Research: DuckDB を用いたファクター計算・特徴量解析
- AI モジュール: ニュースの NLP スコアリング、マーケットレジーム判定（OpenAI API 利用）
- Portfolio: 候補選定・重み付け・ポジションサイズ計算・セクター制限
- CLI ユーティリティ: .env ウィザード、設定検証、レポート生成 など

特徴（抜粋）
-------------
- 環境分離: KABUSYS_ENV により development / paper_trading / live を切替可能。paper_trading は専用 SQLite DB を使用し本番 DB と分離。
- フェイルセーフ: API リトライ、部分失敗時の DB 保護、ログ・監視による自動停止（Kill Switch）等を装備。
- DuckDB を解析基盤として採用し、prices_daily / raw_financials 等からファクター計算を行う。
- ニュース文章を LLM（OpenAI）で評価して ai_scores に反映。レートリミットや JSON 検証を考慮。
- ロギングは統一された setup_logging を通してコンソール＋日次ローテートファイル出力を行う。

セットアップ
-----------

1. Python 環境
   - Python 3.9+ を推奨。仮想環境を作成してください。
     - 例: python -m venv .venv && source .venv/bin/activate

2. 依存パッケージのインストール
   - requirements.txt がある場合は pip install -r requirements.txt
   - 最低限必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML （設定検証で推奨）
   - 例: pip install duckdb psutil openai PyYAML

3. 環境変数（.env）
   - プロジェクトルートの .env を作成します。対話的に作るには:
     - python -m kabusys.config_setup
   - 主要な環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュール使用時に必要）
     - LOG_LEVEL（例: INFO）
     - LOG_DIR（ログ出力先、デフォルト: logs/）
     - KILL_FLAG_CLEAR_ON_START（本番での自動クリア防止推奨: 0）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、デフォルト 60）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant | partial | never | reject）
   - 設定を検証する:
     - python -m kabusys.validate_config
     - --strict をつけると警告も失敗扱いに

4. データディレクトリ
   - デフォルトで使用するディレクトリ: data/（SQLite、pid・フラグファイル等）
   - 初回実行時に自動生成されない場合は作成してください。

使い方（起動・主要コマンド）
---------------------------

- ExecutionEngine（発注実行）
  - デフォルト実行:
    - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にデータを残します。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - PID を data/execution.pid に書きます。
    - 停止は data/stop_requested.flag を作成することで行えます（Monitoring からも停止可能）。

- Monitoring（監視ループ）
  - デフォルト実行:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 挙動:
    - system / trade / risk の各モニタを定期実行し、必要に応じて kill.flag を書き込む（ExecutionEngine 側で検出し停止）。
    - monitoring は常に本番 sqlite_path（SQLITE_PATH）を使用して監視ログを保存します。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ系は関数呼び出しベース
  - ニューススコアリング（プログラム的に呼ぶ）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...") など
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime

停止・Kill Switch
-----------------
- 停止（外部からの優雅な停止）:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
- Kill Switch:
  - リスク（ドローダウン超過等）で自動的に data/kill.flag が書き込まれると ExecutionEngine は停止する設計です。
  - KillSwitch は既存の kill.flag があれば上書きせず冪等に振る舞います。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアします（本番では 0 推奨）。

ログ
----
- logging 設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...") を全スクリプトで使用。
- デフォルトは stdout と logs/<app_name>.log（日次ローテーション、30日保持）に出力。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理（Settings クラス）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - execution/                — 実行系（Engine, OrderManager, BrokerFactory, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py        — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文監視（stale / anomaly 検出）※実装ファイルあり
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - monitoring_engine.py    — 各 Monitor を束ねるループ
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — 通知管理（LINE 等）※実装ファイルあり
  - portfolio/
    - portfolio_builder.py    — 候補選定・スコア順
    - position_sizing.py      — 発注株数計算・aggregate cap
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン・IC・統計
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — マーケットレジーム判定（OpenAI + MA200）
  - data/                     — デフォルトデータ格納（SQLite, pid, flag など）
  - logs/                     — ログ出力ディレクトリ（デフォルト）

開発者向けメモ
---------------
- DuckDB 接続を渡してデータ参照・計算を行う設計です。prices_daily / raw_financials 等のテーブルが期待されます。
- LLM（OpenAI）を用いる部分は API キーの存在チェック、リトライ、レスポンスバリデーションを行いフェイルセーフ化しています。テスト時は内部の API 呼び出し関数をモックしてください。
- validate_config.py の YAML 検証は PyYAML がないとスキップされます（警告）。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

補足
----
- 実運用前に必ず python -m kabusys.validate_config で設定を検証してください。
- 本番環境（KABUSYS_ENV=live）の場合は KILL_FLAG_CLEAR_ON_START=0 を強く推奨します。
- paper_trading は本番 DB と完全分離されるよう設計されていますが、念のため設定ファイルとパスを確認してください。

---
この README はコードベースの主要点をまとめたものです。必要であれば起動例や .env のサンプル、依存関係の細かなバージョンを追加します。どの部分を詳しく書いてほしいか教えてください。