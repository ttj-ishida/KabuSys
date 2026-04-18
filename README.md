# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ + 起動スクリプト群）。

この README はリポジトリ内の主要スクリプト・モジュールの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

## 概要

KabuSys は次のような責務を持つモジュール群で構成されています。

- 実行（ExecutionEngine）: 発注・注文管理・リスク管理を行うエンジン
- 監視（Monitoring）: システム健全性、注文・リスクの監視、Kill Switch 発動
- ポートフォリオ構築（Portfolio）: 候補選定、重み付け、ポジションサイズ計算等
- リサーチ（Research）: ファクター算出、特徴量解析、IC 計算等（DuckDB を利用）
- AI モジュール（ai）: ニュースの NLP スコアリング、レジーム判定（OpenAI API）
- ユーティリティ: 環境設定ウィザード、設定検証、ログ設定、プロセス優先度設定 など
- ツール: ペーパートレード検証レポート生成スクリプト等

設計思想として、本番 DB とペーパートレード DB を分離し、安全性（Kill Switch、監視ログ等）を重視しています。
DuckDB は主にリサーチ/分析用途、SQLite は監視や発注ログの永続化に使われます。

## 主な機能

- ExecutionEngine 起動スクリプト（run_execution）:
  - KABUSYS_ENV に応じて本番 / Paper Trading を切替
  - Broker クライアントの抽象化（Mock を含む）
  - 発注履歴・ポジションの永続化（SQLite）
- Monitoring（run_monitoring / MonitoringEngine）:
  - CPU/メモリ/ディスク・プロセス稼働・データ鮮度監視
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch 書き込みによる安全停止
  - 通知管理（LINE 等の設定を使用）
- Portfolio モジュール:
  - 候補選定（スコア順）、等比重/スコア加重、ポジションサイズ計算（リスクベース含む）
  - セクターキャップ、レジーム乗数の適用
- Research:
  - momentum / volatility / value などのファクター算出（DuckDB + SQL）
  - forward returns / IC / 統計サマリ
- AI:
  - ニュースを LLM（gpt-4o-mini 等）でスコアリングして ai_scores に書き込み
  - マクロニュース + ETF(1321) MA200 乖離を用いた市場レジーム判定
- ツール:
  - config_setup: .env を対話式に生成/更新
  - validate_config: 起動前に環境変数・config/*.yaml を検証
  - paper_verification_report: ペーパー取引の検証レポート生成

## 必要要件（主な依存パッケージ）

最低限の Python ライブラリ（例）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML （config ファイルの詳細検証を行う場合に必要）

インストール例:

pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt/poetry 等があればそれに従ってください）

## セットアップ手順

1. リポジトリのルートに移動して Python 仮想環境を作成・有効化する
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは上記の手動インストール

3. .env を作成（推奨: 対話式ウィザードを使用）
   - python -m kabusys.config_setup
   - もしくは .env を手動で作成（下記に主要な環境変数を参照）

4. 設定検証
   - python -m kabusys.validate_config
   - 起動前にエラー/警告を確認してください。--strict をつけると警告も失敗扱いになります。

5. データディレクトリ
   - デフォルトでは以下のファイル/ディレクトリを使用します（存在しない場合は自動作成される箇所がありますが、権限に注意してください）
     - data/monitoring.db（SQLite）
     - data/paper_trading.db（Paper Trading 用 SQLite）
     - data/kabusys.duckdb（DuckDB）
     - logs/ （ログ保存先）
     - data/execution.pid, data/stop_requested.flag, data/kill.flag（PID/停止フラグ）

6. OpenAI を使う機能を使用する場合
   - 環境変数 OPENAI_API_KEY を設定する（または関数呼び出し時に渡す）
   - AI 機能は API 通信を行います。API レートや料金に注意してください。

## 主要な環境変数（抜粋）

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境切替 / ログ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）

- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

- Paper Trading / Mock 設定
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）

- Kill / PID
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 1|0（本番では 0 推奨）

- OpenAI
  - OPENAI_API_KEY（AI 機能を使う場合必須）

注意: .env 自動読み込みはプロジェクトルート（.git or pyproject.toml を探索）を基準に行われます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## 使い方（コマンド例）

プロジェクトルート（pyproject.toml/.git があると自動 .env ロードが動きます）で実行してください。

- 環境ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine を起動（デフォルト: KABUSYS_ENV に従う）
  - python -m kabusys.run_execution
  - 停止: data/stop_requested.flag を作成することで起動済みループを停止できます（システム内の停止フラグの取り扱いに従ってください）。
  - Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定（または .env に設定）

- Monitoring を起動（ポーリング）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒。デフォルト 60）
  - python -m kabusys.run_monitoring
  - 監視は環境にかかわらず本番 sqlite_path を参照する点に注意してください（監視ログは共通 DB）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI モジュール（スクリプト経由の例）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定してから、各モジュール関数を呼び出すか、提供されている CLI を使います（現状は API 呼び出しを行う Python モジュール経由の利用が想定されています）。

## 停止・Kill Flow（安全停止）

- stop_requested.flag (data/stop_requested.flag)
  - run_execution.py / run_monitoring.py が参照する「停止要求フラグ」です。ファイルの有無を監視し、存在するとループを終了します。

- kill.flag (data/kill.flag)
  - KillSwitch（監視側）がリスク閾値を超えた場合に書き込むファイルです。ExecutionEngine 側でこのフラグを検出し停止する設計になっています。

- PID ファイル
  - data/execution.pid に ExecutionEngine の PID を書きます（プロセス管理用）。

## ディレクトリ構成

リポジトリ（src/kabusys）内の主要ファイル・ディレクトリの説明:

- src/kabusys/
  - __init__.py (パッケージ情報)
  - config.py (環境変数 / 設定ラッパ)
  - config_setup.py (.env 対話式ウィザード)
  - validate_config.py (起動前検証 CLI)
  - run_execution.py (ExecutionEngine 起動スクリプト)
  - run_monitoring.py (SystemMonitor ポーリング起動スクリプト)

- src/kabusys/execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - 発注・注文管理・リスク制御に関する実装（ExecutionEngine の中核）

- src/kabusys/monitoring/
  - monitoring_db.py (SQLite テーブル初期化 / DB ラッパ)
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
  - 監視・KillSwitch・アラート関連（MonitoringEngine が各 Monitor を束ねる）

- src/kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
  - 候補選定、重み付け、株数計算、セクター制限等

- src/kabusys/research/
  - factor_research.py, feature_exploration.py
  - DuckDB を用いたファクター計算・将来リターン・IC 等

- src/kabusys/ai/
  - news_nlp.py (ニュース NLP スコアリング)
  - regime_detector.py (市場レジーム判定)

- src/kabusys/tools/
  - paper_verification_report.py（ペーパートレード検証レポート）

- src/kabusys/utils/
  - logging_setup.py（統一ログ設定）
  - process_priority.py（プロセス優先度 / CPU affinity）
  - など

- data/ （実行時に使用されるファイル）
  - monitoring.db（SQLite）
  - paper_trading.db（ペーパートレード用 SQLite）
  - kabusys.duckdb（DuckDB）
  - execution.pid, stop_requested.flag, kill.flag（制御用フラグ／PID）

- logs/（ログファイル出力先。setup_logging により作成される）

（上記は主要構成の抜粋です。実際のファイルはリポジトリを参照してください）

## 運用上の注意点

- 本番（KABUSYS_ENV=live）での運用時は .env に機密情報を絶対にコミットしないでください。
- KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します（1 にすると起動時に既存の Kill フラグが自動で消えてしまいます）。
- run_monitoring は監視 DB に対して本番 sqlite_path を使用します（環境に依存せず本番監視を行う設計）。
- AI 機能は API レートやコストの影響を受けます。OpenAI の利用は運用ポリシーに従ってください。
- DuckDB/SQLite のファイルパスは .env で上書き可能です。バックアップ・永続化戦略を検討してください。

---

この README はコードベースの主要点を抜粋したものです。詳細な設計・利用方法は各モジュールの docstring やソースコードのコメントを参照してください。追加で README に含めたい項目（例: サンプル .env.example、デプロイ手順、systemd ユニットファイル例など）があれば教えてください。