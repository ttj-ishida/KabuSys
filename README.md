# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群を収めた軽量なフレームワークです。戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究（ファクター計算）、および OpenAI を用いたニュース NLP（センチメント評価）などの機能を備えます。

---

## プロジェクト概要

- 設計方針は「現物市場での安全性」と「テスト容易性の両立」。
- 本番（live）・ペーパー（paper_trading）・開発（development）を環境変数で切替可能。
- 発注ロジックと監視ロジックを分離し、監視から発注エンジンへキルスイッチ（フラグファイル）で安全に停止を通知できる設計。
- DuckDB を使った分析用 DB、SQLite を監視／注文ログ用 DB として使用（デフォルトファイルは `data/` 配下）。

---

## 主な機能一覧

- Execution（発注エンジン）
  - ExecutionEngine、OrderManager、RiskManager、Reconciler 等の実装（発注・注文管理・リスク制御）
  - 環境が `paper_trading` の場合はモックブローカーを使用し、本番 DB と分離して `data/paper_trading.db` に記録
- Monitoring（監視）
  - SystemMonitor：プロセス稼働・CPU/メモリ/ディスク・データ鮮度を監視
  - TradeMonitor：滞留注文・約定異常を監視
  - RiskMonitor：ドローダウン・ポジション上限を監視、必要に応じて kill flag を書き込む
  - MonitoringEngine：各 Monitor のポーリングとアラート発行
- AI（OpenAI 統合）
  - news_nlp.score_news：ニュース記事を LLM でセンチメント評価し `ai_scores` に保存
  - regime_detector.score_regime：ETF（1321）の MA 乖離とマクロニュースの LLM 評価を合成して日次レジーム判定
- Research / ファクター計算
  - ファクター（モメンタム / ボラティリティ / バリュー）計算機能
  - 将来リターン、IC（Information Coefficient）等の解析ユーティリティ
- Portfolio（ポートフォリオ構築）
  - 候補選定、重み計算（等配分／スコア加重）、ポジションサイジング、セクター制約の適用等
- ユーティリティ
  - 環境設定ウィザード（.env 生成）と設定検証 CLI
  - process priority / CPU affinity 設定ユーティリティ
  - Paper trading 検証レポート生成ツール

---

## セットアップ手順（開発環境向け）

1. Python 環境を準備（推奨: venv）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必要なライブラリをインストール
   - 本リポジトリには requirements ファイルが付属しないため、最低限以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

3. プロジェクトルートに移動（.env 自動ロードはプロジェクトルートを基準に探索します）

4. 初期設定（.env）を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは `.env.example` を参考に `.env` を作成してください（リポジトリに example がある場合）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合:
     - python -m kabusys.validate_config --strict

注意: SQLite / DuckDB のデフォルトファイルパスは `data/monitoring.db` と `data/kabusys.duckdb`。必要なら .env で `SQLITE_PATH` / `DUCKDB_PATH` を上書きしてください。

---

## 環境変数（主要なもの）

- KABUSYS_ENV: 実行環境（development / paper_trading / live）  
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルトあり）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 環境時）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）

---

## 使い方（主要なコマンド）

- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告もエラー扱い）:
    - python -m kabusys.validate_config --strict

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - 環境に依らず監視は本番用 sqlite_path を使用して DB を初期化します
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
    - 停止はプロジェクトルート `data/stop_requested.flag` を作成すると検出して終了

- 発注（Execution）プロセス起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`data/paper_trading.db` に記録（本番 DB と分離）
    - 実行中は `data/execution.pid` を作成
    - リモート等から停止させるには `data/stop_requested.flag` を作成

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- AI 関連（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡すとニュースセンチメントを計算して `ai_scores` テーブルへ書き込みます
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - market_regime テーブルへ日次レジームを書き込みます

---

## Kill Switch / 停止フラグ

- ExecutionEngine を強制停止するためのフラグ: `data/kill.flag`
  - 監視側（KillSwitch）や管理者によって書き込まれます
  - ExecutionEngine 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると自動クリアされます（本番では注意）

- プロセス停止要求フラグ: `data/stop_requested.flag`
  - run_monitoring / run_execution はこれを検知して安全に終了します

---

## 重要な挙動メモ

- Paper trading は本番 DB と分離: `settings.is_paper` が True の場合 `paper_sqlite_path` を使用
- 設定ファイル（config/*.yaml）は存在しなくても動作しますが、validate_config で警告されます
- OpenAI API 呼び出しはリトライ・バックオフ機構を備えています。API キーは `OPENAI_API_KEY` または関数引数で供給
- process priority は起動時に `set_process_priority("high")` が試行されます（権限不足等では警告でスキップ）

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- config_setup.py         — .env 対話式ウィザード
- validate_config.py      — 起動前設定検証 CLI
- run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py        — ExecutionEngine 起動スクリプト
- utils/
  - __init__.py
  - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
- monitoring/
  - monitoring_db.py      — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py      — （アラート送信管理：実装は別ファイル）
  - monitoring_engine.py
- execution/               — 発注関連（OrderManager, ExecutionEngine 等）
  - order_repository.py
  - order_manager.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py
  - execution_engine.py
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
- data/ (ランタイムで作成されることを想定)
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用)

その他:
- src/kabusys/tools/paper_verification_report.py — ペーパートレード検証レポート生成ツール

（実際の repo にはさらに細かいファイル・モジュールがあります。上は主要コンポーネントの概観です。）

---

## 依存関係（主な外部ライブラリ）

- duckdb
- psutil
- openai
- PyYAML（任意、validate_config の YAML 検証で使用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib など

環境によっては追加のパッケージが必要となります。テスト・本番環境用の requirements.txt を用意してください。

---

## 開発上の注意点

- .env ファイルは決してリポジトリにコミットしないこと（config_setup にも同旨の注記あり）。
- 本番（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0` を推奨。自動クリアは危険。
- OpenAI を実行する機能は API コスト・レート制限に注意（score_news / score_regime はリトライ実装あり）。
- DuckDB / SQLite への書き込みはトランザクションで保護されていますが、バックアップ・ローテーション戦略を検討してください。

---

必要であれば、README に実行例（.env のテンプレート、systemd ユニット例、docker-compose 例等）を追加します。どの情報を優先的に追加したいか教えてください。