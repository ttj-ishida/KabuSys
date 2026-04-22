# KabuSys

日本株向けの自動売買システム（ライブラリ / スクリプト群）のリポジトリ。  
モジュール化された Execution（発注系）・Monitoring（監視系）・Research（因子計算）・Portfolio（銘柄選定/配分）・AI（ニュース NLP / レジーム判定）等を含みます。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python 製の自動売買基盤です。

- 発注処理（ExecutionEngine）と監視（MonitoringEngine）を分離して安定運用を支援
- Paper Trading と Live（本番）を明確に分離（paper_trading 用の専用 SQLite DB を使用）
- DuckDB を用いた時系列データ / ファクター計算（Research）
- ニュースを LLM（OpenAI）でスコアリングして投資判断へ活用（AI モジュール）
- Kill Switch（安全停止）や各種リスク監視・アラート機構を備える

設計方針として「テスト可能性」「フェイルセーフ」「ルックアヘッドバイアスの排除」を重視しています。

---

## 機能一覧

主な機能は以下の通りです。

- Execution
  - ExecutionEngine（発注エンジン）
  - BrokerClientFactory（実ブローカー / モックの切替）
  - RiskManager / OrderManager / Reconciler / OrderRepository
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、専用 DB（data/paper_trading.db）へ記録
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック）
  - TradeMonitor（発注ログチェック・滞留注文検知・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（閾値到達で data/kill.flag を書き込み Execution を停止）
  - MonitoringEngine（上記を束ねるポーリングループ）
  - 監視ログ永続化（SQLite）: system_status / trade_logs / risk_logs / positions / dashboard
- Portfolio（純粋関数）
  - 銘柄選定（スコア順ソート）
  - 重み付け（等金額 / スコア重み）
  - セクターキャップ適用、レジーム乗数
  - 発注株数計算（単元株丸め・aggregate cap）
- Research
  - momentum / volatility / value 等のファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリ
- AI
  - news_nlp: raw_news を LLM（OpenAI / gpt-4o-mini）でセンチメント評価して ai_scores に書き込み
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime を算出・保存
- CLI / ユーティリティ
  - .env の対話式作成・更新: kabusys.config_setup (python -m kabusys.config_setup)
  - 設定検証 CLI: kabusys.validate_config (python -m kabusys.validate_config)
  - Paper Trading 検証レポート生成: kabusys.tools.paper_verification_report
  - ログ設定ユーティリティ（統一的な Stream + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity のユーティリティ

---

## セットアップ手順

以下はローカルで動かすための簡易セットアップ例です。

1. 必要な Python バージョン
   - Python 3.10 以上（PEP 604 の union 型 `X | Y` を利用しているため）

2. 必要ライブラリ（代表例）
   - duckdb
   - psutil
   - openai
   - pyyaml（設定検証で任意）
   - その他（標準ライブラリ: sqlite3 等）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （実プロジェクトでは requirements.txt を用意している想定です。なければ上記を参考にしてください）

3. リポジトリルートで初期ディレクトリを作成
   - data/ と logs/ を作成（自動生成されることが多いですが手動作成しておくと権限問題を避けられます）
     - mkdir -p data logs

4. .env の作成（対話型ウィザード推奨）
   - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を環境変数に設定（config_setup は直接設定しないため export 等で設定）
   - 重要な設定例（.env の例）
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PAPER_FILL_MODE=instant

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると WARNING も失敗として扱う

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用 / 動作切替
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: instant | partial | never | reject
  - OPENAI_API_KEY: OpenAI API を使う場合に必要
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（開発用。0/1）

---

## 使い方

基本的な起動・運用フロー例を示します。

- .env を準備・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config

- ExecutionEngine を起動（発注エンジン）
  - 簡易: KABUSYS_ENV を切り替えて挙動を変えられる
    - Paper Trading：
      - export KABUSYS_ENV=paper_trading
      - python -m kabusys.run_execution
      - Paper モードでは MockBrokerClient を使用し data/paper_trading.db にログを残す
    - Live（本番）:
      - export KABUSYS_ENV=live
      - 注意: 本番では設定を慎重に確認してください（validate_config が警告を出します）

  - 停止方法:
    - run_execution はプロジェクトルート/data/stop_requested.flag を監視しています。ファイル作成で安全に停止できます。
    - KillSwitch が発動すると data/kill.flag を生成して Execution 側で検知・停止させる設計です。

- Monitoring を起動（監視ループ）
  - export MONITOR_POLL_INTERVAL=60  # 秒（任意）
  - python -m kabusys.run_monitoring
  - 監視は常に本番用の sqlite_path（Settings.sqlite_path）を参照して監視ログを記録します（環境に関係なく）

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで PAPER_TRADING_SQLITE_PATH を上書き可能

- ログ
  - logs/<app_name>.log に日次ローテーションで出力されます（TimedRotatingFileHandler）
  - コンソール出力は stdout（stderr ではない）

- Kill / Stop ファイル
  - data/kill.flag : KillSwitch による強制停止指示（Execution 側が参照）
  - data/stop_requested.flag : run_* スクリプト（monitoring / execution）のループ停止用ファイル
  - data/execution.pid : ExecutionEngine が書き込む PID ファイル

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリ内の主なモジュールとファイル構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - config_setup.py          — .env 対話型ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - data/                    — （データファイル置き場: data/*.db, flags）
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し、ai_scores 書込）
    - regime_detector.py     — レジーム判定（MA200 + ニュース）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化層（テーブル作成 / CRUD）
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 発注ログ監視（ファイルは別途）
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 機構
    - alert_manager.py        — （アラート送信ロジック）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体
    - broker_factory.py      — ブローカークライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity

（上の一覧はこのリポジトリの主要部分のみを抜粋しています。詳細はソースツリーを参照してください）

---

## 運用上の注意・推奨

- KABUSYS_ENV=live 設定は本番運用です。LINE通知や kill flag 設定を含め全設定を慎重に確認してください。
- OpenAI API を利用する機能は API キーとトークン利用料が必要です。エラー時はフェイルセーフでスコア 0 等にフォールバックする設計ですが、想定外の影響を避けるため権限管理を行ってください。
- ログディレクトリの権限やディスク容量を監視してください（TimedRotatingFileHandler による古いログ保持はデフォルトで 30 日）。
- data/ ディレクトリ内の .db やフラグファイルは運用上非常に重要です。バックアップ方針を定めてください。
- .env は機密情報を含むため絶対に Git 等にコミットしないでください（config_setup でも注意書きを出しています）。

---

README はここまでです。必要であれば「起動時の環境変数テンプレート（.env.example）」や「各 CLI の詳細なオプション、ExecutionEngine の内部フロー図、DB スキーマ詳細」などの追加ドキュメントを作成できます。どの内容を優先して追加しますか？