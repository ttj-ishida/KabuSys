# KabuSys

日本株自動売買システム KabuSys のリポジトリ用 README（日本語）

概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な要素は以下の通りです。

- 発注エンジン（ExecutionEngine）：本番 / ペーパートレード双方に対応  
- 監視機構（Monitoring）：プロセス死活監視、データ鮮度、リスク（ドローダウン等）監視、Kill Switch  
- ポートフォリオ構築ライブラリ（候補選定・重みづけ・株数計算など）  
- 研究（ファクター計算・特徴量解析）用モジュール（DuckDB を利用）  
- AI モジュール（ニュースの NLP によるセンチメント評価、レジーム判定、OpenAI 経由）  
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）  

設計方針のポイント：
- 設定は .env / 環境変数で管理（自動ロード機能あり、必要に応じて無効化可能）
- 本番 DB とペーパートレード DB は分離
- ログは標準出力 + 日次ローテートファイルで統一管理
- DuckDB を用いて大規模集計・研究処理をローカルで実行

---

## 機能一覧

- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV に応じて実ブローカーまたは MockBroker を利用。
  - ペーパートレード時は data/paper_trading.db（既定）を使用して本番 DB と分離。
  - 停止はデータディレクトリの stop_requested.flag / kill.flag を用いて制御可能。

- run_monitoring.py
  - SystemMonitor をポーリング実行。システムリソース、データ鮮度、プロセス生存などを定期チェック。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。

- monitoring パッケージ
  - MonitoringDB（SQLite）: 監視ログ・トレードログ・リスクログ・ダッシュボードの永続化
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager, MonitoringEngine

- portfolio パッケージ
  - 銘柄選定（select_candidates）、重み計算（等重/スコア重み）
  - ポジションサイズ決定（risk_based / equal / score）、セクターキャップ、レジーム乗数

- research パッケージ
  - ファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン、IC 計算、ファクター統計サマリー（DuckDB を利用）

- ai パッケージ
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュースを合成して市場レジーム判定
  - OpenAI API を利用するため OPENAI_API_KEY が必要

- utils
  - logging_setup: 共通ログ設定（stdout + 日次ローテーション）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ
  - config / config_setup / validate_config: .env の対話式生成・自動読み込み・検証 CLI

- tools
  - paper_verification_report: ペーパートレード DB から PASS/FAIL 判定を行うレポート生成

---

## セットアップ手順

前提
- Python 3.10 以上を想定（型アノテーションなどで利用）
- system-level: sqlite3 は標準搭載、DuckDB は Python ライブラリとして必要

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install -r requirements.txt
   - requirements.txt がない場合、少なくとも以下をインストールしてください:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（config 検証で YAML を使う場合に推奨）
   例:
     - pip install duckdb psutil openai PyYAML

3. データディレクトリを作成
   - mkdir -p data logs

4. 環境変数（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作成する場合の最小例:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_password_here
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

   注意:
   - 自動で .env をロードする機能はデフォルトで有効です。無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も致命扱いにするには --strict

---

## 使い方

基本的な起動 / 運用コマンド：

- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - 起動時、プロセス優先度を high に設定します（可能な場合）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 30秒ごと
  - 監視は（設定に関わらず）本番用 sqlite_path を使用して監視ログを残します。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- .env の対話設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告があると exit(1)

運用関連のフラグ / ファイル
- stop_requested.flag
  - run_execution.py / run_monitoring.py はプロジェクトルート/data/stop_requested.flag を監視し存在したらループを抜けます（シャットダウン）。
- kill.flag
  - KillSwitch がトリガーすると data/kill.flag に理由を書き込み、ExecutionEngine に停止を促す（Execution 側はこれを検出して停止する設計）。
- PID ファイル
  - data/execution.pid（デフォルト）にエンジンの PID を記録

ログ
- デフォルトでは logs/<app_name>.log に日次ローテートで出力されます（30日保持）。
- コンソール出力は stdout に出ます（cron 等でリダイレクトしやすい）。

AI 関連
- news_nlp, regime_detector を利用するには OpenAI の API キーが必要です。
  - 環境変数 OPENAI_API_KEY を設定してください。
- API 呼び出しは失敗時にリトライやフェイルセーフ（0.0 フォールバック）を行う設計です。

ペーパートレード
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）にトレード履歴が記録されます。
- 本番 DB とは完全分離されます。

---

## 主要設定（環境変数）

重要な環境変数の抜粋：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY — OpenAI API キー（AI 機能に必要）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアする（1=クリア、0=クリアしない。production では 0 を推奨）

詳細は `kabusys/config.py` と `kabusys/config_setup.py` を参照してください。

---

## ディレクトリ構成

ルートの主要ファイル / ディレクトリ（src/kabusys を想定）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py       — 共通ログ設定
      - process_priority.py    — 優先度 / CPU affinity 設定
    - monitoring/
      - monitoring_db.py       — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
    - execution/                — 発注関連（Broker, Engine, OrderManager 等）
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - data/ (実行時に生成されることが多い)
      - monitoring.db (デフォルト SQLITE_PATH)
      - paper_trading.db (ペーパートレード用)
      - kill.flag, stop_requested.flag, execution.pid
    - tools/
      - paper_verification_report.py

---

## 開発上の注意点 / 運用時の注意

- 本番（KABUSYS_ENV=live）では設定を慎重に行ってください。validate_config の警告や注意点を必ず確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも注記があります）。
- OpenAI 等の外部 API を使う機能は API キーと費用が必要です。テストは Mock 実装や小規模データで行ってください。
- run_execution / run_monitoring は stop_requested.flag による優雅な停止、kill.flag による緊急停止（Kill Switch）をサポートしています。運用手順でどちらを用いるかを定めてください。
- DuckDB を使った分析はローカルファイルを参照します。データのバックアップ戦略を立ててください。

---

この README はコードベースから抜粋して要点をまとめたものです。より詳細な仕様や運用手順は各モジュール（kabusys/ 以下のファイル群）および関連ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）があればそちらも参照してください。