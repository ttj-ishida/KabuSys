# KabuSys

日本株自動売買システムのコアライブラリ / 実行スクリプト群。  
このリポジトリは取引エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター研究、AI を用いたニュース分析など、実運用を想定したモジュール群を含みます。

---

## 概要

KabuSys は以下のような機能を提供するモジュール群と CLI スクリプトを備えたプロジェクトです。

- 発注エンジン（ExecutionEngine）とそれを支える注文管理 / リスク管理 / リコンサイル
- 監視サブシステム（System / Trade / Risk Monitor）と Kill Switch（フラグファイルで Execution を停止）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・セクター制限）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI モジュール（ニュースセンチメントスコアリング、レジーム判定） — OpenAI API を利用
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- 運用用ツール（Paper Trading 検証レポート生成など）

重要設計方針（抜粋）:
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と完全分離（`data/paper_trading.db` を使用）。
- 監視（monitoring）は環境にかかわらず本番の sqlite_path を参照（run_monitoring の挙動）。
- LLM 呼び出しなど外部 API 失敗時はフェイルセーフ（例: スコア 0.0 / スキップ）で継続する設計。

---

## 主な機能一覧

- 実行（run_execution.py）
  - 本番 / ペーパートレードの切り替え（`KABUSYS_ENV`）
  - BrokerClientFactory によるブローカー抽象化
  - リスク管理（ポジション上限・ドローダウンなど）
  - PID / 停止フラグ連携（`data/execution.pid`, `data/stop_requested.flag`）

- 監視（run_monitoring.py / monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス監視、データ鮮度チェック
  - TradeMonitor: 発注ログや滞留注文の監視（trade_logs）
  - RiskMonitor: ドローダウンやポジション上限の監視
  - KillSwitch: 指定条件で `data/kill.flag` を書き込んで Execution を停止
  - AlertManager（通知管理、LINE などに接続可能）

- ポートフォリオ（portfolio パッケージ）
  - 候補選定、等金額／スコア加重、スコアが 0 のフォールバック
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（lot 単位丸め、aggregate cap スケーリング）

- 研究（research パッケージ）
  - モメンタム / ボラティリティ / バリューなどファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計

- AI（ai パッケージ）
  - news_nlp: raw_news を OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM センチメントを合成してレジーム判定

- ツール
  - .env ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート（python -m kabusys.tools.paper_verification_report）

---

## 要件

- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- （任意）PyYAML（設定検証で YAML のパース検証を行う場合）

（requirements.txt はプロジェクトに応じて用意してください）

---

## セットアップ手順

1. レポジトリをクローン、作業ディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - （requirements.txt がない場合は手動で duckdb, psutil, openai 等をインストール）

4. 初期設定（.env の作成）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - 生成後、必要に応じて .env を編集する

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ / ログディレクトリの準備
   - デフォルト DB やログは以下:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
     - ログ: logs/<app_name>.log
   - 多くは初回起動で自動作成されますが、パーミッション等に注意してください。

---

## 環境変数（主要）

一部抜粋。詳細は `kabusys.config.Settings` や config_setup の項目を参照してください。

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)
- OPENAI_API_KEY (AI 機能使用時)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒, デフォルト 60)
- PAPER_FILL_MODE (paper_trading の MockBroker 挙動; instant | partial | never | reject)

Kill / Stop フラグ・PID ファイル（デフォルト位置）
- data/execution.pid — ExecutionEngine の PID
- data/stop_requested.flag — run_execution / run_monitoring が監視する外部停止フラグ
- data/kill.flag — KillSwitch が書き込む停止フラグ（Execution 停止指示）

---

## 使い方（起動 / ツール）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - Paper Trading（.env で KABUSYS_ENV=paper_trading を設定）では MockBroker と paper DB を使用

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- .env ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit code 1

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ライブラリ呼び出し例）
  - ニューススコア付与: kabusys.ai.score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

注意: AI 機能は OpenAI API キー（OPENAI_API_KEY 環境変数または api_key 引数）が必要です。

---

## 運用メモ / 停止フロー

- run_execution / run_monitoring はプロジェクトルートの `data/stop_requested.flag` を監視し、存在するとグレースフルに停止します。
- KillSwitch は `data/kill.flag` を作成して ExecutionEngine に停止を伝えます（Execution 起動時に `KILL_FLAG_CLEAR_ON_START` が 1 のと危険）。
- run_monitoring は監視用 DB として常に `Settings.sqlite_path`（本番パス）を使用します（環境に依らず）。
- run_execution は `KABUSYS_ENV=paper_trading` の場合、専用の paper DB（`PAPER_TRADING_SQLITE_PATH`）を使用し本番 DB とは分離します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings
- config_setup.py — .env ウィザード CLI
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring ポーリング起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py — ニュースの LLM ベースセンチメント付与
  - regime_detector.py — マーケットレジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py (実装ファイルあり)
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (通知管理)
- execution/
  - broker_factory.py
  - execution_engine.py
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py — 共通ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity
- data/ （実行時に生成される想定）
  - *.db, *.flag, *.pid
- logs/（ログファイル）

---

## 開発・デバッグのヒント

- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name="...")` を各起動スクリプトで使用しています。ログはデフォルトで `logs/<app_name>.log` に日次ローテーションで保存されます。
- 外部 API 呼び出し（OpenAI など）は明示的にリトライやフェイルセーフ実装が入っています。テスト時は該当関数（例: _call_openai_api）をモックすることを推奨します。
- DuckDB を使った研究系関数は「prices_daily」「raw_financials」「raw_news」などのテーブルを前提にしています。テーブルスキーマはコードコメントや SQL から確認できます。

---

## ライセンス / 貢献

（ここにライセンス情報・貢献方法を追記してください）

---

README はここまでです。必要に応じて以下を提供できます：
- requirements.txt のサンプル
- .env.example のサンプル
- 起動用 systemd / supervisor ユニット例

必要な場合はどれを追加するか教えてください。