# KabuSys

日本株向け自動売買システムのコアライブラリ（README 日本語版）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買／研究用途に使えるモジュール群です。  
主に以下を提供します：

- データ処理・研究（DuckDB を用いたファクター計算、特徴量・IC解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- 実行系（ExecutionEngine、ブローカークライアントの抽象化、ペーパートレード対応）
- 監視系（System / Trade / Risk の監視、Kill Switch、監視 DB）
- AI 支援（ニュースの NLP スコアリング、レジーム判定）
- 各種 CLI ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として、ルックアヘッドバイアスを避ける・本番 DB とペーパートレード DB を分離する・外部 API 呼び出しはフェイルセーフで止めない（失敗時はフォールバック）、といった点に配慮しています。

---

## 主な機能一覧

- 環境設定ウィザード（`.env` 自動生成 / 更新） — `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の基本チェック） — `kabusys.validate_config`
- 実行エンジン起動スクリプト（本番 / paper_trading 切替） — `run_execution.py`
  - paper_trading 時は mock broker を使い、別 DB（`data/paper_trading.db`）に記録
- 監視ループ起動スクリプト（SystemMonitor のポーリング） — `run_monitoring.py`
  - ポーリング間隔は `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- 監視 DB（SQLite）永続化レイヤー（system_status / trade_logs / positions / risk_logs / dashboard）
- RiskMonitor（ドローダウン／ポジション上限監視）と KillSwitch（`data/kill.flag`）連携
- Portfolio モジュール（候補選定、等重/スコア重み、ポジションサイズ計算、セクター上限）
- Research モジュール（momentum, volatility, value などのファクター計算、IC 計算）
- AI モジュール（ニュース NLP スコアリング / レジーム判定、OpenAI を利用）
- ツール: Paper Trading 検証レポート生成スクリプト

---

## 前提条件

- Python 3.10+
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（`validate_config` の YAML 検証に利用。無くても警告でスキップ）
- OS: Linux / macOS / Windows（ただし process priority / cpu affinity は OS に依存する挙動あり）

必要なパッケージはプロジェクトで管理されている要件ファイルがあればそちらを利用してください。

---

## セットアップ手順（概略）

1. リポジトリをクローンして仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. `.env` の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは必須項目（J-Quants トークン、kabu API パスワード等）を案内します。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱いたい場合は `--strict` を付与

5. データディレクトリの確認
   - デフォルト DB / ファイルパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じて `.env` で上書き

---

## 使い方（主要コマンド例）

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード: python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番 / paper_trading に応じて動作が切り替わる）
  - python -m kabusys.run_execution
  - 実行中に `data/stop_requested.flag` を作成すると安全に停止を促す（スクリプト内で使用）
  - paper_trading の場合は環境変数 KABUSYS_ENV=paper_trading を設定し、別 DB（PAPER_TRADING_SQLITE_PATH）へ記録

- Monitoring 起動（SystemMonitor のポーリングループ）
  - python -m kabusys.run_monitoring
  - ポーリング周期は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可。デフォルト: 60

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 関連（コード内 API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn は DuckDB 接続、api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill flag を自動クリアするか（0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（テスト用）

注意: `.env` は自動的に `.env` → `.env.local` の順で読み込まれます（OS 環境変数が優先）。テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 運用・監視に関する補助ファイル

- data/kill.flag : Kill Switch 用フラグ（KillSwitch が書き込む）
- data/stop_requested.flag : run_* スクリプトが停止を検知するためのフラグ
- data/execution.pid : ExecutionEngine の PID ファイル（設定に応じたパス）
- logs/<app_name>.log : 日次ローテートログ（TimedRotatingFileHandler; 既定 30日保持）

KillSwitch や stop flag による外部からの停止・運用制御を想定しています。運用時は `.env` の KILL_FLAG_CLEAR_ON_START 設定に注意してください（本番では 0 推奨）。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py — パッケージ定義（__version__ 等）
- config.py — 環境変数／設定管理（.env の自動読み込みロジック含む）
- config_setup.py — 対話式 .env ウィザード
- validate_config.py — 起動前設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM センチメント評価（score_news）
  - regime_detector.py — マーケットレジーム判定（score_regime）
- monitoring/
  - monitoring_db.py — SQLite 監視 DB 層
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — （注文監視ロジック）※（実装ファイルあり）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - alert_manager.py — （アラート送信管理）※（実装ファイルあり）
- execution/
  - execution_engine.py — 実行エンジンのコア（EngineConfig 等）
  - broker_factory.py — ブローカークライアントの生成
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 実行周辺サポート
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — ファクター計算（momentum/volatility/value）
  - feature_exploration.py — 将来リターン・IC 等
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py — ロギング統一設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- data/ （プロジェクトルートに想定されるディレクトリ）
  - monitoring.db（デフォルト）
  - paper_trading.db（paper_trading 用）
  - kabusys.duckdb（DuckDB）
  - stop_requested.flag / kill.flag / *.pid

（実際のファイルツリーはプロジェクト内容に応じて若干の差異がある場合があります）

---

## 開発者向けヒント

- ロギングは `kabusys.utils.logging_setup.setup_logging(app_name="...")` で統一的にセットアップします。デフォルトは stdout と日次ローテーションファイル出力です。
- Process priority / CPU affinity は `psutil` を用いて OS に依存した設定を行います。権限不足や未対応 OS の場合は警告を出してスキップします。
- DuckDB 接続は research / ai モジュールで使用されます。AI 処理は OpenAI API のレート制御やリトライを実装していますが、API キーは必ず安全に管理してください。
- paper_trading は本番 DB と完全分離される設計（`Settings.is_paper` が有効時に専用 SQLite を使用）です。
- `.env` は絶対にリポジトリへコミットしないでください（config_setup のヘッダにも注意喚起があります）。

---

## 参考コマンドまとめ（例）

- ウィザード: python -m kabusys.config_setup
- 検証: python -m kabusys.validate_config
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: python -m kabusys.run_monitoring
- ペーパートレード検証: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ライセンス / バージョン

- バージョン: src/kabusys/__init__.py にて `__version__ = "0.1.0"`
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

---

必要であれば README に具体的な .env 例や起動時ログの例、ユニットテストの実行方法、CI 設定などを追記できます。どの情報を優先して追加しますか？