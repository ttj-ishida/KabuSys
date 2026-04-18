# KabuSys

日本株向け自動売買システムの実装スケルトン。ポートフォリオ構築、ポジションサイジング、監視・リスク管理、ペーパートレード検証、LLM ベースのニュースセンチメント/レジーム判定などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のコンポーネントを持つモジュール群から構成されています（抜粋）:

- execution: 発注エンジン（ExecutionEngine）・注文管理・リスク管理など
- monitoring: システム状態、注文ログ、リスク（ドローダウン・ポジション上限）監視、Kill Switch
- portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター制約
- research: ファクター計算（Momentum/Volatility/Value）や特徴量解析
- ai: ニュースの NLP スコアリング（OpenAI）・市場レジーム判定
- utils: ログ設定、プロセス優先度設定、環境設定読み込み等
- tools: レポート生成スクリプト等

設計方針として、DB（DuckDB / SQLite）を使ったデータ参照、外部 API 呼び出しは明示的に管理（OpenAI 等）、本番とペーパートレードのデータ分離を重視しています。

---

## 主な機能一覧

- 環境変数 / .env の対話式ウィザード（kabusys.config_setup）
- 起動前の設定検証 CLI（kabusys.validate_config）
- ExecutionEngine（本番 / ペーパートレード切替対応）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db に記録
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor）のポーリング
  - system_status, trade_logs, positions, risk_logs, dashboard を SQLite に永続化
  - Kill Switch による ExecutionEngine 停止指令（data/kill.flag）
- Portfolio 構築ユーティリティ（候補選定・重み付け・リスク調整・株数決定）
- Research モジュール（ファクター計算・将来リターン・IC 計算）
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメントスコアリング（ai_scores への書込）
  - regime_detector: ETF とマクロニュースを合成して日次レジーム判定（market_regime へ書込）
- ツール
  - paper_verification_report: ペーパートレード DB を用いた検証レポート生成（稼働率・成功率・レイテンシ等）

---

## 動作要件（主な依存パッケージ）

最低限の主要ライブラリ（環境によって追加が必要）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使用する場合)
- pyyaml（config ファイルの検証を行う場合に便利）

例（仮想環境内）:
pip install duckdb psutil openai pyyaml

注: requirements.txt は本リポジトリに含まれていないため、用途に応じて必要なパッケージを追加してください。

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - 例: git clone ... && cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

3. 依存ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
   - AI 機能を使わない場合は openai は不要

4. .env の作成
   - 対話式ウィザードを実行:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - その他: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LINE_* 等

5. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱いたい場合: python -m kabusys.validate_config --strict

6. データディレクトリ（デフォルト: data/）やログディレクトリ（デフォルト: logs/）の作成は多くのユーティリティが自動で行いますが、権限やマウント環境に注意してください。

---

## 使い方（主要スクリプト）

- Execution エンジンを起動
  - python -m kabusys.run_execution
  - 実行時の挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag が存在すると起動をスキップ
    - 停止は data/stop_requested.flag を作成することで行える（daemon スレッドにより検出して停止）
    - プロセス PID は data/execution.pid に書き込まれる

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - SystemMonitor.check_once() を定期実行し system_status 等のテーブルに永続化
    - ポーリング間隔は環境変数で上書き可能: MONITOR_POLL_INTERVAL（秒、デフォルト 60）
      - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - 監視は Settings から sqlite_path（デフォルト data/monitoring.db）を使用（Monitoring は環境に関わらず本番 sqlite_path を使います）
    - 停止はプロジェクトの data/stop_requested.flag ファイルを作成すると検知して終了

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- .env ウィザード
  - python -m kabusys.config_setup

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI / Research 関連はモジュール API（kabusys.ai.score_news, kabusys.ai.regime_detector.score_regime, kabusys.research.calc_momentum など）として利用可能。これらは DuckDB 接続や target_date を渡して使います。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード DB、デフォルト data/paper_trading.db)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
- OPENAI_API_KEY (AI 機能利用時)
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング秒数、デフォルト 60)

監視・Kill Switch 関連:
- KILL_FLAG_PATH (デフォルト data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1、1 にすると Execution 起動時に既存の kill.flag を自動クリア)

---

## ログ

- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（30 日保持）。
- setup_logging() によりコンソール( stdout ) とファイルの両方へ出力されます。
- app_name は起動スクリプト（例: "execution", "monitoring"）で設定されます。

---

## Kill Switch / Stop フラグについて

- kill.flag (Settings.kill_flag_path、デフォルト data/kill.flag)
  - KillSwitch が危険検出時（ドローダウン超過など）に作成するフラグ。ExecutionEngine に対する停止シグナル。
  - Execution 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると自動でクリアされる（危険。Production では 0 推奨）。

- stop_requested.flag (プロジェクト data/stop_requested.flag)
  - run_execution/run_monitoring の停止制御に使用（外部から停止をリクエストするためにこのファイルを作成する）。

---

## 開発・実行時の注意点

- DB マイグレーションは init_monitoring_db() により冪等に実行されます。既存スキーマへカラム追加がある場合、簡易マイグレーションも行われます（例: dashboard.peak_value, trade_logs.latency_ms）。
- AI モジュールを実行する際は OpenAI API キーを適切に設定してください。API 呼び出しに失敗した場合はフォールバック（スコア 0.0 など）して継続する設計ですが、本番利用時はレート制限等に注意してください。
- process_priority を起動時に "high" に設定します。権限が不足する場合は警告が出ますが処理は継続します。
- DuckDB は分析用の読み取り中心 DB、SQLite は監視・注文ログ等の永続化に使用する想定です。

---

## ディレクトリ構成（抜粋）

以下は本リポジトリの主要なファイル / ディレクトリの例（src/kabusys 配下を中心に抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings 管理
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリング起動スクリプト
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP / OpenAI 呼び出し
      - regime_detector.py     — レジーム判定
    - monitoring/
      - monitoring_db.py       — SQLite テーブル定義・永続化ラッパ
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - ... (trade_monitor, alert_manager 等)
    - execution/                — 発注エンジン、注文管理、ブローカーファクトリ等
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
      - __init__.py

- data/                       — デフォルトの DB/log/pid/flag が置かれる想定（実行時に自動生成）
  - monitoring.db (SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                       — ログファイル（logs/execution.log, logs/monitoring.log 等）

（上記はコードベースの一部を抜粋した構成です。実プロジェクトではさらに detail なパッケージ・モジュールが含まれる想定です。）

---

## よくある操作例

- モニタ起動（デフォルトポーリング 60 秒）:
  - python -m kabusys.run_monitoring

- モニタを 30 秒間隔で動かす:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（ペーパーで起動）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- .env を対話式で作成:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

---

## サポート / 拡張ポイント（今後の参考）

- 発注の実行層 (ExecutionEngine) とモニタリングの連携強化（外部アラート連携・Webhook）
- 銘柄別の lot_size を stocks マスタへ移行して position_sizing を拡張
- DuckDB のテーブルスキーマ管理・スキーマ移行スクリプト整備
- テストカバレッジ拡充（AI 呼び出しはモック化してユニットテストを用意）
- 運用向け: systemd / supervisor などでプロセス管理、ログ・メトリクスの集約

---

README の内容やコマンドで不明点があれば、どの部分を詳しく書けば良いか教えてください。運用手順や具体的な .env のサンプルも用意できます。