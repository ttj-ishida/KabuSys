# KabuSys

日本株向けの自動売買 / 研究フレームワーク（モジュール群）のリポジトリです。  
本リポジトリは、Execution エンジン（発注処理）・Monitoring（監視）・Research（ファクター計算）・AI（ニュースセンチメント/レジーム判定）などの主要コンポーネントを含みます。

## 概要
- 実運用を想定した設計で、発注ロジックと監視・キルスイッチを備えています。
- Paper trading（ペーパートレード）用に本番 DB と分離された振る舞いをサポートします。
- DuckDB を使った分析・ファクター計算、OpenAI を使ったニュース NLP 判定機能を持ちます。
- ロギング・プロセス優先度設定・DB マイグレーション等のユーティリティを含みます。

## 主な機能一覧
- Execution（発注）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化（paper/live の分岐）
  - リスク管理（RiskManager）、注文管理（OrderManager）など
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせた MonitoringEngine
  - kill.flag / stop フラグによる安全停止、監視ログの永続化（SQLite）
  - アラート管理（LINE などの通知連携は設定次第）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターンの計算、IC 計算、統計サマリー
- AI
  - ニュースを OpenAI に渡して銘柄ごとのセンチメントを算出（ai_scores テーブルへ保存）
  - マクロニュース + ETF MA200 を合わせた市場レジーム判定
- ツール
  - .env 対話ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- ユーティリティ
  - ログ設定（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）
  - 設定管理（config.py）：.env 自動読み込み、Settings クラス

## 要件（推奨）
- Python 3.10+
- 必要な Python パッケージ（プロジェクト使用パッケージの一例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - pyyaml（設定ファイルの検証を行う場合 / validate_config での検証に使用）
- SQLite（Python 標準ライブラリに含まれます）

※ 実行環境に合わせて requirements.txt を用意してインストールしてください。

## セットアップ手順（ローカル開発環境向け）
1. リポジトリをクローンして、作業ディレクトリに移動
2. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai pyyaml
4. 設定ファイル（.env）の作成
   - 対話ウィザードを実行して .env を生成:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照して必要な環境変数を設定）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告を厳密扱いにする場合: python -m kabusys.validate_config --strict
6. データディレクトリの確認
   - デフォルト DB/ログ/flag パスは以下を参照（必要に応じて .env で変更）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper-trading SQLite: data/paper_trading.db
     - PID / stop / kill flag: data/execution.pid, data/stop_requested.flag, data/kill.flag
     - ログディレクトリ: logs/

## 環境変数（主要なもの）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト `development`
  - paper_trading の場合は MockBrokerClient を使用し paper_sqlite_path に記録される
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（monitoring）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必要）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒）。run_monitoring で上書き可能（デフォルト 60秒）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（詳細は config.py を参照）

注意:
- run_monitoring（監視）は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番 monitoring DB）を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離します。

## 使い方（主要コマンド）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag ファイルを作成するとループは終了します。kill.flag は Execution 停止用（下記）
- Execution 起動（発注エンジン）
  - python -m kabusys.run_execution
  - Paper trading モード（MockBrokerClient を使用）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止: data/stop_requested.flag を作成することで実行中エンジンに停止シグナルを送ります。
  - kill.flag を Monitoring 側から書き込むと ExecutionEngine に停止要求が送られます（KillSwitch 経由）。
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定可
- AI モジュール（プログラム的に呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb 接続
    - api_key を省略した場合は環境変数 OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 停止 / Kill フロー
- data/stop_requested.flag
  - run_monitoring / run_execution のループを安全に停止させるためのフラグファイル。存在を検知するとループを終了します。
- data/kill.flag
  - KillSwitch が条件を満たしたときに書き込まれるファイル。ExecutionEngine の停止トリガーとなります。
- PID ファイル
  - run_execution は data/execution.pid にプロセス PID を書き込みます（設定により変更可能）。

## ログ
- ログはデフォルトで logs/ ディレクトリに日次ローテートで保存されます（TimedRotatingFileHandler）。
- 各起動スクリプトは setup_logging(app_name=...) を呼んで統一的にログ出力します。
  - 例: logs/execution.log, logs/monitoring.log

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュールの一覧と簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — ログ初期化ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視ログ永続化層
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — （注文関連監視）※実装参照
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — Kill 判定・flag 書き込み
    - monitoring_engine.py — モニタ群を束ねるエンジン
    - alert_manager.py — アラート送信管理（LINE 連携等は設定次第）
  - execution/
    - execution_engine.py — 発注セッションの実行ロジック
    - broker_factory.py — ブローカークライアント生成（mock/live 切替）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注管理に関するコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・配分スコア操作
    - position_sizing.py — 株数算出・単元丸め・キャップ処理
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - ai/
    - news_nlp.py — OpenAI を使ったニュースセンチメント処理（ai_scores 書き込み）
    - regime_detector.py — マクロニュース + ETF MA200 を使って日次レジーム判定
  - tools/
    - paper_verification_report.py — Paper trading の検証レポート生成スクリプト

（上記は主なファイルのみ抜粋。詳細は src/kabusys 以下のソースを参照してください）

## 開発上の注意事項 / 備考
- .env は機密情報（API キー等）を含むため、絶対にバージョン管理にコミットしないこと。
- run_monitoring は Settings.sqlite_path（本番監視 DB）を常に使用します。監視と発注の DB 設計に注意してください。
- AI 機能を使用する場合は OpenAI API の利用制限・コストを確認してください。API 失敗時のフェイルセーフ実装（デフォルトスコアやスキップ）がありますが、運用時は注意が必要です。
- DuckDB 上のテーブル（prices_daily / raw_financials / raw_news など）は Research/AI モジュールで参照されます。必要なスキーマ・データを事前に投入してください。
- process_priority 設定やログディレクトリ作成に失敗するケースがあるため、監視・実行スクリプトはその場合でもフォールバックして動作するよう設計されています。

---

質問や README に追加してほしいコマンド例・環境変数の詳細があれば教えてください。README を用途（運用者向け / 開発者向け）に合わせて調整できます。