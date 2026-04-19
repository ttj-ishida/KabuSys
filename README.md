# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、信号生成・ポートフォリオ構築・発注実行・監視・研究用ユーティリティを含む自動売買システムのコードベースです。各モジュールはできるだけ副作用を抑え、環境変数経由で設定可能となっています。

---

## 概要

- ポートフォリオ構築（候補選定・重み計算・株数決定）
- 発注実行エンジン（実口座 / ペーパートレード切替）
- 監視（システム状態、注文・約定ログ、リスク監視、Kill Switch）
- 研究用モジュール（ファクター計算、特徴量解析）
- AI連携（ニュースセンチメント、レジーム判定：OpenAI）
- CLI ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主要スクリプト:
- 実行エンジン起動: python -m kabusys.run_execution
- 監視ループ起動: python -m kabusys.run_monitoring
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config
- ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report

---

## 主な機能一覧

- Settings / .env の自動読み込み（.env, .env.local、OS 環境変数優先）
- .env 対話式ウィザード（config_setup）
- 設定検証 CLI（validate_config）: 必須環境変数や YAML ファイルの存在チェック
- ExecutionEngine:
  - 実際のブローカークライアントと Mock（paper_trading）を切替
  - 発注・注文管理・リスク管理・整合処理を統合
- Monitoring:
  - SystemMonitor: CPU/メモリ/ディスク/プロセス死活、データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文滞留・約定異常・ドローダウン・ポジション上限
  - KillSwitch / MonitoringEngine: ルールに基づく停止フラグ出力とアラート連携
- Research:
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）等の統計ツール
- AI:
  - news_nlp: OpenAI を用いたニュースセンチメント集計（銘柄単位）
  - regime_detector: ETF マクロ指標 + LLM による日次レジーム判定
- ツール:
  - ペーパートレード検証レポート生成（期間指定可）
- ロギング:
  - 統一的な logging セットアップ（コンソール stdout + 日次ローテートファイル）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 以下はこのコードベースで使用される主なパッケージ例です（requirements.txt が無い場合は手動で）。
     - duckdb
     - psutil
     - openai
     - PyYAML (validate_config の YAML 検証にのみ必要)
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env を手動で作成 (下記「環境変数」参照)

5. データディレクトリの準備
   - デフォルトでは data/ に DB ファイルやフラグファイルが作成されます。権限を確認してください。
   - ログは logs/ に出力されます（LOG_DIR 環境変数で変更可）。

6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱いたい場合は --strict を付与

---

## 重要な環境変数

（.env ファイルに設定してください。対話式ウィザードで生成可能）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

重要（省略可 / デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live) — デフォルト: development
  - paper_trading では MockBroker を使用し、専用の paper DB に記録します
- OPENAI_API_KEY — OpenAI を利用する場合に必要（AI 機能）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH — Execution 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1/0、デフォルト 0）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、default: 60）
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject、default: instant）

注意:
- run_monitoring は KABUSYS_ENV に関係なく本番の sqlite_path を使用します（監視は運用 DB を見る設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離します。

サンプル minimal .env:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL にする）: python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 標準起動:
    - python -m kabusys.run_execution
  - Paper Trading モードで起動する場合:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - このとき paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
  - 停止:
    - 実行中のエンジンは data/stop_requested.flag（stop_requested.flag）を存在確認して終了処理を行います。
    - Kill Switch（システムが危険と判定した場合）は data/kill.flag を書き込み、ExecutionEngine に停止シグナルを与えます。
  - PID ファイル:
    - 実行時に data/execution.pid に PID を書きます（Settings.pid_file_path で変更可）。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視プロセス自身を停止するには、プロジェクトルート/data/stop_requested.flag を作成します（run_monitoring が検出して終了）.

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です。環境変数または関数引数で指定します。
  - 関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 停止 / Kill Switch の挙動

- stop_requested.flag
  - run_monitoring / run_execution などの起動スクリプトはプロジェクトルート/data/stop_requested.flag の存在を監視しており、存在するとループを抜けて安全に終了します。
- kill.flag
  - KillSwitch（監視ロジック）は条件を満たすと data/kill.flag に理由を記したファイルを書きます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に自動でクリアされます（本番では 0 推奨）。
- PID ファイル
  - ExecutionEngine は data/execution.pid に PID を書きます。プロセス優先度の設定や stale PID 検出に使用されます。

---

## ディレクトリ構成

（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env 自動読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py (存在想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在想定)
  - execution/
    - execution_engine.py (存在想定)
    - broker_factory.py (存在想定)
    - order_manager.py (存在想定)
    - order_repository.py (存在想定)
    - reconciler.py (存在想定)
    - risk_manager.py (存在想定)
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

プロジェクト外に作成されるデータ/ログ:
- data/
  - monitoring.db (デフォルト SQLITE_PATH)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kabusys.duckdb (DUCKDB_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/
  - execution.log
  - monitoring.log
  - ...（アプリ名ごとに日次ローテート）

---

## 開発・運用の注意点

- 本番環境（KABUSYS_ENV=live）では設定ミスが致命的になりうるため validate_config による検証を必ず実行してください。
- OpenAI 連携機能を利用する際は rate limit やエラーへのリトライロジックが組み込まれていますが、APIキーとコスト管理に注意してください。
- monitoring は本番 DB を参照する設計のため、監視用 DB と実行用 DB の分離や権限管理を検討してください。
- .env は決してリポジトリにコミットしないでください（config_setup にも注記あり）。

---

## 参考コマンド集

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai PyYAML

- ウィザードで .env 作成
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視起動（ポーリング間隔を 30 秒に）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（ペーパートレード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- ペーパートレード検証レポート（2026-04-01〜2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

必要であれば README に含めるサンプル .env、運用手順（デプロイ / systemd / supervisor の設定例）、トラブルシューティング項目などを追記します。どの情報がより詳しく欲しいか教えてください。