# KabuSys

日本株自動売買システムのパッケージ（KabuSys）の README。  
このファイルはリポジトリ内の主要スクリプト・ユーティリティ群を概説し、初期セットアップから実行までの手順を日本語でまとめたものです。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。主な機能は以下のとおりです。

- ExecutionEngine：発注・リスク管理・注文再整合（実際のブローカーまたはモックを使用）
- Monitoring：システム稼働性・注文・リスク監視、Kill Switch によるエンジン停止
- Research / AI：ファクター計算、将来リターン分析、ニュースの LLM ベースセンチメント評価、レジーム判定
- Portfolio：銘柄選定・重み付け・ポジションサイズ計算・セクター上限適用
- Tools：ペーパートレード検証レポートなどの補助ツール
- 設定ユーティリティ：.env ウィザード（config_setup）・設定検証（validate_config）
- ロギング / ユーティリティ：統一ログ設定、プロセス優先度設定など

設計上、DuckDB（分析用）とSQLite（監視・ペーパートレード用）を併用し、本番 DB とペーパートレード DB は分離されます。

---

## 主な機能一覧

- 環境設定ウィザード（python -m kabusys.config_setup）
- 起動前設定検証（python -m kabusys.validate_config）
- Execution エンジン起動（本番 / ペーパートレード切替）
- Monitoring ポーリング／アラート（MONITOR_POLL_INTERVAL で間隔制御）
- Kill Switch：条件に基づき data/kill.flag を書き込んで Execution を停止
- AI ニューススコアリング（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ETF とマクロニュースを合成）
- ポートフォリオ構築ロジック（候補選定・重み付け・単元株丸め）
- Paper Trading 検証レポート出力（期間指定で検証指標を出力）

---

## 必要な依存パッケージ（主なもの）

- Python 標準ライブラリ（sqlite3, threading, logging など）
- duckdb
- psutil
- openai
- PyYAML（config/.yaml の内容検証を行いたい場合に必要）

インストール例:
- pip install duckdb psutil openai pyyaml

（requirements.txt があるリポジトリではそちらを利用してください）

---

## セットアップ手順

1. リポジトリをチェックアウトして作業ディレクトリをプロジェクトルートにする。
   - プロジェクトルートは .git か pyproject.toml があるディレクトリとして自動検出されます。

2. 依存ライブラリをインストールする:
   - pip install duckdb psutil openai pyyaml

3. 環境変数を準備する:
   - 対話式ウィザードで .env を作成する（推奨）:
     - python -m kabusys.config_setup
   - 重要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション / 推奨:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能を使う場合に必要
     - PAPER_FILL_MODE — paper_trading 用の約定モード（instant/partial/never/reject）
   - 自動ロード:
     - .env / .env.local は自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

4. 設定検証:
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗（exit 1）扱いになります

5. データディレクトリの準備:
   - data/ ディレクトリに DB ファイルが作成されます（初回起動時に自動作成されます）
   - logs/ ディレクトリは logging 設定で作成されます

---

## 使い方（起動コマンド例）

- ExecutionEngine（通常運用）:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- ExecutionEngine（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - ペーパートレード時は data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と分離されます。

- Monitoring（監視ループ）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト: 60）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード（対話式 .env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか環境変数 PAPER_TRADING_SQLITE_PATH を設定

- ログ:
  - デフォルトで logs/<app_name>.log に日次ローテーションで保存されます（ログレベルは LOG_LEVEL／引数で制御）。
  - setup_logging() がアプリ起動時に呼ばれるため、各スクリプト（execution / monitoring 等）は統一されたログ設定を使用します。

---

## 停止・Kill Switch の仕組み

- 手動停止：
  - data/stop_requested.flag が作成されると run_monitoring / run_execution のループは停止します（スクリプト側で検出して終了）。
- Kill Switch（自動停止）：
  - リスク条件（ドローダウン超過等）を満たすと、KillSwitch が data/kill.flag を作成します。ExecutionEngine は起動時/監視でこれを検出して安全に停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると Execution 起動時に kill.flag を自動的にクリアします（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

以下はソースの主要パス（src/kabusys）を抜粋した構成例です。

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings 管理（自動 .env 読み込み等）
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — Monitoring ポーリング起動スクリプト
    - utils/
      - logging_setup.py        — ログ設定ユーティリティ
      - process_priority.py     — 優先度 / CPU affinity 設定ユーティリティ
    - monitoring/
      - monitoring_db.py        — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
      - system_monitor.py       — システム稼働性・データ鮮度監視
      - trade_monitor.py        — 注文関連監視（ファイルには実装あり）
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - kill_switch.py          — kill.flag 管理
      - monitoring_engine.py    — 各 Monitor をまとめるポーリングエンジン
      - alert_manager.py        — アラート送信（ファイルには実装あり）
    - execution/
      - execution_engine.py     — ExecutionEngine 本体（発注ループ等）
      - broker_factory.py       — ブローカークライアント生成（実ブローカー / Mock 切替）
      - order_manager.py        — 注文管理
      - order_repository.py     — 注文永続化（SQLite 等）
      - reconciler.py           — 注文再整合ロジック
      - risk_manager.py         — 実行時リスク制御
    - portfolio/
      - portfolio_builder.py    — 候補選定・重み付け
      - position_sizing.py      — 株数決定・丸め・投下資金スケーリング
      - risk_adjustment.py      — セクター制限・レジーム乗数
    - research/
      - factor_research.py      — モメンタム・バリュー・ボラ計算（DuckDB）
      - feature_exploration.py  — IC / 将来リターン / 統計サマリ
    - ai/
      - news_nlp.py             — OpenAI を使ったニュースセンチメント集約・書込み
      - regime_detector.py      — 市場レジーム判定（ETF + マクロニュース）
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート生成
    - data/                      — 実行時に生成される（DB・flag・pid 等）
      - monitoring.db (default: data/monitoring.db)
      - kabusys.duckdb (default: data/kabusys.duckdb)
      - paper_trading.db (ペーパートレード用)
      - kill.flag / stop_requested.flag / execution.pid

（注）上記は主要ファイルの一覧です。細かなサブモジュールや補助ファイルはリポジトリ内を参照してください。

---

## 補足・運用上の注意

- .env は機密情報を含むため Git にコミットしないこと（config_setup.py のヘッダにも同旨の注意あり）。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必要。API 呼び出しの失敗時はフェイルセーフ（多くは 0.0 等でフォールバック）を採用していますが、API 利用制限やコストに注意してください。
- ログディレクトリ作成やファイル書き込み権限がない環境ではファイルログが無効化され、コンソールのみのログになります（setup_logging の挙動）。
- DuckDB / SQLite のファイルパスは Settings で制御できます。ペーパートレード時は paper_sqlite_path を使用して本番 DB と分離されます。

---

README に記載のない詳細な実装・API 使用法・拡張方法は各モジュールの docstring と関数コメントを参照してください。必要であればモジュール別の詳細ドキュメント（使い方、設計資料）も作成可能です。