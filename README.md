# KabuSys

日本株向け自動売買フレームワーク（プロジェクト骨格の一部）。  
この README はリポジトリ内の主要スクリプト・モジュールを基に作成した利用ガイド兼参照です。

注意: 実際に運用する前に `.env` を適切に設定し、`python -m kabusys.validate_config` で検証してください。

---

## プロジェクト概要

KabuSys は日本株の自動売買／バックテスト／監視を想定したコンポーネント群です。主に以下の役割を持つモジュールで構成されています。

- Execution（ExecutionEngine 等）: 注文の送信・管理・リスク管理
- Monitoring（System/Trade/Risk Monitor）: システム状態・取引ログ・リスクの監視とアラート、Kill Switch
- Research / Portfolio: ファクター計算、ポートフォリオ構築・サイズ決定、リスク調整
- AI 支援: ニュースの NLP スコアリング、レジーム判定（OpenAI 利用）
- ツール: Paper Trading の検証レポート等
- 設定ユーティリティ: .env ウィザード（config_setup）、設定検証（validate_config）

実行スクリプトはモード（開発 / ペーパートレード / 本番）に応じて挙動を切り替えます。

---

## 主な機能一覧

- ExecutionEngine 起動スクリプト（run_execution）:
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、ペーパートレード用 DB に記録（本番 DB と分離）。
  - プロセス優先度設定、PID ファイル管理、停止フラグによる安全停止。
- Monitoring（run_monitoring / MonitoringEngine）:
  - システムリソース監視（CPU/MEM/DISK）、データ鮮度チェック、Execution プロセス生存確認。
  - Trade / Risk の定期チェック、Kill Switch（重大リスク時に kill.flag を作成）と通知連携。
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
- データ永続化:
  - SQLite（監視用）と DuckDB（時系列・分析用）を使用。テーブル初期化用ユーティリティあり。
- Research / Portfolio:
  - モメンタム・バリュー・ボラティリティ等のファクター計算、ファクターと将来リターンの解析（IC 等）。
  - 候補選定、等重／スコア加重、リスクベースのポジションサイズ計算、セクター制限等。
- AI モジュール:
  - OpenAI を用いたニュースのセンチメントスコア（ai_scores）生成（news_nlp）。
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（regime_detector）。
  - API 呼び出しはリトライや結果バリデーションを行い、失敗時はフェイルセーフ動作。
- ツール:
  - Paper Trading の検証レポート（tools/paper_verification_report.py）
- 設定管理:
  - 対話式ウィザードで `.env` を生成（config_setup）。
  - 設定チェック CLI（validate_config）で起動前に設定不備を検出。

---

## セットアップ手順（開発用・最小）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - SQLite は標準ライブラリで利用可能です。

   ※ 実際の requirements.txt がある場合はそちらを使用してください。

3. `.env` を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で `.env` を作成（リポジトリルート）。主要変数は下記参照。

4. 設定検証
   - python -m kabusys.validate_config
   - 必要なら `--strict` を付けて警告もエラー扱いにする。

5. データディレクトリの作成（ログや DB 用）
   - デフォルトでは `data/`（SQLite / DuckDB）と `logs/` に書き込みが行われます。
   - 必要に応じて `.env` の `DUCKDB_PATH` / `SQLITE_PATH` を設定。

---

## 主要な環境変数（代表）

- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（省略可）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイル（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動で .env を読み込ませない（1 をセット）

.env 生成時の主なキー例（抜粋）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token_here
- KABU_API_PASSWORD=your_password_here
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- LOG_LEVEL=INFO
- KILL_FLAG_CLEAR_ON_START=0

---

## 使い方（よく使うコマンド）

- 環境ウィザード（.env の作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB に記録し MockBrokerClient を利用。
    - 起動時に PID ファイル（data/execution.pid など）を管理。
    - data/stop_requested.flag が存在する場合は起動をスキップまたは停止。

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で指定可能。
  - 監視は常に本番用 sqlite_path（SQLITE_PATH）を使用してログを残します（環境に依らない）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- ログ設定
  - 各起動スクリプトは共通の setup_logging を使用します。ログは stdout と日次ローテートされたファイル（logs/<app>.log）に出力されます。

停止／Kill フラグの運用
- data/stop_requested.flag:
  - run_execution / run_monitoring のループを検出して安全に終了させるための外部停止フラグ（存在確認のみ）。
- data/kill.flag:
  - KillSwitch がリスク検出時に書き込むファイル。ExecutionEngine 側は存在を検出して停止します。
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag をクリアします（本番では 0 を推奨）。

---

## ディレクトリ構成（主要ファイル）

リポジトリの `src/kabusys/` 以下（抜粋）:

- __init__.py
- config.py
  - .env の自動ロード、Settings クラス（環境設定の抽象化）
- config_setup.py
  - 対話式 .env ウィザード
- validate_config.py
  - 起動前の設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - Monitoring 起動スクリプト

- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

- monitoring/
  - monitoring_db.py — SQLite テーブル初期化 / 操作ラッパー
  - system_monitor.py — CPU/MEM/DISK・データ鮮度・プロセス監視
  - trade_monitor.py — （コード中に含まれるはずの取引監視）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成・検査
  - monitoring_engine.py — 各 Monitor を束ねる

- execution/
  - ExecutionEngine, OrderManager, OrderRepository, BrokerClientFactory, Reconciler, RiskManager 等（起動時に組み立てられます）

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー等
  - feature_exploration.py — forward returns / IC / 統計サマリー

- ai/
  - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores に書込む
  - regime_detector.py — ETF MA + マクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- data/
  - （実行時に生成されることを想定）monitoring DB / paper_trading DB / PID/flag ファイル等

---

## 開発上の注意点・運用上のガイダンス

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリアを無効（KILL_FLAG_CLEAR_ON_START=0）にし、LINE 通知等のアラート設定を必ず確認してください。
- run_monitoring は監視ログを本番 sqlite に記録します（環境に関係なく sqlite_path を使用）。監視データは運用判断に使うため消失に注意してください。
- OpenAI 関連の機能は API キー（OPENAI_API_KEY）が必要です。API 呼出しはリトライやパース検証を実施しますが、コスト・レイテンシを考慮し運用してください。
- データベーススキーマのマイグレーションは簡易的な追加カラム対応を行う箇所があります（monitoring_db.init_monitoring_db）。より大規模な変更時は注意が必要です。
- process_priority を高に設定する処理がありますが、OS 権限により失敗する場合がある（警告ログでスキップ）。

---

## 参考コマンドまとめ（例）

- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

もし README に追加してほしい内容（例:詳細な .env サンプル、systemd / Supervisor 用の起動スクリプト例、Dockerfile、要求パッケージの pinned requirements.txt など）があれば教えてください。必要に応じて追記します。