# KabuSys

日本株自動売買システム（ライブラリ／起動スクリプト群）の README（日本語）

概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は日本株を対象にした自動売買システムのコードベースです。主な責務は次のとおりです。

- データ（DuckDB / SQLite）を用いたファクター計算・リサーチ
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine による注文管理（本番 / ペーパートレード切替）
- 監視（System / Trade / Risk）と Kill Switch
- ニュースの NLP（OpenAI）を使ったセンチメント評価・レジーム判定
- ユーティリティ（環境設定ウィザード、設定検証、検証レポート生成）

設計方針として「本番 DB と開発／ペーパートレードを分離」「ルックアヘッドバイアスを避ける」「フェイルセーフ（API失敗時のフォールバック）」が意識されています。

---

## 主な機能一覧

- 設定管理
  - .env 生成ウィザード（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）
- 実行（Execution）
  - ExecutionEngine 起動スクリプト（`run_execution.py`）
  - ペーパートレードモード対応（MockBrokerClient／専用 SQLite）
  - リスク管理（ポジション上限、ドローダウン等）
- 監視（Monitoring）
  - System / Trade / Risk モニタ、監視ループ（`run_monitoring.py`）
  - Kill Switch（`data/kill.flag` による Execution 停止）
  - 監視データ永続化（SQLite）
- 研究・ファクター計算
  - Momentum / Volatility / Value 等のファクター（DuckDB）
  - 将来リターン・IC 計算などの統計ユーティリティ
- AI（OpenAI）
  - ニュースセンチメント評価（`kabusys.ai.news_nlp`）
  - 市場レジーム判定（`kabusys.ai.regime_detector`）
- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）
- 共通ユーティリティ
  - ロギング設定（ファイルローテーション含む）
  - プロセス優先度 / CPU affinity 設定（psutil ベース）

---

## 要件（推奨）

- Python 3.10+
- 必須／推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML（`validate_config` が YAML を検証する場合）
- ファイルシステムに `data/` と `logs/` へ書き込み可能であること

（実際にはプロジェクトに requirements.txt があればそれを使用してください）

---

## セットアップ手順（クイックスタート）

1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例:
     - pip install duckdb psutil openai
     - 必要に応じて: pip install PyYAML

3. .env の作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - もしくは手動で `.env` をプロジェクトルートに配置

4. 設定の検証
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする場合は `--strict` を付ける

5. データディレクトリの確認
   - デフォルト DB 等は `data/` 配下に置かれます（必要なら作成）
   - ログは `logs/` に出力されます（`kabusys.utils.logging_setup`）

6. 実行・監視の起動（次章参照）

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 実行環境
  - 値: `development` / `paper_trading` / `live`
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルトあり）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（`instant` / `partial` / `never` / `reject`）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動でクリアするか（0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動で .env を読み込まない（テスト用）

設定は `.env` に記述しておくことを想定しています。テンプレートは .env.example を参照してください（存在する場合）。

---

## 使い方（主要コマンド）

- 環境設定ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV により本番／ペーパートレードを自動切替）
  - python -m kabusys.run_execution
  - ペーパートレードにする:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合、MockBrokerClient が使われ、DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
  - 停止方法:
    - `data/stop_requested.flag` を作成すると run_execution の起動ループが検知して停止します
    - kill.switch を使って ExecutionEngine 側に停止信号（`data/kill.flag`）を送ることもできます

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - run_monitoring は監視用 DB（sqlite_path）へ書き込みを行います。監視は常に本番 sqlite_path を参照します（環境に依存しない）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH でデータベースを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーを引数または環境変数 OPENAI_API_KEY で指定

---

## Kill Switch / 停止フラグ等の挙動

- kill.flag（デフォルト: data/kill.flag）
  - KillSwitch が条件を満たすとこのファイルを書き、ExecutionEngine に停止を要求します
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動クリアされます（本番では推奨しない）

- stop_requested.flag（スクリプト停止用）
  - run_monitoring / run_execution は `data/stop_requested.flag` の存在を見てループを終了します
  - 手動で停止するときはこのファイルを作成してください

- PID ファイル
  - Execution 起動時に PID を `data/execution.pid`（デフォルト）に書きます

---

## 監視 DB（SQLite）概要

`kabusys.monitoring.monitoring_db.init_monitoring_db` により必要テーブルが冪等で作成されます。主なテーブル:

- system_status: CPU/メモリ/ディスク/プロセス状態の時系列ログ
- trade_logs: 発注・約定イベントログ（latency_ms カラムあり）
- positions: 保有ポジション
- risk_logs: リスク関連イベント（デデュプリケーション対応）
- dashboard: 集計（id=1 の1行で保持）

これらは run_monitoring / run_execution 起動時に自動作成・マイグレーションされます。

---

## ディレクトリ構成（抜粋）

プロジェクトルートの `src/kabusys` を基準に主要ファイルを列挙します。

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / Settings
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py         — ロギングセットアップ（stdout + 日次ファイルローテーション）
    - process_priority.py      — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (注: 実装がある場合)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
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
  - data/  (runtime に生成される想定)
    - *.db (例: monitoring.db, paper_trading.db)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/  (デフォルトログディレクトリ)

（上記は主要ファイルの抜粋です。実際のリポジトリ全体はこれ以外のモジュールも含みます）

---

## 開発・運用上の注意

- 環境自動ロード
  - `config.py` はプロジェクトルート（.git または pyproject.toml を探索）を検出できれば自動で `.env` と `.env.local` を読込みます。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Python バージョン
  - 型注釈などで `X | Y` を使用しているため Python 3.10 以上を想定しています
- ログ
  - `kabusys.utils.logging_setup.setup_logging` を起動スクリプトで呼び出して統一的にログを管理しています。ログディレクトリ作成に失敗した場合は標準出力のみで継続します。
- OpenAI
  - AI 機能を利用する場合は `OPENAI_API_KEY` を必ず設定してください。API エラー時はフェイルセーフとしてスコアを 0 にフォールバックする設計です。
- 本番運用
  - `KABUSYS_ENV=live` の場合は特に LINE 通知設定等を確認してください（`validate_config` は本番向けの追加警告を出します）。
  - `KILL_FLAG_CLEAR_ON_START=1` は本番では慎重に扱ってください（自動クリアは危険な場合があります）。

---

## よく使うコマンドまとめ

- 環境ウィザード: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はこのコードベースの主要な使い方と構成をまとめたものです。詳細な API やモジュール間の呼び出し関係、戦略仕様（PortfolioConstruction.md, StrategyModel.md 等）が別途存在する前提です。質問や追加のドキュメント生成が必要であれば教えてください。