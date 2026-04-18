# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買基盤（KabuSys）の一部モジュールを含みます。
監視（Monitoring）、注文実行エンジン（Execution）、ポートフォリオ構築、ファクター計算、
LLM を使ったニュースセンチメント評価などの機能を備えています。

以下はこのコードベースに対する README.md（日本語）です。

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群です。

- 市場データ（DuckDB）を用いたファクター計算・リサーチ
- 発注周り（ExecutionEngine） — 実口座 / ペーパートレードの分離
- 監視（Monitoring） — システム状態・注文ログ・リスク監視、Kill Switch
- LLM（OpenAI）を用いたニュースセンチメント評価とレジーム判定
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 各種ユーティリティ（ロギング設定、プロセス優先度設定等）

設計方針の一部：
- 設定は .env（または環境変数）で管理。`config_setup` による対話ウィザードを提供。
- Paper trading と Live は DB や動作を明確に分離。
- LLM 呼び出しはフェイルセーフ（API失敗時はフォールバック）で実装。
- DuckDB を解析用 DB、SQLite を監視ログ / 発注ログ用 DB に使用。

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動（KABUSYS_ENV による paper/live 切替）
  - run_monitoring.py — SystemMonitor のポーリングループを起動
- 設定管理
  - config.py — 環境変数 / .env 自動ロードと Settings クラス
  - config_setup.py — 対話式 .env 生成ウィザード
  - validate_config.py — .env / config/*.yaml の事前検証 CLI
- 監視
  - monitoring/monitoring_db.py — SQLite による永続化層
  - monitoring/system_monitor.py — CPU/メモリ/ディスク/データ鮮度の監視
  - monitoring/trade_monitor.py（注文監視: コードベースに含まれる想定）
  - monitoring/risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring/kill_switch.py — 条件に応じた stop フラグ書き込み
  - monitoring/monitoring_engine.py — 各モニタの束ねとアラート通知
- Execution（発注）
  - execution/* — BrokerClientFactory、ExecutionEngine、OrderManager 等（発注フロー）
  - ペーパートレード用 MockBroker のサポート（KABUSYS_ENV=paper_trading）
- 研究・分析
  - research/factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - research/feature_exploration.py — 将来リターン・IC 等の分析ユーティリティ
- AI（LLM 統合）
  - ai/news_nlp.py — raw_news をまとめて OpenAI で銘柄別センチメントを算出し ai_scores に書込
  - ai/regime_detector.py — ma200 とマクロニュースの LLM スコアを合成し市場レジーム判定
- ポートフォリオ構築
  - portfolio/* — 候補選定、重み付け、リスク調整、株数計算（単体関数群）
- ユーティリティ
  - utils/logging_setup.py — 一貫したログ設定（コンソール + 日次ローテーションファイル）
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

## 要件（代表例）

実行には以下のパッケージが想定されます（requirements.txt は本リポジトリに含まれていないため、環境に応じてインストールしてください）:

- Python 3.9+
- duckdb
- psutil
- openai (OpenAI SDK)
- PyYAML（validate_config の YAML 検査を有効にする場合）
- （必要に応じて）その他の依存は実行時にインポートエラーで判明します

例:
pip install duckdb psutil openai pyyaml

## セットアップ手順

1. リポジトリをクローンし作業ディレクトリに移動
   - git clone ... && cd repo

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - pip install -r requirements.txt  （ない場合は依存を個別にインストール）

4. .env の作成
   - 対話ウィザード: python -m kabusys.config_setup
   - もしくは .env.example（未提供なら README の下欄参照）を参考に手動作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - strict モード: python -m kabusys.validate_config --strict

6. データディレクトリの準備（必要に応じて）
   - デフォルト DB / PID / flag 等は `data/` 下を想定
   - logs ディレクトリは logging_setup が自動作成

## 主要な環境変数（重要なもの）

（設定は .env に書くか環境変数で設定します。括弧はデフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用して DB を分離
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- LOG_LEVEL (INFO)
- LOG_DIR
- OPENAI_API_KEY — LLM 機能を使用する場合に必要
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

注意:
- Paper trading は本番 DB と完全に分離され、発注は MockBroker により記録されます（PAPER_TRADING_SQLITE_PATH）。
- kill.flag（デフォルト data/kill.flag）を書き込むと ExecutionEngine に停止シグナルを送ります。
- stop フラグ: data/stop_requested.flag を作成すると run_* スクリプトのループを正常終了できます。

## 使い方（実行例）

- ExecutionEngine を起動（デフォルト: Settings.env に従う）
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading を設定すると MockBroker を使用して data/paper_trading.db に記録

- Monitoring を起動（システム監視ポーリング）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート（SQLite の paper_trading DB を解析）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニュース評価 / レジーム判定）はライブラリ関数として利用します（DuckDB 接続が必要）。
  - 例（簡易）:
    - from openai import OpenAI
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, datetime.date(2026, 4, 10), api_key="sk-...")

  ※ 実行前に OPENAI_API_KEY を設定するか api_key を引数で渡してください。API 呼び出しは失敗時にフォールバック（スコア 0 など）する実装です。

## 停止 / Kill Switch の仕組み

- KillSwitch（monitoring/kill_switch.py）は RiskMonitor 等の結果から条件判定し、理由を含む `data/kill.flag` を書き込みます。
- ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START` の設定により動作を決めます。監視が `kill.flag` を見つけると発注エンジンの停止を促します。
- また run_* スクリプトは `data/stop_requested.flag` の存在を見てポーリングループを安全に終了します。

## ロギング

- 共通ロギングは kabusys.utils.logging_setup.setup_logging() で設定されます。
- デフォルトは stdout（コンソール）と `logs/<app_name>.log`（日次ローテーション、30日保持）。
- LOG_DIR と LOG_LEVEL は環境変数で上書き可能。

## ディレクトリ構成

（src/kabusys 以下の主要ファイル・ディレクトリ）

- src/
  - kabusys/
    - __init__.py
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - config.py                       — Settings / .env 自動ロード
    - config_setup.py                 — .env 対話ウィザード
    - validate_config.py              — 設定検証 CLI
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading レポート生成ツール
    - ai/
      - __init__.py
      - news_nlp.py                   — ニュース NLP（OpenAI）処理
      - regime_detector.py            — レジーム判定（MA200 + LLM）
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層（schema + API）
      - system_monitor.py             — システム状態監視
      - trade_monitor.py              — 注文監視（ログ解析・異常検出）※存在想定
      - risk_monitor.py               — ドローダウン/ポジション上限監視
      - kill_switch.py                — kill.flag 管理
      - monitoring_engine.py          — 各 Monitor を束ねるエンジン
      - alert_manager.py              — アラート送信（LINE 等）※存在想定
    - execution/
      - broker_factory.py             — Broker クライアント生成（実/モック）
      - execution_engine.py           — ExecutionEngine 本体（run_session 等）
      - order_manager.py              — Order 管理
      - order_repository.py           — DB 永続化（orders）
      - reconciler.py                 — 注文とポジションの整合処理
      - risk_manager.py               — 発注前のリスクチェック
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

## 開発メモ / 補足

- config._find_project_root() により .env 自動読み込みはリポジトリルート（.git または pyproject.toml のある場所）を基準に行われます。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- DB スキーマ変更時の簡易マイグレーションを monitoring_db.init_monitoring_db() 内で実施（列追加等の互換処理あり）。
- LLM 呼び出し部分は外部 API の失敗を考慮しており、リトライやフォールバックロジックが入っています。
- 実運用での注意点：
  - 本番実行（KABUSYS_ENV=live）時は .env に機密を含めないようにし、LINE 等の通知設定を必ず確認してください（validate_config の警告参照）。
  - kill.flag や stop_requested.flag を誤って残すと起動しない挙動になるため、運用手順を明確にしてください。

---

この README はコードベースの主要機能・使い方の概要を示すものです。各モジュール（特に ExecutionEngine、BrokerClient、AlertManager 等）は実装詳細に依存するため、これらを変更／拡張する際は該当ソースを参照してください。必要ならば各コンポーネント用のより詳細なドキュメント（API 使用例・設定例・運用手順）を別途作成できます。