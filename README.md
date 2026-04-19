# KabuSys

日本株向け自動売買システムのコードベース。ポートフォリオ構築、注文実行（実口座／ペーパートレード対応）、監視、研究用ファクター計算、ニュースNLP 等のモジュールを含みます。

## プロジェクト概要
KabuSys は次を目的としたモジュール群を提供します。

- 戦略（ファクター計算・特徴量解析）とポートフォリオ構築
- 注文実行（実口座 ↔ ペーパートレード切替）
- 実行状態・注文・リスクの監視（Kill Switch を含む）
- ニュースを用いた AI スコアリング（OpenAI API）
- 運用支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート等）

設計上のポイント:
- 設定は環境変数 / .env で管理（自動読み込み機能あり）
- 本番 DB（SQLite）・分析 DB（DuckDB）を併用
- ペーパートレードは本番 DB と完全に分離（data/paper_trading.db）
- ロギングは統一的に設定（stdout + 日次ローテーションファイル）

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて MockBroker / 実ブローカーを自動選択
  - paper_trading 時は専用 SQLite を使用
  - PID ファイル管理 / stop フラグ対応
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor をポーリングし監視ログを保存
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能
- モニタリング DB 層（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブル
  - マイグレーション（カラム追加）を含む初期化処理
- リスク監視 / Kill Switch（risk_monitor.py, kill_switch.py）
  - ドローダウン閾値・ポジション数超過を検出し kill.flag を出力
- MonitoringEngine（monitoring_engine.py）
  - 各 Monitor をまとめて定期実行、アラート発行の統合
- ポートフォリオ構築・サイズ決定（portfolio パッケージ）
  - 候補選定、等金額・スコア重み、リスク調整、単元株丸め等
- 研究用モジュール（research パッケージ）
  - ファクター計算（モメンタム／ボラ／バリュー等）、IC 計算、統計サマリ
- AI 関連（ai パッケージ）
  - ニュース NLP（OpenAI でセンチメント評価）および市場レジーム判定
  - OpenAI API キー必須（環境変数 `OPENAI_API_KEY` または引数で指定）
- ユーティリティ
  - logging_setup（統一ログ設定）
  - process_priority（プロセス優先度 / CPU affinity 設定）
- ツール
  - config_setup: 対話式 .env ウィザード（python -m kabusys.config_setup）
  - validate_config: 起動前に設定を検証（--strict オプションあり）
  - paper_verification_report: ペーパートレードの検証レポート生成

## セットアップ手順（ローカル開発向け / 概要）
1. リポジトリをクローン／展開
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必須例: duckdb, psutil, openai
   - オプション: PyYAML（config 検証で YAML パースを行う場合）
   - 例:
     - pip install -r requirements.txt
     - （requirements.txt がない場合は個別に）pip install duckdb psutil openai pyyaml
4. 必要ディレクトリ作成
   - data/ と logs/ を作成しておくと良い:
     - mkdir -p data logs
5. .env を用意
   - `python -m kabusys.config_setup` を実行すると対話式に .env を生成できます。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（デフォルト値あり）:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH (例: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB, 例: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード用 DB, 例: data/paper_trading.db)
     - LOG_LEVEL (例: INFO)
     - OPENAI_API_KEY（AI 機能を使う場合に必須）
6. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする場合: python -m kabusys.validate_config --strict

## 使い方（主要な実行例）
- ExecutionEngine（注文実行）を起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で制御:
    - paper_trading: MockBroker を使用し data/paper_trading.db に記録
    - live: 実ブローカーを使用（要注意）
  - 停止方法:
    - data/stop_requested.flag を作成すると起動中のループが検知して停止します
- Monitoring（監視）を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用してログを保存します
- .env 設定ウィザード
  - python -m kabusys.config_setup
- 設定の静的検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗（exit code 1）扱い
- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを直接指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定するか、関数引数で渡す必要があります
  - モジュール関数:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 停止・Kill Switch の仕組み
- kill.flag（Settings.kill_flag_path、デフォルト: data/kill.flag）:
  - KillSwitch が条件を満たすとこのファイルを書き込み、ExecutionEngine に停止シグナルを送ります
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると自動クリアされる設定があります（本番では 0 推奨）
- stop_requested.flag:
  - run_execution / run_monitoring のスクリプトは data/stop_requested.flag の存在を検知して安全停止します

## ロギング
- ログは stdout（StreamHandler）に出力され、かつ logs/<app_name>.log に日次ローテーションで保存されます
- ログディレクトリやレベルは環境変数で上書き可能:
  - LOG_DIR（ログ保存先ディレクトリ）
  - LOG_LEVEL（例: DEBUG / INFO）

## 主要な環境変数（まとめ）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用・挙動制御:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）

ペーパートレード固有:
- PAPER_FILL_MODE: instant|partial|never|reject（デフォルト: instant）

Kill Switch / 起動フラグ:
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 1 なら起動時に kill.flag を自動クリア（本番では 0 推奨）

## ディレクトリ構成（抜粋）
プロジェクトルート配下の src/kabusys を想定。主要ファイル／サブパッケージ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の自動読み込みと Settings クラス
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — 監視用 SQLite 永続化層
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — 注文・取引監視（存在）
    - risk_monitor.py        — ドローダウン等のリスク監視
    - kill_switch.py         — Kill Switch 実装
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - alert_manager.py       — アラート送信（LINE 等、存在）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig, run_session）
    - broker_factory.py      — ブローカクライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
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
  - tools/
    - paper_verification_report.py

（注）実際のファイル一覧はリポジトリにより多少異なる可能性があります。上は主要モジュールの抜粋です。

## 開発上の注意点
- 本番（KABUSYS_ENV=live）での起動前には必ず `python -m kabusys.validate_config --strict` で設定を検証してください。
- .env は絶対に VCS にコミットしないでください（config_setup 生成ヘッダにもその旨を記載）。
- AI 機能は外部 API（OpenAI）に依存するため、API 呼び出し失敗時のフォールバック挙動を理解してください（多くはロギングして継続する設計です）。
- ペーパートレードは本番データベースと分離されています。運用前に PAPER_TRADING_SQLITE_PATH を確認してください。

---

README に不足している具体的な実行引数や内部 API の詳細が必要であれば、用途別（デプロイ手順、systemd/cron 用のユニットファイル例、環境ごとの推奨設定等）に追加で作成します。どの情報を優先して追記しますか？