# KabuSys

日本株自動売買システムの実装リポジトリ（ライブラリ + 起動スクリプト群）

この README はコードベースの主要コンポーネント、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ用のモジュール群を提供します。主な機能は次のとおりです。

- 戦略（ファクター計算、特徴量探索）用の研究モジュール（DuckDB を想定）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、リスク調整）
- ExecutionEngine（注文管理・発注・リスク管理） — 本番 / ペーパートレードをサポート
- Monitoring（システム状態・注文状況・リスク監視）と Kill Switch
- AI を用いたニュース NLP（OpenAI）によるセンチメント集約
- 運用ツール（構成ウィザード・設定検証・ペーパートレード検証レポート）

設計方針の一部：
- DuckDB と SQLite をデータ層として使用
- 本番／ペーパーの DB 分離（paper_trading モードでは専用 SQLite を使用）
- 自動化・運用に配慮したログ・PID/flag ファイル管理、フェイルセーフ設計

---

## 機能一覧（抜粋）

- run_execution.py
  - ExecutionEngine を起動するエントリポイント。
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録。
  - 起動・停止は data/stop_requested.flag / data/execution.pid により制御。

- run_monitoring.py
  - SystemMonitor のポーリングループを起動するスクリプト。
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト: 60秒）。
  - Monitoring は環境にかかわらず production sqlite_path を使用する。

- config_setup.py
  - 対話式に .env を作成・更新するウィザード。

- validate_config.py
  - .env と config/*.yaml（存在する場合）を起動前に検証する CLI。
  - `--strict` を付けると警告も失敗扱いに。

- tools/paper_verification_report.py
  - ペーパートレード履歴から検証レポート（稼働率、約定率、レイテンシ等）を生成。

- ai/news_nlp.py / ai/regime_detector.py
  - OpenAI を用いたニュースセンチメントの集計・市場レジーム判定（gpt-4o-mini 想定）。
  - API 呼び出しや書き込みはフェイルセーフに設計。

- portfolio/*
  - 候補選定、等重／スコア重み、リスク調整（セクター制限、レジーム乗数）、ポジションサイズ計算等の純粋関数群。

- research/*
  - ファクター計算（momentum/value/volatility）や特徴量解析、IC 計算など（DuckDB 接続を受け取る設計）。

- monitoring/*
  - MonitoringDB（SQLite を使った永続化層）、SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager 統合用の MonitoringEngine。

- utils/*
  - ロギング設定、プロセス優先度／CPU affinity 設定など運用ユーティリティ。
  
---

## セットアップ手順（ローカル開発向け）

前提：Python 3.9+（プロジェクトで特定のバージョン要件があれば適宜合わせてください）。

1. リポジトリをクローンして作業ディレクトリに移動
   - git clone ...  
   - cd <repo>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 依存はプロジェクトに requirements.txt がない想定のため、最低限のパッケージ例:
     - duckdb
     - psutil
     - openai
     - （任意）PyYAML（config 検証で YAML をチェックしたい場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ 実際の運用ではプロジェクトで指定された requirements.txt や pyproject.toml を使ってください。

4. 初期設定ファイルの作成（.env）
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考に）。主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - KABUSYS_ENV — 実行環境（development / paper_trading / live）デフォルト: development
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — ペーパートレード DB（paper_trading 時）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
     - LOG_LEVEL, LOG_DIR, その他

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 本番チェック（警告を失敗扱い）:
     - python -m kabusys.validate_config --strict

---

## 使い方（主要なコマンド）

- ExecutionEngine を起動（デーモン化は各自で）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV=paper_trading の場合は paper_trading SQLite（PAPER_TRADING_SQLITE_PATH）を使用。
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中は data/execution.pid に PID を書きます。
    - 停止は data/stop_requested.flag を作成するか、プロセスに SIGINT（Ctrl+C）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - Monitoring は環境にかかわらず設定された本番 SQLite（SQLITE_PATH）を使用して監視ログを残します。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱いで非ゼロ終了する

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ用の関数呼び出し（ライブラリ用途）
  - 例: ニューススコアリング（Python コードから）
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key="...")

  - 研究用:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value
    - 各関数は duckdb 接続・対象日を渡して呼びます。

---

## 重要な運用ファイル / フラグ

- data/stop_requested.flag
  - run_monitoring.py / run_execution.py がポーリングループ内で存在をチェックし、あれば安全に停止します（手動で作成して停止させる運用が可能）。

- data/kill.flag
  - KillSwitch が条件を満たした場合に書き込むファイル。ExecutionEngine 停止のために用いられます。
  - Settings.kill_flag_clear_on_start が `1` の場合、起動時に自動でクリアされる設定になっています（本番では `0` 推奨）。

- data/execution.pid（デフォルト）
  - ExecutionEngine が PID を書き込むファイル。

- logs/
  - setup_logging により出力されるログファイルはデフォルトで logs/<app_name>.log（日次ローテーション・30 日保持）。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

重要（よく使う）:
- KABUSYS_ENV — execution モード（development / paper_trading / live）デフォルト: development
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- OPENAI_API_KEY — OpenAI API キー（AI機能で必須）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

運用用フラグ:
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（1=yes, 0=no）

設定ウィザード起動や設定検証を利用して、必要な環境変数を整えてください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py               — 環境変数ロード・Settings
- config_setup.py         — .env ウィザード
- validate_config.py      — 設定検証 CLI
- run_execution.py        — ExecutionEngine 起動スクリプト
- run_monitoring.py       — Monitoring 起動スクリプト

src/kabusys/ai/
- news_nlp.py             — ニュース NLP（OpenAI）スコアリング
- regime_detector.py      — 市場レジーム判定

src/kabusys/monitoring/
- monitoring_db.py        — SQLite による監視ログ永続化層
- system_monitor.py       — システム状態・データ鮮度検査
- trade_monitor.py        — 発注ログ監視（ファイル内には参照があるが省略）
- risk_monitor.py         — ドローダウン・ポジション上限監視
- kill_switch.py          — Kill Switch（flag 書き込み）
- monitoring_engine.py    — 各 Monitor を束ねるエンジン
- alert_manager.py        — （アラート送信ロジック。コードベースに存在）

src/kabusys/portfolio/
- portfolio_builder.py    — 候補選定・重み付け
- position_sizing.py      — 発注株数算出
- risk_adjustment.py      — セクターキャップ・レジーム乗数

src/kabusys/research/
- factor_research.py      — ファクター計算（momentum/value/volatility）
- feature_exploration.py  — 将来リターン、IC、統計要約

src/kabusys/tools/
- paper_verification_report.py — ペーパートレード検証レポート

src/kabusys/utils/
- logging_setup.py        — ログ設定ヘルパ
- process_priority.py     — プロセス優先度 / CPU affinity

その他:
- config/                  — YAML 設定ファイル群（テンプレート）
- data/                    — デフォルト DB / flag / pid の配置場所（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db など）
- logs/                    — ログ出力先（setup_logging により作成）

---

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）では LINE 通知等の設定を確実に行い、KILL_FLAG_CLEAR_ON_START=0 を推奨します。
- Monitoring は本番の sqlite_path を参照して監視ログを記録します。paper_trading 時も monitoring は本番 sqlite_path を使う点に注意してください（run_execution は paper_trading 用 DB を使用）。
- OpenAI を用いる機能は API キーが必要で、API のレート制限や課金を考慮して運用してください。失敗時のフォールバックが組まれているものの、機能の設計とコストは運用者で管理してください。
- データベースのマイグレーションやスキーマ変更は monitoring_db.init_monitoring_db に一部ロジックが含まれています。手動で DB を編集する前にバックアップを取ってください。

---

この README はコードベースの現状（主要スクリプト・モジュール）を元に作成しています。追加の実行手順や依存関係はプロジェクト側の requirements/pyproject を参照して更新してください。必要であれば起動オプションや具体的な運用手順（systemd / Docker / Supervisor でのデプロイ例）も追記します。