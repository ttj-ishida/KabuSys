# KabuSys

日本株向け自動売買システムの軽量実装（モジュール群・ユーティリティ群）。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ用のファクター計算、AI を使ったニュースセンチメント評価などを含むコンポーネント群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されたコンポーネント群を含みます。

- Execution Engine: ブローカークライアント経由で注文を作成・送信・管理する実行系。
- Monitoring: システム状態、注文滞留、ドローダウン等の監視とアラート送信（LINE）。
- Portfolio Construction: 候補選定、重み計算、ポジションサイズ算出などの純粋関数群。
- Research: DuckDB を利用したファクター計算（Momentum, Volatility, Value 等）及び特徴量探索。
- AI モジュール: OpenAI を用いたニュースのセンチメント評価（ai.news_nlp）や市場レジーム判定（ai.regime_detector）。
- Tools: Paper Trading の検証レポート生成など。

設計上の特徴:
- 環境変数ベースの設定管理（kabusys.config.Settings）
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離（専用 SQLite）
- DuckDB をデータ分析用に利用（prices_daily / raw_financials 等を保存）
- 監視データは SQLite（data/monitoring.db）へ永続化
- OpenAI API を用いる処理は API キー必須かつフェイルセーフ設計（失敗時はスキップやフォールバック）

---

## 主な機能一覧

- 実行系
  - 注文作成・送信・状態同期（Reconciler）
  - リスク管理（RiskManager）
  - 注文管理（OrderManager, OrderRepository）
- 監視
  - SystemMonitor: CPU/MEM/DISK, プロセス状態, 株価データ鮮度
  - TradeMonitor: 滞留注文、約定価格の異常検知
  - RiskMonitor: ドローダウン・ポジション上限の監視、Kill Switch（flag ファイルで停止信号）
  - AlertManager: LINE へ通知（クールダウンあり）
  - Streamlit ダッシュボード（監視情報の可視化）
- ポートフォリオ構築
  - 候補選定 (select_candidates)
  - 等配分 / スコア重み配分 (calc_equal_weights, calc_score_weights)
  - ポジションサイジング (calc_position_sizes)
  - セクターキャップ・レジーム調整 (apply_sector_cap, calc_regime_multiplier)
- リサーチ
  - ファクター計算 (calc_momentum, calc_volatility, calc_value)
  - 将来リターン・IC 計算・統計サマリ
- AI 関連
  - ニュースセンチメント自動スコアリング（OpenAI）
  - レジーム判定（MA200 とマクロニュースセンチメントの合成）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 要求環境 / 依存

- Python 3.10 以上（ソース内での型注釈に Python 3.10 の構文を使用）
- 必要（主に）パッケージ:
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai (AI モジュール用)
- 標準ライブラリ: sqlite3, threading, logging, os, pathlib, datetime 等

（実際には requirements.txt をプロジェクトに追加して管理してください）

例:
pip install duckdb psutil requests streamlit openai

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt  （存在しない場合は下記パッケージを個別インストール）
   - 例: pip install duckdb psutil requests streamlit openai

4. データディレクトリ作成（必要に応じて）
   - mkdir -p data

5. 環境変数設定
   - .env または環境変数で設定します。自動読み込み機構があり、プロジェクトルートに `.env` / `.env.local` があると自動で読み込まれます（テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 主要な環境変数（Defaults は Settings クラス参照）:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須）
     - KABU_API_PASSWORD: （必須）
     - OPENAI_API_KEY: OpenAI を利用する場合必須
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: アラート送信用
     - SQLITE_PATH: 監視 DB のパス（default: data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（default: data/paper_trading.db）
     - PAPER_FILL_MODE: paper trading の注文約定モード（instant|partial|never|reject）
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH 等（デフォルト data/ 以下）

6. 初期 DB 作成
   - Execution や Monitoring を最初に起動すると必要なテーブルは自動的に作成されます（monitoring_db.init_monitoring_db が冪等でテーブルを作成します）。

---

## 使い方（実行方法）

以下は主要スクリプトの実行例です。運用は systemd などでデーモン化することを推奨します。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - Paper Trading モード（本番と DB を分離）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - 実行中停止には data/stop_requested.flag を作成するとエンジンが停止します（Stop フラグの検出あり）。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視も data/stop_requested.flag を検出すると停止します。監視は本番 sqlite_path を使用（環境に依らず本番 DB を参照する設計の箇所あり）。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（ニューススコア付与 / レジーム判定）
  - ニューススコア付与: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - 実行スクリプトは含まれていませんが、API は公開されているため外部ジョブから呼び出してください。
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

- Kill Switch / 手動停止
  - KillSwitch は監視結果に応じて data/kill.flag を書き込み、ExecutionEngine 側で検出して停止処理を行います。
  - 手動で停止信号を送りたい場合は data/kill.flag を作成すればよいです（Execution 側で KILL_FLAG を参照）。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが運用モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI を利用する場合必須
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定なら通知はスキップ）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB データベースファイル（default: data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（default: 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等も設定可能

詳細は `src/kabusys/config.py` の Settings クラスを参照してください。

---

## ディレクトリ構成（主要ファイル）

概要: 以下はソースツリーの主なファイル／ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - execution/
    - execution_engine.py     — 実行エンジン本体（注: ファイルの中身が大きい想定）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - ... (broker_api 等)
  - monitoring/
    - monitoring_db.py        — 監視用 SQLite テーブル定義 + API
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
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                      — 実行時生成の DB / PID / flag（リポジトリに含めないこと）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ヘルパー

（実際のリポジトリは上記以外のファイル・モジュールを含む場合があります）

---

## 運用上の注意・設計上のポイント

- Paper Trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。実運用時は混同に注意してください。
- 監視は `data/monitoring.db` に記録されます。バックアップやログローテーションが必要な場合は運用環境で対策してください。
- OpenAI 呼び出しを含む処理は API エラーに対してリトライやフォールバックを実装していますが、API キーは必ず安全に管理してください。
- process priority / CPU affinity 設定は psutil を使用します。権限不足により設定に失敗する可能性があるためログに注意してください。
- `.env` の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準とします。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Kill Switch（data/kill.flag）は冪等に書き込みを行います。手動で flag を作成すると Engine を停止させられます。clear は `KillSwitch.clear()` を使用します。
- 監視ループ・実行エンジンともに `data/stop_requested.flag` を検出すると終了します。デプロイ時に意図せぬファイルがあると起動しないので注意してください。

---

## 開発／拡張のヒント

- DuckDB は分析処理（prices_daily / raw_financials 等）に使われています。ローカルでデータを取り込み、research モジュールを試すときに便利です。
- AI モジュールの OpenAI 呼び出し部分はテスト容易性を考慮して分離されているため、モック化してユニットテストが可能です。
- MonitoringDB は冪等にスキーマ作成・マイグレーションを行います（既存カラムチェックあり）。ロガーやエラーハンドリングは各モジュールで丁寧に扱われています。

---

必要に応じて README にサンプル .env.example、requirements.txt、起動用 systemd ユニット例などを追加できます。README の補足や実運用向けドキュメントの追記をご希望であれば、どの部分を詳しくしたいか教えてください。