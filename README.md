KabuSys
======

日本株向け自動売買システムのコードベース（ドキュメント版）。  
本 README はリポジトリ内の主要モジュールをもとに、導入・起動方法、機能・構成を日本語でまとめたものです。

概要
---
KabuSys は以下のような機能を備えた自動売買プラットフォームの一部実装です。

- 注文実行エンジン（ExecutionEngine）
  - 実際のブローカー接続／モック（ペーパートレード）に対応
  - 注文管理・リスク管理・リコンシリエーション
- 監視（Monitoring）
  - システム稼働性・データ鮮度・注文ログの監視
  - Kill Switch（危険検出時に Execution を停止するフラグ）
- ポートフォリオ構築（選定・配分・ポジションサイズ計算）
- リサーチ / ファクター計算（DuckDB を利用したファクター群）
- AI連携（OpenAI を用いたニュースセンチメント / レジーム判定）
- ツール群（ペーパートレード検証レポート等）
- 環境設定ウィザード / 設定検証 CLI

主な特徴
---
- 環境分離:
  - KABUSYS_ENV により development / paper_trading / live を切替可能
  - ペーパートレード時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離
- フェイルセーフ:
  - AI 呼び出しのリトライ（指数バックオフ）、API 失敗時のフォールバック実装
  - 監視モジュールで自動的に kill.flag を作成してエンジン停止が可能
- データストア:
  - DuckDB（分析・ファクター計算用）と SQLite（監視 / 発注ログ）を併用
- ロギング:
  - 共通の logging 設定を提供（コンソール + 日次ローテーションファイル）

セットアップ手順
---
1. リポジトリをクローンし、Python 仮想環境を作成・有効化する:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールする（一例）:
   - pip install duckdb psutil openai
   - もし YAML の検証を行うなら PyYAML を追加: pip install pyyaml
   - さらに必要に応じて開発用・テスト用ライブラリをインストール

   （リポジトリに requirements.txt がない場合は上記モジュールが最低限必要です）

3. .env の初期作成:
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env.example を参照）

4. 設定の検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります（exit code 1）

主要な環境変数（代表）
---
- 必須 (最低限)
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / 推奨
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: 分析 DB のパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB のパス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト: instant）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）で必要
  - LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- 監視・制御
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1: 自動クリア、デフォルト: 0 推奨）
  - KILL_FLAG_PATH / PID_FILE_PATH 等は Settings 経由で上書き可能

使い方（コマンド例）
---
- 環境作成ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動:
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading DB（デフォルト: data/paper_trading.db）に記録します。
    - 実行中に data/stop_requested.flag が存在すると起動を止めます。
    - 実行中に kill.flag (Settings.kill_flag_path) が書かれた場合はエンジンが停止されます。

- 監視プロセス起動:
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を参照して監視用テーブルを初期化します。
    - 停止は data/stop_requested.flag を作成することで行えます。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH でも DB を指定できます。

ロギング
---
- 共通の logging 設定は kabusys.utils.logging_setup.setup_logging で行います。  
  デフォルトではコンソール出力（stdout）と logs/<app_name>.log（日次ローテーション、30日保持）に出力します。
- LOG_LEVEL / LOG_DIR 環境変数で調整可能。ログディレクトリ作成に失敗した場合はコンソールのみで出力します。

停止フラグ / Kill Switch
---
- 手動停止用フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring の外部停止フラグ
- 自動停止（Kill Switch）:
  - monitoring モジュールがリスク（ドローダウン / ポジション上限など）を検出すると Settings.kill_flag_path（デフォルト: data/kill.flag）に理由を書き込んで ExecutionEngine に停止を通知します。
  - KillSwitch は冪等で、既にファイルが存在する場合は再書き込みしません。

AI（OpenAI）関連
---
- ai.news_nlp / ai.regime_detector は OpenAI API（モデル: gpt-4o-mini を想定）を呼び出してニュースセンチメントや市場レジームを評価します。
- 必要: OPENAI_API_KEY（環境変数または関数引数で指定）
- 仕様上、API の 429/ネットワーク断/5xx に対しては指数バックオフでリトライします。失敗時は安全側のフォールバック値（例: macro_sentiment=0.0）を使って継続します。
- 出力は JSON モードを期待してパース・検証後、DuckDB テーブルへ書き込みます。

主な機能一覧（抜粋）
---
- run_execution.py: ExecutionEngine の起動スクリプト（ペーパートレード分離）
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト
- config_setup.py: 対話式 .env 作成ウィザード
- validate_config.py: 起動前設定チェック CLI
- monitoring:
  - monitoring_db.py: 監視用 SQLite テーブルの初期化・読み書きラッパー
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/実行プロセスの監視
  - risk_monitor.py: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ
  - trade_monitor.py / alert_manager.py / kill_switch.py（監視/通知/停止制御）
- execution: 注文管理・リスク管理・ブローカ抽象化（BrokerClientFactory 等）
- portfolio: 候補選択・重み計算・セクター制限・ポジションサイズ計算
- research: ファクター計算（momentum/value/volatility）・特徴量探索（IC, forward returns）
- ai: news_nlp（ニューススコアリング）、regime_detector（市場レジーム判定）
- tools: paper_verification_report（ペーパートレード検証レポート）

ディレクトリ構成（主要ファイル）
---
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / Settings
- config_setup.py                 — .env ウィザード
- validate_config.py              — 設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — Monitoring 起動スクリプト

- execution/                       — 注文実行関連（Broker, Engine, OrderManager 等）
- monitoring/
  - monitoring_db.py               — SQLite テーブル定義 + MonitoringDB ラッパー
  - system_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - trade_monitor.py
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
- utils/
  - logging_setup.py
  - process_priority.py

補足 / 注意点
---
- 本 README はコードコメントをもとに要点を整理したものです。実運用前に必ず python -m kabusys.validate_config で設定チェックを行ってください。
- 本番運用（KABUSYS_ENV=live）では LINE 通知設定や KILL_FLAG_CLEAR_ON_START の値など安全項目を十分に確認してください。
- DuckDB / SQLite のファイルパスはデフォルトで data/ 配下にあります。バックアップやファイル権限に注意してください。
- OpenAI 連携部分は API コストと rate limit に注意して利用してください。

ライセンス / バージョン
---
- パッケージバージョンは kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。

その他
---
- 実際の運用・デプロイ手順、詳細な設定ファイル（config/*.yaml）生成スクリプト、テストケース等は別途用意される想定です。必要であれば README に追加の起動例やトラブルシュートを追記できます。