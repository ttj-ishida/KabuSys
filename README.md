# KabuSys — 日本株自動売買システム（README）

本ドキュメントはリポジトリ内のコードベースに基づく簡易 README です。セットアップ手順、主要機能、使い方、ディレクトリ構成などを日本語でまとめています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／リサーチ基盤です。以下の主要機能を持ちます。

- 発注実行エンジン（ExecutionEngine）／ペーパートレードモード（環境切替可能）
- システム監視 / リスク監視（Monitoring）
- ポートフォリオ構築（銘柄選定・重み算出・株数決定）
- リサーチ（ファクター計算、特徴量解析）
- ニュース NLP を用いた銘柄センチメント評価（OpenAI 経由）
- ペーパートレード検証レポート生成ツール

設計方針として、データ永続化は SQLite（監視ログ等）と DuckDB（リサーチ用分析）を使い、環境変数や .env による設定管理、起動スクリプト群による運用を想定しています。

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を利用し、paper_trading DB（data/paper_trading.db）に完全分離して記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ検知（data/stop_requested.flag）

- run_monitoring.py
  - SystemMonitor をポーリングしてシステム／データ鮮度を記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視ログは常に本番用 sqlite_path を利用

- monitoring モジュール
  - system_monitor、trade_monitor、risk_monitor、monitoring_engine、kill_switch、MonitoringDB 等
  - kill.flag による ExecutionEngine 停止機構、リスクイベントのログ化、ダッシュボード集計

- portfolio モジュール
  - 銘柄選定（select_candidates）、重み算出（等金額・スコア加重）、ポジションサイズ計算（リスクベース等）
  - セクター制限、レジーム乗数等のリスク調整ロジック

- research モジュール
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- ai モジュール
  - news_nlp: raw_news を OpenAI（gpt-4o-mini 等）でセンチメント化して ai_scores に保存
  - regime_detector: ETF やマクロニュースを基に市場レジーム（bull/neutral/bear）を判定・保存

- utils
  - logging_setup: 統一ロギング（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定（psutil 利用）

- ツール
  - config_setup.py: .env を対話式で作成・更新するウィザード
  - validate_config.py: .env および config/*.yaml の事前検証 CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート出力

---

## 動作要件（概略）

- Python 3.9+
- 依存パッケージ（プロジェクトに requirements.txt がある想定）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（config/*.yaml の内容検証用）
- SQLite（組み込み）を使用
- OpenAI を使う機能は OPENAI_API_KEY が必要

※psutil によるプロセス優先度設定・CPU affinity は OS と権限によって失敗する場合があります（警告でスキップされます）。

---

## セットアップ手順

1. リポジトリをクローン／展開する
   - 仮定: ソースは `src/kabusys` に配置済み

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）pip install -r requirements-dev.txt（存在する場合）
   - PyYAML を入れると `validate_config` が config YAML を検証できます: pip install pyyaml

4. .env を作成
   - 推奨: python -m kabusys.config_setup を実行して対話式に作成
   - もしくは手動で作成 (.env.example がある場合は参考にする)

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL（exit code 1）になります

6. データディレクトリの準備
   - デフォルトは `data/` 以下に sqlite/duckdb/log/ pid/flag ファイル等を置きます。アプリ起動時に自動作成されますが、権限が必要な場合は事前にディレクトリ作成を行ってください。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API 用パスワード

- 運用 / オプション
  - KABUSYS_ENV — execution のモード（development|paper_trading|live）デフォルト: development
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 sqlite（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）
  - OPENAI_API_KEY — OpenAI 呼び出しに必要
  - LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
  - LOG_DIR — ログ出力先（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)
  - PID_FILE_PATH / KILL_FLAG_PATH — 各種パスを上書き可能

---

## 使い方（起動例）

- 環境整備（例）
  - export KABUSYS_ENV=development
  - export OPENAI_API_KEY=sk-...
  - export LOG_LEVEL=INFO

- .env を作成（対話式）
  - python -m kabusys.config_setup

- 設定の検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 実行中は data/execution.pid を作成、data/stop_requested.flag により停止可能

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=120 python -m kabusys.run_monitoring
  - デフォルト 60 秒ごとに SystemMonitor.check_once() を実行

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db /path/to/paper_trading.db （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 処理（プログラム的利用）
  - ニュース NLP（ai.news_nlp.score_news）を呼び出す場合は OpenAI API キーが必須
  - 例（Python スクリプト内）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

---

## 運用上の注意

- paper_trading モードでは発注先がモックとなり、paper_trading 用 DB（data/paper_trading.db）に記録されます。本番 DB（monitoring.db 等）とは分離されています。
- process priority / cpu affinity は OS やユーザー権限により実行できない場合があります。ログで警告が出るだけで処理は継続します。
- OpenAI を使う処理は API エラー時にリトライ処理やフォールバック（安全側）を実装していますが、API キーとコスト管理に注意してください。
- kill.flag（KILL_FLAG_PATH）の運用は本番環境では慎重に。validate_config のチェックでは KILL_FLAG_CLEAR_ON_START の設定を警告する仕組みがあります。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 配下の主要なファイル・ディレクトリ一覧です（抜粋）。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"

  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI

  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - trade_monitor.py       — （滞留注文等の監視）※実装あり
    - kill_switch.py         — kill.flag を書き込むロジック
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （通知系、LINE 等）※実装あり？

  - execution/
    - execution_engine.py    — ExecutionEngine（起動・セッション管理）
    - broker_factory.py      — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数計算・投下資金調整
    - risk_adjustment.py     — セクター制限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py     — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
    - __init__.py

  - ai/
    - news_nlp.py            — ニュース NLP の LLM 呼び出しと ai_scores 書込み
    - regime_detector.py     — 市場レジーム判定
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
    - __init__.py

  - data/                    — 実行時生成（ログ・DB・pid・flag 等）

注: 上記は抜粋です。実際のリポジトリ全体を確認してください。

---

## 開発者向けメモ

- ロギングは共通の setup_logging を呼ぶことで統一されます。ログはコンソール（stdout）と日次ローテーションファイルに出力されます。
- DuckDB 接続はリサーチ系で使用し、大量データの分析に最適化されています。
- SQLite は運用ログ（system_status, trade_logs, positions, risk_logs, dashboard）に使用されます。monitoring_db.init_monitoring_db() はマイグレーション的なカラム追加処理を持ち冪等です。
- OpenAI の呼び出しはエラー種別に応じて適切にリトライ/フォールバックを行う実装になっています。テスト時は API 呼び出し関数をモックすることが推奨されます。

---

必要であれば、README にサンプル .env のテンプレート、より詳細な運用手順（systemd / cron / supervisor によるデーモン化、ログローテーションの運用指針等）を追加します。どの情報を追加したいか教えてください。