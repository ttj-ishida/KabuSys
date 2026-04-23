# KabuSys

日本株自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注（本番 / ペーパートレード）・監視・AI ニュース解析・研究ユーティリティを含む自動売買プラットフォームのコア部分です。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。主な設計方針は次のとおりです。

- 発注ロジックと研究（factor/feature）・ポートフォリオ構築ロジックを分離
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）の切替を環境変数で管理
- DuckDB を使った分析用データ、SQLite を使った監視・注文ログ永続化
- OpenAI API を用いたニュースセンチメント解析・レジーム判定機能（オプション）
- 監視（Monitoring）コンポーネントによるシステム状態・注文状態の常時チェックと Kill Switch

---

## 主な機能一覧

- ExecutionEngine（発注エンジン）
  - 本番とペーパートレードを切り替え可能（KABUSYS_ENV）
  - リスク管理（RiskManager）・注文管理（OrderManager）・再整合（Reconciler）を組み合わせて発注を実行
- Monitoring（監視）
  - SystemMonitor: CPU/MEM/DISK、プロセス生存、データ鮮度を監視
  - TradeMonitor, RiskMonitor を組み合わせた MonitoringEngine（アラート送信・Kill Switch）
  - SQLite ベースの監視 DB（monitoring_db.py）
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群
- Research（研究用）
  - ファクター計算（momentum/value/volatility）、forward returns、IC 計算、特徴量サマリ
  - DuckDB 接続を受けてオフラインで実行
- AI（OpenAI 利用）
  - news_nlp: ニュースを LLM でセンチメント解析して ai_scores テーブルに書き込み
  - regime_detector: ETF（1321）の MA200 とマクロニュースを組み合わせて市場レジーム判定
- CLI ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## セットアップ手順（開発環境向け）

前提: Python 3.8+（コードは型注釈で 3.8+ を想定）、git が使える環境

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要なパッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai psutil
   - （YAML 検証を使う場合）pip install pyyaml

   ※ 実運用では requirements.txt / poetry などで管理してください。

4. データディレクトリの作成（任意だが推奨）
   - mkdir -p data logs

5. 環境変数設定
   - 対話式ウィザードで `.env` を作成:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成。主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
     - PAPER_FILL_MODE=instant|partial|never|reject

6. 設定検証
   - python -m kabusys.validate_config
   - 本番実行前は `--strict` オプションで警告も失敗扱いにできます。

---

## 実行方法（使い方）

以下は主要なエントリポイントと実行例です。実行前に .env をセットしておくことを推奨します。

- 監視ループを起動（SystemMonitor 単体）
  - python -m kabusys.run_monitoring
  - 補足:
    - デフォルトのポーリング間隔: 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
    - 監視は Monitoring 用 SQLite（Settings.sqlite_path）を使用（環境に依らずデフォルトの sqlite_path を使用）

- 発注エンジンを起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します
    - 実行中は data/execution.pid に PID を書きます
    - 停止させるには data/stop_requested.flag を作成（または Kill Switch による data/kill.flag が書かれると停止シグナルが実行されます）

- .env 設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
  - 環境変数:
    - PAPER_TRADING_SQLITE_PATH でデフォルト DB パスを指定可能

- AI 機能（ニュース点数化 / レジーム判定）
  - 必要: OPENAI_API_KEY を環境変数に設定（または関数呼び出し時に渡す）
  - モジュール関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- Kill Switch:
  - KillSwitch は条件が揃うと data/kill.flag を書き、ExecutionEngine 側で検知して発注を停止します（本番での安全措置）。
  - Settings.kill_flag_clear_on_start が 1 に設定されていると起動時に kill.flag を自動クリアします（本番では推奨しません）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (default: development) — 値: development | paper_trading | live
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- LOG_LEVEL (default: INFO)
- OPENAI_API_KEY (AI 機能を使う場合)
- MONITOR_POLL_INTERVAL (監視ループ間隔秒, default: 60)
- PAPER_FILL_MODE (paper_trading の約定挙動: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (0/1)

詳しい説明やデフォルト値は kabusys.config.Settings のプロパティを参照してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env 自動ロード / Settings 定義
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 起動前チェック CLI

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py — ニュースの LLM センチメント解析（ai_scores への書込）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロセンチメント）

- monitoring/
  - monitoring_db.py — SQLite による監視ログ永続化（テーブル初期化 / CRUD）
  - system_monitor.py — CPU/MEM/DISK・データ鮮度・プロセス監視
  - trade_monitor.py — （注文・約定の監視）※実装ファイルは該当ディレクトリを参照
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書込みロジック
  - monitoring_engine.py — 各モニタを束ねてポーリング、アラート連携

- execution/
  - execution_engine.py — 発注エンジン（EngineConfig, run_session 等）
  - broker_factory.py — BrokerClient の生成（本番/Mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など

- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数計算・単元丸め・投下資金制限
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — momentum/value/volatility 等のファクター計算
  - feature_exploration.py — forward returns, IC, summary 統計
  - __init__.py（外部公開 API）

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成
  - __init__.py

- utils/
  - logging_setup.py — 統一ログ設定（Stream + TimedRotatingFileHandler）
  - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
  - __init__.py

その他:
- data/ — デフォルトの DB / flag / pid 等が格納される想定（自動作成されることが多い）
- logs/ — ログファイル（log_dir 環境変数で変更可）

---

## 運用上の注意点

- 本番実行前に必ず `python -m kabusys.validate_config` で設定を検証してください。
- 本番環境（KABUSYS_ENV=live）では kill_flag_clear_on_start を 0（デフォルト）にしておくことを推奨します。自動クリアは危険です。
- AI 機能を使う場合は OpenAI の API 使用料・レート制限に注意してください。news_nlp / regime_detector はリトライ・バックオフ実装がありますが、運用計画を検討してください。
- logs ディレクトリのパーミッションやディスク容量に注意してください（ログローテーションは 30 日保持）。
- DuckDB / SQLite ファイルは定期的にバックアップしてください。特に本番 SQLite（monitoring.db）は重要な監視・注文ログを保持します。

---

必要に応じて README に追記したい内容（例: サンプル .env、要求される Python バージョンの明確化、CI 手順、デプロイ手順など）があれば教えてください。