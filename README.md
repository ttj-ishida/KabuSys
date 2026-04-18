# KabuSys

日本株向け自動売買システム（ライブラリ + 起動スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・研究用ユーティリティを含む自動売買プラットフォームの骨子実装です。モジュール設計により本番・ペーパートレード切替、監視・キルスイッチ、AI を使ったニュース評価やレジーム判定、DuckDB を利用したファクター計算などを提供します。

## 主な特徴
- 実行環境切替（KABUSYS_ENV: development / paper_trading / live）
  - paper_trading では MockBrokerClient を用い、ペーパートレード用 DB（data/paper_trading.db）へ記録して本番 DB と分離
- ExecutionEngine（発注エンジン）と Monitoring（監視）を独立したプロセスとして起動可能
- Kill Switch による安全停止（data/kill.flag）
- 監視ログの永続化（SQLite：data/monitoring.db）とダッシュボード・リスクログ等の管理
- DuckDB を用いた研究用ファクター計算・特徴量探索
- ニュースの LLM（OpenAI）によるセンチメントスコアリング（ai.news_nlp）
- 市場レジーム判定（ai.regime_detector）
- Paper Trading の検証レポート生成ツール
- 環境設定ウィザード（.env の生成）と起動前設定検証 CLI

## 主要機能一覧
- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動（発注処理）
  - run_monitoring.py — SystemMonitor ポーリングループ起動（監視）
- 設定管理
  - config_setup.py — 対話式 .env ウィザード
  - validate_config.py — 環境・設定ファイルの検証 CLI
  - config.py — Settings クラス（環境変数読み込み・デフォルト）
- 監視
  - monitoring/monitoring_db.py — 監視用 SQLite スキーマと永続化 API
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py 等
- 発注・リスク管理（execution 以下）
  - Broker クライアントファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（詳細は execution パッケージ参照）
- ポートフォリオ構築（portfolio）
  - 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- 研究（research）
  - factor_research（モメンタム / バリュー / ボラティリティ等）、feature_exploration（IC計算等）
- AI 関連（ai）
  - news_nlp.score_news — ニュースの銘柄別センチメント付与（OpenAI）
  - regime_detector.score_regime — レジーム判定（ETF MA + マクロニュースの LLM）
- ツール
  - tools/paper_verification_report.py — ペーパートレード検証レポート出力

## セットアップ手順（開発環境向け）
1. Python 仮想環境の作成・有効化
   - python3 -m venv .venv
   - Unix/macOS: source .venv/bin/activate
   - Windows: .venv\Scripts\activate

2. 依存ライブラリをインストール
   - 本リポジトリに requirements ファイルは同梱していませんが、主に以下が必要になります：
     - duckdb
     - psutil
     - openai
     - (オプション) PyYAML — validate_config の YAML 検証を有効にするため
   - 例:
     - pip install duckdb psutil openai PyYAML

3. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env を手動で作成（.env.example を参照）
   - config.py はプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます。自動読み込みを無効化する場合は:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定の検証（起動前確認）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 以下に DB やフラグファイルが置かれます。必要なら作成してください（多くの起動処理は自動作成を行いますが事前に権限を確認してください）。

## 主要な環境変数（抜粋）
- 必須（少なくとも一部は必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 実行環境
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
    - paper_trading: MockBroker を使用し、PAPER_TRADING_SQLITE_PATH へ書き込み
- ログ
  - LOG_LEVEL — ログレベル（DEBUG/INFO/…、デフォルト: INFO）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
- DB パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- AI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュール使用時に必要）
- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 参照）

（注）config.py に記載のプロパティが使用可能です。詳細なデフォルト値や検証は src/kabusys/config.py を参照してください。

## 使い方（起動 / 実行例）

- ExecutionEngine（発注エンジン）を起動
  - python -m kabusys.run_execution
  - 特記事項:
    - 起動時にプロセス優先度を "high" に設定します（set_process_priority を使用）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録します。
    - 停止は data/stop_requested.flag や data/kill.flag（Kill Switch）などで制御されます。
    - 実行中の PID は data/execution.pid（デフォルト）へ書き込まれます。

- Monitoring（監視ループ）を起動
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を上書き可能（秒）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 特記事項:
    - Monitoring は KABUSYS_ENV にかかわらず、本番の sqlite_path（Settings.sqlite_path）を使用します（監視ログは常に同じ DB に記録）。
    - 停止フラグ: data/stop_requested.flag を作成するとループ終了。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール呼び出し（例: ニューススコアリング）
  - プログラムから呼ぶ:
    - from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 1), api_key="sk-xxxx")
  - OPENAI_API_KEY 環境変数を設定しておけば api_key を省略できます。

## 重要なファイル・フラグ
- data/kill.flag — Kill Switch のフラグファイル（存在すると ExecutionEngine に停止勧告）
- data/stop_requested.flag — 起動スクリプト（run_execution / run_monitoring）が外部からの停止要求を検知するためのフラグ
- data/execution.pid（PID ファイル、デフォルトパスは Settings.pid_file_path）
- logs/ — デフォルトのログディレクトリ（setup_logging が作成）

## ディレクトリ構成（概観）
（src 以下を想定。主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
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
    - execution/         (発注系の実装: Engine, BrokerFactory, OrderManager 等)
    - data/              (データパイプライン / DuckDB 用ユーティリティ ※別ファイル群あり)

（注）上記は主要モジュールの一覧です。各パッケージ内にさらに実装が存在します。

## 運用上の注意
- 本番環境（KABUSYS_ENV=live）では env の値や LINE 通知設定、KILL_FLAG_CLEAR_ON_START 等を慎重に設定してください。validate_config は本番向けの警告も出します。
- OpenAI 等外部 API を利用する機能は API キー管理に注意してください（課金・レート制限）。
- run_monitoring は監視 DB を参照しますが、本リポジトリの設計では監視ログは環境にかかわらず production sqlite_path を書きます。意図的な分離を行いたい場合は設定を確認してください。
- プロセス優先度設定や CPU affinity の変更はプラットフォーム依存で失敗することがあります（権限不足など）。失敗時は警告ログのみ出して継続します。

## 開発・拡張のヒント
- DuckDB 接続を受け取る研究系関数（research/*.py）は外部依存が少なく、ユニットテストが書きやすい設計です。
- AI 関連の外部呼び出しは専用ラッパー関数（_call_openai_api 等）をモックしてテスト可能です。
- monitoring/monitoring_db.py の init_monitoring_db は冪等にテーブルを作成し、簡易マイグレーションも行います。DB スキーマ変更時はここを更新してください。

---

README に記載されていない詳細や実装上の質問、起動でのトラブルシュートが必要であれば、目的（例: 実機で起動したい / ログが出ない / AI の API エラー）が分かる簡単な状況を添えて質問してください。必要に応じて起動コマンドや環境変数の具体例を追記します。