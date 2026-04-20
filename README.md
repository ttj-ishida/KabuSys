# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買・リサーチ基盤の一部を実装した Python パッケージです。本リポジトリは、監視（Monitoring）、Execution（発注実行）、ファクター計算、ポートフォリオ構築、AI を使ったニュース分析などのユーティリティ群を提供します。

以下の README はこのコードベースの使い方・設定方法をまとめたものです。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）とそれを監視する Monitoring コンポーネントを中心に設計されています。
- Paper Trading（ペーパートレード）モードと Live（実運用）モードを切り替え可能。
- DuckDB / SQLite を用いたデータ保管・解析と、OpenAI を利用したニュースセンチメント分析モジュールを含みます。
- ログや PID / フラグファイルを通じてプロセス管理や安全停止（Kill Switch）を実現します。

---

## 主な機能一覧

- 設定管理
  - .env（.env.local）自動読み込み、対話式の .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

- 実行 / 監視
  - run_execution: ExecutionEngine を起動（paper_trading 時は MockBroker を使用し DB 分離）
  - run_monitoring: SystemMonitor 等を定期ポーリングして監視・アラート判定
  - kill.flag（Kill Switch）と stop_requested.flag による安全停止機構
  - PID ファイル / ログ設定（logs/ 日次ローテート）

- 監視 DB 層
  - monitoring_db: system_status / trade_logs / positions / risk_logs / dashboard の永続化、簡易マイグレーション

- リスク管理
  - RiskMonitor: ドローダウン・ポジション上限の検出と risk_logs 登録
  - KillSwitch: 重大条件での停止フラグ書き込み

- ポートフォリオ構築（純粋関数）
  - 候補選定、重み計算（等金額／スコア加重）
  - セクター上限適用、レジーム乗数
  - 発注株数計算（単元丸め、aggregate cap、risk-based 配分）

- リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索・IC 計算等

- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM で評価して ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロニュースを統合して市場レジーム判定

- ツール
  - paper_verification_report: Paper Trading の検証レポートを生成

---

## セットアップ手順

1. Python（3.9+ 推奨）を用意します。

2. 必要な Python パッケージをインストールします（代表的なもの）:

   ```
   pip install duckdb psutil openai pyyaml
   ```

   - OpenAI SDK は AI 機能を使う場合のみ必要です。
   - PyYAML は `validate_config` が YAML 検証を行う際に必要ですが、未インストールでも実行可能（警告が出ます）。

3. プロジェクトルートに `.env` を作成します（対話式ウィザードを推奨）:

   ```
   python -m kabusys.config_setup
   ```

   ウィザード後に `.env` が生成されます。`.env` は絶対に Git にコミットしないでください。

4. 設定検証:

   ```
   python -m kabusys.validate_config
   # 警告を厳格に扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ（デフォルト: `data/`）やログディレクトリ（`logs/`）が自動作成されますが、権限やパスに問題が無いか確認してください。

---

## 環境変数（主要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development

- データベース / ファイルパス
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: Execution の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグ（デフォルト: data/kill.flag）

- ログ
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs/）

- Monitoring
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

- Paper Trading
  - PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY: OpenAI を使う機能の API キー

- その他
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化します（テスト用途）。

注意: .env の自動読み込みはプロジェクトルートを .git または pyproject.toml で検出して行われます。`.env.local` は `.env` 上書き（優先）されます。

---

## 使い方（主な CLI / スクリプト）

- 設定ウィザード（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス（Monitoring）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を変更可能（デフォルト 60）。
  - 監視は Settings.sqlite_path を使用（Monitoring は環境にかかわらず本番 sqlite_path を参照します）。
  - 停止: プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して終了します。

- 実行エンジン（Execution）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し、`data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）に記録します（本番 DB と分離）。
  - 起動前に `data/stop_requested.flag` が存在する場合は起動しません。
  - 実行中に `data/stop_requested.flag` を作成するとエンジンへ停止シグナルが送られ、終了します。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 関連（プログラム的に呼び出す例）
  - ニューススコアリング:
    - duckdb 接続オブジェクトを作成して `kabusys.ai.score_news(conn, target_date, api_key=None)` を呼びます。
    - `OPENAI_API_KEY` または `api_key` 引数が必要です。
  - レジーム判定:
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 停止 / Kill Switch

- 手動完全停止（run_* スクリプト共通）:
  - `data/stop_requested.flag` を作成すると run_monitoring/run_execution が検知して終了します。

- Kill Switch（自動停止判定）:
  - Monitoring 側の条件（ドローダウン超過、ポジション上限超過など）で `data/kill.flag` が書き込まれます。
  - ExecutionEngine は起動時に `kill.flag` の存在を確認し、存在する場合は起動しません。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START` を 0 にすることを推奨します（自動クリアは危険）。

---

## ロギング

- 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging(app_name="...")` を通じて、
  - コンソール（stdout）出力
  - 日次ローテーション（`logs/<app_name>.log`）を設定します。
- デフォルトで 30 日分のログを保持します。
- ログディレクトリが作成できない場合はファイル出力をスキップしてコンソールのみで継続します。

---

## マイグレーション / DB 初期化

- `monitoring_db.init_monitoring_db(conn)` は必要なテーブルを冪等に作成し、既存 DB に対して簡易マイグレーション（`dashboard.peak_value` や `trade_logs.latency_ms` の追加）を行います。
- run_monitoring と run_execution は起動時にこの初期化を呼び出します。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の `src/kabusys` をルートとして抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (参照されるがここでは省略)
    - kill_switch.py
    - alert_manager.py (参照されるがここでは省略)
  - execution/
    - broker_factory.py (参照)
    - execution_engine.py (参照)
    - order_manager.py (参照)
    - order_repository.py (参照)
    - reconciler.py (参照)
    - risk_manager.py (参照)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/  (実行時に生成・利用)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag, stop_requested.flag, execution.pid など

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml

※ 一部ファイル（trade_monitor, alert_manager, execution/* 等）は README 作成時点で内部実装や参照のみのため、実運用では各モジュールの実装と依存関係を確認してください。

---

## よくある運用注意点

- Monitoring は常に Settings.sqlite_path（監視 DB）を参照します。実運用で Monitoring と Execution を分離したい場合はパス設定に注意してください。
- run_execution は paper_trading のときに専用 DB（PAPER_TRADING_SQLITE_PATH）を使い、本番 DB と完全に分離します。
- OpenAI を利用する AI モジュールは API コストとレートリミットに注意してください。エラー時はフォールバック動作（スキップ / 0.0）する設計です。
- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START=0`、`LINE` 関係の通知設定を適切に行うことを推奨します。
- .env の自動ロードはプロジェクトルート検出に依存します。パッケージ配布後の実行環境では適切に環境変数をセットしてください。

---

## 開発・テスト

- 多くの関数は副作用を持たない純粋関数として設計されており、ユニットテストがしやすい構造になっています（例: portfolio/*.py, research/*.py）。
- AI 呼び出し部分は `_call_openai_api` を patch することでテスト可能です。
- DB 周りは一時 SQLite / DuckDB ファイルを用いてテストできます。

---

以上がこのコードベースの主要な使い方と構成です。追加の詳細や各モジュールの使い方が必要であれば、特定のファイルや機能について更に README を拡張します。