# KabuSys

日本株向け自動売買システムのコアライブラリ群（リサーチ、ポートフォリオ構築、実行、監視、AI補助など）。

このリポジトリは実稼働を想定した設計が散りばめられており、ローカル開発 / ペーパートレード / 本番（live）環境を環境変数で切り替えて使用できます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要機能を提供します。

- ファクター計算・リサーチ（DuckDB を使った時系列計算）
- ポートフォリオ構築（候補選定・重み計算・株数計算）
- 実行エンジン（ブローカー抽象化、ペーパートレード用の分離 DB）
- 監視エンジン（システム健全性、注文の滞留、リスク制御、Kill Switch）
- AI 補助（ニュースの NLP スコアリング、レジーム判定）
- 運用用 CLI（環境設定ウィザード・設定検証・レポート生成）

設計上の注意点：
- DuckDB / SQLite をデータレイヤに使用。分析と監視はファイル DB に永続化します。
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV=paper_trading の場合に専用 SQLite を使用）。
- OpenAI（gpt-4o-mini 等）を用いた NLP モジュールは API キーが必要です。API 失敗時はフェイルセーフになります。

---

## 主な機能一覧

- kabusys.research
  - calc_momentum / calc_volatility / calc_value：ファクター計算（DuckDB 接続を受け取る）
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析・IC 計算
- kabusys.portfolio
  - select_candidates, calc_equal_weights, calc_score_weights：候補選定・重み計算
  - calc_position_sizes：株数決定（リスクベース / 等配分 等）
  - apply_sector_cap, calc_regime_multiplier：セクター制限・レジーム乗数
- kabusys.ai
  - score_news：ニュースを LLM でスコアリングして ai_scores テーブルへ書込
  - regime_detector.score_regime：MA とマクロニュースを合成して市場レジーム判定
- kabusys.execution
  - ExecutionEngine 等（ブローカーファクトリ経由で本番/モック切替）
- kabusys.monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine：監視とアラート
  - KillSwitch：フラグファイルによる強制停止（Execution の安全装置）
  - monitoring_db：監視用 SQLite スキーマと永続化 API
- utils
  - logging_setup：統一ログ設定（stdout + 日次ローテーション）
  - process_priority：プロセス優先度 / CPU affinity 設定ユーティリティ
- CLI / ツール
  - config_setup：.env の対話式ウィザード
  - validate_config：環境変数・config/*.yaml の事前検証
  - tools.paper_verification_report：ペーパートレード検証レポート生成

---

## セットアップ手順

前提:
- Python 3.10+（typing の union タイプ等を使用）
- DuckDB, psutil, OpenAI SDK 等が必要

1. リポジトリをクローン / チェックアウト

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - PyYAML は設定検証（config/*.yaml のパース）を行う場合に必要: pip install PyYAML
   - （任意）その他の依存は開発環境に応じて追加してください

4. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを設定します
   - 生成された `.env` は Git にコミットしないでください

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は表示に従って `.env` や設定ファイルを修正してください
   - --strict を付けると警告も FAIL 扱いになります

6. データ・ログディレクトリ作成（通常は自動作成されますが先に用意しておくと安全）
   - mkdir -p data logs

---

## 環境変数（主なもの）

- KABUSYS_ENV: 実行環境
  - development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、実行エンジンは MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に書きます
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で利用、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（本番では 0 推奨）

---

## 使い方（主要スクリプト / CLI）

- 環境ウィザード（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密検証: python -m kabusys.validate_config --strict

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明:
    - プロセス優先度を high に設定
    - Settings から sqlite_path / duckdb_path を読み DB 初期化
    - SystemMonitor を初期化してポーリングを繰り返す
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能
    - 監視は常に Settings.sqlite_path（本番 sqlite）を参照する（KABUSYS_ENV に依存しない）
    - 停止: プロジェクトルート/data/stop_requested.flag を作成するとループ終了

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録
    - PID ファイル: data/execution.pid（デフォルト）
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 終了は kill.flag と stop_requested.flag による制御を併用

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを明示的に指定できます（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- プログラム的な利用例（AI スコア付与）
  - Python から呼び出す例:
    - import duckdb
    - from kabusys.ai import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,10), api_key="sk-...")

---

## 運用上のポイント

- ロギング
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトで呼び出しています
  - ファイルログは logs/<app_name>.log に日次ローテーション（30日分保持）
  - LOG_DIR 環境変数でログ保存先を変更可能

- Kill Switch / 停止フラグ
  - KillSwitch は条件（ドローダウン超過等）で data/kill.flag を書き込み、ExecutionEngine に停止を促します
  - 手動停止用フラグ: data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアしますが、本番では危険なため 0 推奨

- DB 分離
  - 監視ログ（monitoring）は Settings.sqlite_path（デフォルト data/monitoring.db）を使用
  - ペーパートレードは data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に完全分離して記録されます

- PS / CPU 優先度
  - 起動スクリプトは set_process_priority("high") を試みます（権限や OS により失敗する可能性あり）
  - psutil を利用しており、対応外 OS では設定がスキップされます

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_monitoring.py
    - run_execution.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
    - tools/
      - paper_verification_report.py

（上記は主要モジュールの抜粋です。実際のツリーはリポジトリ内のファイル一覧を参照してください）

---

## 注意事項 / ベストプラクティス

- 本番環境 (KABUSYS_ENV=live) では、LINE 通知等の設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は本番に関する警告を出します。
- .env や API キーは絶対に Git にコミットしないでください。
- DuckDB / SQLite ファイルへのバックアップ・ローテーション方針を検討してください（特に本番の分析 DB）。
- OpenAI 等の外部 API を使う処理はコストとレイテンシに注意。API キーとレート制限に依存します。
- 監視ループや実行エンジンの停止は stop_requested.flag を用いると安全です。kill.flag は自動的に書かれる可能性があるため運用ルールを作成してください。

---

README は必要に応じて追記・調整してください。追加で「インストール用 requirements.txt の提案」や「具体的な config/*.yaml の説明」「各モジュールの API ドキュメント生成」などを望む場合はその旨を教えてください。