README — KabuSys（日本語）
======================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。本プロジェクトは以下の主要機能を持ち、ライブラリとしてもスクリプトとしても利用できます。

- 発注・実行エンジン（ExecutionEngine）
- 監視（System / Trade / Risk）および Kill Switch
- Paper Trading 用モックブローカーと検証レポート
- ファクター計算・特徴量探索（Research）
- ニュース NLP（OpenAI を用いたセンチメント）とレジーム判定
- ポートフォリオ構築（候補選定・配分・株数決定・セクター制限）
- 環境設定ウィザード・設定検証ツール

主な機能一覧
-------------
- 実行スクリプト
  - run_execution: ExecutionEngine を起動。KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 専用 SQLite DB に記録（本番 DB と分離）。
  - run_monitoring: SystemMonitor をポーリングして system_status などを記録。MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）。

- 設定管理
  - config_setup: .env を対話式に生成/更新するウィザード。
  - validate_config: .env や config/*.yaml を起動前に検証する CLI。

- 監視関連
  - MonitoringEngine: System/Trade/Risk モニタをまとめてポーリングし、KillSwitch や Alert を発動。
  - KillSwitch: data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送信。
  - MonitoringDB: SQLite に監視ログ（system_status / trade_logs / positions / risk_logs / dashboard）を永続化。

- Paper Trading 検証
  - tools/paper_verification_report: ペーパートレード DB から稼働率・成功率・レイテンシ等を集計してレポートを出力。

- 研究（Research）
  - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 接続で prices_daily / raw_financials を参照）。
  - feature_exploration: 将来リターン・IC 計算・統計サマリー等。

- AI（OpenAI）
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄ごとのセンチメント（ai_scores）を生成。
  - regime_detector: ETF（1321）の MA200 乖離と LLM によるマクロセンチメントを合成して市場レジームを判定し、market_regime テーブルに保存。

セットアップ手順
----------------
前提:
- Python 3.10+（コードは typing と新しい構文を利用）
- duckdb, psutil, openai 等の外部ライブラリ（requirements.txt がある場合はそれを使用）

1. リポジトリをクローン
   - git clone ... / プロジェクトルートに移動

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール
   - pip install -r requirements.txt
   - 必須ライブラリ（主なもの）: duckdb, psutil, openai, (PyYAML は検証のために任意)

4. .env の作成
   - 推奨: python -m kabusys.config_setup
     - 対話式で .env を生成します（.env は Git にコミットしないでください）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要: KABUSYS_ENV は development / paper_trading / live のいずれか

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

使い方（主要コマンド）
--------------------

- 実行エンジン（Execution）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db）を用いる
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中は data/execution.pid に PID を書きます

- 監視（Monitoring）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60）
    - 停止はプロジェクトルート/data/stop_requested.flag を作成することで可能
    - 監視は環境にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視データを記録します

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / レジーム判定（プログラム呼び出し）
  - OpenAI API キーは環境変数 OPENAI_API_KEY に設定
  - news_nlp:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=None)
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

主要環境変数（抜粋）
-------------------
- KABUSYS_ENV: execution モード（development | paper_trading | live） デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL） デフォルト: INFO
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒） デフォルト: 60
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject） デフォルト: instant
- KILL_FLAG_CLEAR_ON_START: 本番での Kill Flag 自動クリア（0/1） デフォルト: 0 推奨: 0

ファイル / ディレクトリ構成
--------------------------
（主要ファイルのみ抜粋、パッケージは src/kabusys 配下）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数・Settings 管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor 起動スクリプト

  - utils/
    - logging_setup.py           — ロギング設定ユーティリティ
    - process_priority.py        — プロセス優先度 / CPU affinity 設定

  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py          — システム状態 / データ鮮度監視
    - trade_monitor.py           — （発注 / トレード関連監視: ファイルにある想定）
    - risk_monitor.py            — ドローダウン・ポジション上限検査
    - kill_switch.py             — data/kill.flag を書き込む Kill Switch
    - monitoring_engine.py       — 各モニタを束ねる

  - execution/
    - execution_engine.py        — ExecutionEngine（発注セッション制御）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - portfolio/
    - portfolio_builder.py       — 候補選定・重み計算
    - position_sizing.py         — 株数決定・スケーリング・単元丸め
    - risk_adjustment.py         — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py         — Momentum/Volatility/Value 算出
    - feature_exploration.py     — 将来リターン・IC・統計

  - ai/
    - news_nlp.py                — ニュース NLP / OpenAI で銘柄スコア作成
    - regime_detector.py         — マクロセンチメント + MA200 で市場レジーム判定

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

デフォルトのパス / フラグファイル
--------------------------------
- ログ: logs/<app_name>.log（TimedRotatingFileHandler、日次ローテーション）
- 監視 DB（SQLite）: data/monitoring.db（Settings.sqlite_path）
- DuckDB: data/kabusys.duckdb
- Paper Trading DB: data/paper_trading.db
- Kill Flag: data/kill.flag（KillSwitch が作成）
- Stop Flag: data/stop_requested.flag（run_* スクリプトが監視して終了）
- Execution PID: data/execution.pid

注意・トラブルシューティング
----------------------------
- .env は常にローカルに保存し、Git にコミットしないでください（config_setup にも注意書きあり）。
- validate_config は PyYAML がない場合に YAML 内容の検証をスキップします（警告）。
- OpenAI 関連機能（news_nlp / regime_detector）は OPENAI_API_KEY が必須です。API レート制限や 5xx にはリトライを実装していますが、外部 API の障害は影響します。
- run_execution は Paper Trading 時に MockBroker を使い、本番 DB と明確に分離します。KABUSYS_ENV を誤って live にしないよう注意してください。
- run_monitoring は監視ログ保存に本番 sqlite_path を常に使用します（環境に依存しない）。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（warning が出ます）。
- process_priority や CPU affinity の設定は psutil の権限に依存します。権限不足の場合は警告が出ますが動作は継続します。

開発者向けメモ
---------------
- DuckDB 接続を取る関数群（research / ai）は副作用を避け、与えられた接続で読み取り／書き込みを行います。テスト時は DuckDB の in-memory 接続を使うと良いです。
- AI 呼び出し部分はテスト用に _call_openai_api をパッチ可能な形で実装してあります（unittest.mock.patch を利用可）。
- monitoring_db.init_monitoring_db は冪等であり、起動時にスキーマ自動マイグレーション（列追加）を行います。

貢献・ライセンス
----------------
README 内に記載なし（リポジトリのトップに LICENSE があればそちらを参照してください）。

以上。必要であればインストール手順の具体的な requirements.txt や systemd / supervisor 用の起動例、デバッグ方法（ロギング設定のオーバーライド方法）についても追記できます。どの情報が欲しいか教えてください。