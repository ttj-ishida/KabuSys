# KabuSys

日本株自動売買システム KabuSys の簡易ドキュメント（README）。  
このリポジトリは取引エンジン、監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などの機能を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買フレームワークです。主な目的は以下です。

- シグナル生成 → 発注（ExecutionEngine）
- 発注・約定ログ管理・リスク制御
- システム稼働監視（監視エンジン / Kill Switch）
- ポートフォリオ構築（候補選定、重み算出、株数決定）
- DuckDB を使ったリサーチ / ファクター計算
- OpenAI を利用したニュースセンチメント評価および市場レジーム判定
- ペーパートレードモードでの完全分離（専用 SQLite）

設計上のポイント:
- .env（環境変数）から設定を読み込む仕組みを持つ
- Paper trading と Live を明確に分離
- ログはコンソール + 日次ローテートファイル出力（logs/）
- フェイルセーフ（API失敗やデータ欠損時は安全側にフォールバック）

---

## 機能一覧

- Execution
  - 実際のブローカークライアントまたは MockBroker（paper_trading）を使った注文実行
  - RiskManager、OrderManager、Reconciler による堅牢な発注制御
  - PID ファイル / stop フラグによる起動・停止制御

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働チェック、データ鮮度チェック
  - TradeMonitor: 発注ログ・滞留注文・約定異常などの監視（該当ファイル参照）
  - RiskMonitor: ドローダウン・ポジション上限の監視、KillSwitch トリガー
  - MonitoringEngine: 各 Monitor を束ねるポーリングループ

- Portfolio
  - 候補選定（スコア順）、等配分/スコア配分、リスクベースの株数算出
  - セクターキャップ適用、レジーム乗数算出

- Research
  - DuckDB 接続を利用したファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）で評価し銘柄別スコアを ai_scores テーブルへ保存
  - regime_detector: ETF の MA とマクロニュースの LLM センチメントを合成して日次レジーム判定

- ユーティリティ
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 依存関係をインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 明示的に必要なライブラリ例:
     - pip install duckdb psutil openai PyYAML
   （実際の requirements はプロジェクト側で用意してください）

4. 環境変数の準備（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - よく使う任意 / 上書き可能変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, default: data/paper_trading.db)
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR)
     - OPENAI_API_KEY（AI 機能利用時）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動消去するか: 0/1）

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

注意:
- .env は決して Git にコミットしないでください（config_setup でその旨の注意書きがあります）。
- データフォルダ（data/）やログフォルダ（logs/）は起動時に自動作成される場合がありますが、権限等に注意してください。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - PID ファイル (data/execution.pid) を使ってプロセス管理
    - data/stop_requested.flag が存在すると起動しない / 既存停止フラグがあると即停止

- Monitoring を起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可（デフォルト 60）
  - 監視は常に本番 sqlite_path（KABUSYS_ENV に関わらず）を参照して監視ログを保存

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - PAPER_TRADING_SQLITE_PATH 環境変数で DB を指定可能

- Kill Switch（手動）
  - data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る仕組み（KillSwitch が書き込む）
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨

ログ:
- ログはデフォルトで logs/<app_name>.log に日次ローテートされます（コンソールにも出力）。
- app_name は run_execution なら "execution"、run_monitoring なら "monitoring"。

---

## 重要な環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要（任意 / デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — default: development
- DUCKDB_PATH — default: data/kabusys.duckdb
- SQLITE_PATH — default: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
- LOG_LEVEL — default: INFO
- OPENAI_API_KEY — AI 機能を使う場合に必須
- MONITOR_POLL_INTERVAL — 監視ポーリング秒（run_monitoring 用, default: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み / Settings クラス（アプリ設定）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
    - trade_monitor.py       — 発注ログ監視（滞留注文等）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みユーティリティ
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - alert_manager.py       — （アラート送信ロジック、LINE 等の実装想定）
  - execution/
    - execution_engine.py
    - broker_factory.py
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
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定

その他:
- data/（ランタイムで生成されることが多い）
  - monitoring.db（SQLite、デフォルト）
  - paper_trading.db（paper トレード用）
  - kill.flag / stop_requested.flag / execution.pid 等フラグ・PID ファイル
- logs/（ログファイル）

---

## 開発上の注意点 / 運用メモ

- Paper trading モード（KABUSYS_ENV=paper_trading）は本番 DB と分離され、MockBroker と専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます。実際の資金が動くことはありませんが実ロジックの検証に有用です。
- OpenAI を利用するモジュール（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必要です。API の呼び出しはリトライやバックオフ実装、レスポンスのバリデーションを行いフェイルセーフを意識していますが、料金・レート制限には注意してください。
- 監視ループ / エンジンは stop flag（data/stop_requested.flag）や kill.flag によって制御されます。起動前に存在する場合は起動しないような安全措置があります。
- ログ出力先ディレクトリ作成に失敗した場合、ファイルハンドラは無効化されコンソール出力のみになります。権限の確認をしてください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行われます。自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

README は以上です。各モジュールの詳細な使い方や開発ガイドは、各ファイル内の docstring / コメントに記載されています。必要であれば、特定モジュールの詳しい使い方や設定例（.env の具体例、docker-compose 例など）を追加で作成します。必要な項目を教えてください。