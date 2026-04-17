# KabuSys

KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした軽量なプロジェクトです。本リポジトリは以下の主要領域を含みます: 発注実行（Execution）、監視（Monitoring）、ポートフォリオ構築（Portfolio）、リサーチ（Research）、AI ベースのニュース解析（AI）、およびユーティリティ・ツール群。

---

## プロジェクト概要

- 目的: 日本株の自動売買ワークフロー（シグナル → 注文 → 約定管理 → ポジション管理）と、開発/検証向けの研究・監視機能を提供する。
- 設計方針:
  - 実運用（live） / ペーパートレード（paper_trading） / 開発（development）に対応。
  - DB は SQLite（監視・注文ログ）と DuckDB（時系列・ファクター計算）を使用。
  - AI（OpenAI）を利用したニュースセンチメント評価・レジーム判定機能を搭載。
  - 監視サブシステムは kill flag による安全停止や LINE 通知をサポート。

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine による注文送信、OrderManager / OrderRepository を使った状態管理
  - Reconciler による起動時の自動復旧（ブローカーとの突合）
  - Paper Trading モード（KABUSYS_ENV=paper_trading）では MockBroker を使用し、本番 DB と分離して data/paper_trading.db に記録

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存確認、株価データ鮮度チェック
  - TradeMonitor: 滞留注文・約定異常価格検出
  - RiskMonitor: ドローダウン・ポジション上限の監視と警告ログ化
  - MonitoringEngine: 各モニタを束ねてポーリング実行
  - AlertManager: LINE プッシュ通知（クールダウン管理）
  - streamlit ベースの簡易ダッシュボード（reading-only）

- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 重み計算（等分・スコア加重）
  - セクター上限適用、レジーム乗数
  - 株数決定ロジック（position sizing） — 単元株処理・エンベロープ（available_cash に合わせたスケール調整）付き

- Research（研究）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン算出、IC（情報係数）計算、統計サマリ

- AI（OpenAI 統合）
  - news_nlp: ニュース記事をまとめて LLM に投げ、銘柄別センチメント（ai_scores）を生成
  - regime_detector: ma200 乖離 + マクロニュースの LLM センチメントを合成して市場レジーム判定を行い DB に書き込み

- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率・成功率・レイテンシ等の集計）

---

## セットアップ手順（開発 / ローカル実行向け）

※ 実際の requirements.txt は本コード一覧に含まれていません。以下は最低限の推奨パッケージ例です。

1. Python 3.10+ を用意する。

2. 仮想環境を作成・有効化する（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール:
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他パッケージを追加してください）

4. プロジェクトルート直下に data ディレクトリを作成:
   - mkdir -p data

5. 環境変数の設定:
   - プロジェクトルートに .env（または .env.local）を作成して設定可能。自動ロードはデフォルトで有効。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: （必須）
     - OPENAI_API_KEY: OpenAI を使用する機能に必要
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知を有効にする場合
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文埋め方）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
   - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. データベース初期化:
   - 監視 DB テーブルは run_monitoring や run_execution の起動時に init_monitoring_db() が実行され、必要テーブルが作成されます。

---

## 使い方（代表的なコマンド）

- ExecutionEngine を起動する（本番／paper_trading 共通）:
  - python -m kabusys.run_execution
  - 補足: KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper_trading 用 SQLite に記録します。
  - 起動時に data/execution.pid に PID が書かれ、停止は data/stop_requested.flag や data/kill.flag を通じて制御できます。

- Monitoring（監視ループ）を起動する:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位でオーバーライド可能（デフォルト 60）。
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存しない設計）。

- Streamlit ダッシュボード（読み取り専用）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで SQLite を開くため、MonitoringEngine を先に起動して監視データを生成してください。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

- AI 機能（プログラムから利用）:
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")  — OpenAI API キーが必要
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key="...")

---

## 主要ファイル・挙動に関する補足

- 設定ロード (.env):
  - kabusys.config は自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
  - Settings クラスで環境変数の検証を行います（必須項目未設定時は ValueError を送出）。

- DB パス（デフォルト）:
  - 監視 SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db
  - DuckDB: data/kabusys.duckdb

- プロセス優先度:
  - run_execution / run_monitoring の起動時に set_process_priority("high") を呼び出します（psutil ベース）。失敗時は警告を出して継続します。

- Kill / Stop フラグ:
  - data/stop_requested.flag: run_* スクリプトがこのファイルの存在を検知して安全にループを抜けます。
  - data/kill.flag: KillSwitch が書き込むファイルで ExecutionEngine 停止を要求します（監視サブシステムによる安全停止）。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py (Settings / .env 自動ロード)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor 起動スクリプト)
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（broker_factory, execution_engine, order_repository 等）
  - monitoring/
    - monitoring_db.py (SQLite テーブル定義・永続化層)
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - data/  (ランタイムに使用するディレクトリ例)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
    - execution.pid / stop_requested.flag / kill.flag
  - utils/
    - process_priority.py
    - __init__.py
  - その他: data モデル・ブローカー周りの実装ファイル等

（上記は本README に含まれるコードに基づく主要ファイル一覧です。実プロジェクトではさらに多くのファイル・依存が存在する可能性があります。）

---

## 開発・運用上の注意点

- KABUSYS_ENV による分岐:
  - paper_trading: ブローカーは Mock を使用し、paper_trading_sqlite_path に記録。実口座との分離を保証。
  - live: 実ブローカー接続を前提。取り扱いには注意。
- AI 呼び出し:
  - OPENAI_API_KEY が必須。API 呼び出しはレート制限・ネットワークエラー等を考慮したリトライ設計になっていますが、キー管理は慎重に。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等で、既存 DB へのカラム追加（簡易マイグレーション）処理を含みます。
- テスト:
  - AI API 呼び出しやシステム機能はモック可能（内部の呼び出し関数を patch してテストする設計）。
- 権限:
  - set_process_priority / cpu_affinity は OS 権限に依存します（権限不足で設定に失敗した場合はログ警告でスキップ）。

---

## よく使うコマンドまとめ

- 仮想環境・依存インストール:
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil requests openai streamlit

- 実行:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はリポジトリ内の主要モジュール群（Execution / Monitoring / Portfolio / Research / AI / Tools）に基づいて作成しました。実行時の詳細な挙動や追加の設定項目は各モジュール（config.py、run_*.py、各サブパッケージの docstring）を参照してください。必要があれば、セットアップ手順の補足（requirements.txt、docker コンテナ化手順、デプロイ手順など）も作成できます。