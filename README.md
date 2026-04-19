README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤の Python コードベースです。
主な目的は以下の通りです。

- 取引エンジン（ExecutionEngine）による発注処理（本番 / ペーパートレード対応）
- システム監視（SystemMonitor / MonitoringEngine）による稼働状態・データ鮮度監視
- リスク監視（ドローダウン・ポジション数など）と Kill Switch の自動発動
- 研究用ファクター計算・特徴量解析（DuckDB を使用）
- ニュースを用いた AI ベースのセンチメント評価（OpenAI API 統合）
- ペーパートレード検証用レポート生成ツール

主要機能
--------
- 環境管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式ウィザードで .env を作成/更新（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行系
  - run_execution: ExecutionEngine 起動（KABUSYS_ENV により paper_trading モードを切替）
  - run_monitoring: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 監視・アラート
  - system_status / trade_logs / risk_logs / dashboard を SQLite に永続化
  - RiskMonitor によるドローダウン監視・ポジション上限監視
  - KillSwitch によるフラグファイル生成で ExecutionEngine を安全に停止
- ポートフォリオ関連（純粋関数群）
  - 候補選定、重み計算、リスク調整、ポジションサイズ計算（単元丸め含む）
- 研究（DuckDB ベース）
  - モメンタム/ボラティリティ/バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）や統計サマリ
- AI 統合（OpenAI）
  - ニュース記事を LLM でスコアリングし ai_scores に書き込み
  - 市場レジーム判定（ETF + マクロ記事の LLM 評価の複合）
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順
----------------

1. リポジトリをクローンし、仮想環境を作成・有効化します。
   （ここでは一般的な手順のみ示します）

   - Python 3.9+ を推奨
   - 仮想環境作成例:
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows

2. 必要なパッケージをインストールします。
   requirements.txt がある場合はそれを使ってください。
   主要依存例（プロジェクト内で使われているもの）:
   - duckdb
   - psutil
   - openai
   - PyYAML（config 検証で任意）
   - そのほか標準ライブラリ（sqlite3 等）
   例:
     pip install duckdb psutil openai PyYAML

3. 初期設定（.env）の準備
   - 対話式ウィザードで .env を生成:
       python -m kabusys.config_setup
     ウィザードに従い J-Quants / kabuAPI / DB パス等を入力してください。
   - もしくは .env を手動で作成してください（.env.example を参照）。

4. 設定検証（起動前の推奨手順）:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 配下に DB やフラグファイルを作成します。
   - logs/ ディレクトリはログ出力時に自動作成されますが、書き込み権限を確認してください。

主要な環境変数（概要）
---------------------
- 必須（runtime / validate_config がチェック）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / ログ:
  - KABUSYS_ENV: development | paper_trading | live （default: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

- データベースパス（デフォルト値）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading モード専用）

- OpenAI:
  - OPENAI_API_KEY: AI 関連（news_nlp / regime_detector）で使用

- 監視関連:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、default=60）
  - PID_FILE_PATH / KILL_FLAG_PATH: pid / kill flag のパス（Settings 経由で上書き可）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" でクリア）

- 自動 .env ロード制御:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化（テスト用途）

使い方（主なコマンド）
--------------------

- 対話式に .env を作る:
    python -m kabusys.config_setup

- 設定の検証:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパートレードは KABUSYS_ENV に従う）:
    python -m kabusys.run_execution
  - run_execution はデーモン的に ExecutionEngine をスレッドで動かし、
    data/stop_requested.flag の存在で安全に終了します。
  - paper_trading モードでは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

- Monitoring（SystemMonitor のポーリング）を起動:
    python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能:
      MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ペーパートレード検証レポート:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（プログラムから呼び出す例）
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定の上、プログラムから呼び出します。
  - 例（簡易）:
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 1))
  - 注意: OpenAI 呼び出しはネットワーク/レート制限を伴います。API キーは安全に管理してください。

ログと永続化
------------
- ログ:
  - setup_logging によりコンソール（stdout）と日次ローテートされたファイルログ（logs/<app_name>.log）に出力します。
  - ログディレクトリは LOG_DIR 環境変数またはデフォルトの logs/ に作成されます。
- 永続化:
  - 監視・注文履歴等は SQLite（SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）に記録します。
  - 研究データ等は DuckDB（DUCKDB_PATH）で管理します。

重要な運用注意点
-----------------
- KABUSYS_ENV を live に設定する場合は設定（APIキー・LINE通知設定等）を慎重に確認してください。validate_config は live 時に特別な警告を出します。
- KillSwitch は data/kill.flag を作成することで ExecutionEngine に停止を指示します。ExecutionEngine 側は起動時に kill.flag の有無をチェックします。
- run_monitoring / run_execution は data/stop_requested.flag による安全停止機構を持ちます。運用での停止はこのフラグの作成で行えます。
- OpenAI 関連は API コストとレート制限に注意してください。失敗時のフォールバックロジックを組み込んでありますが、運用設計は慎重に行ってください。
- psutil を使ってプロセス優先度や CPU affinity を設定します。権限不足で設定できない場合はワーニングでスキップされます。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py                     — パッケージ定義（__version__）
- config.py                       — 環境変数/.env の読み込みと Settings クラス
- config_setup.py                 — .env 対話式ウィザード
- validate_config.py              — 設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py                    — ニュースの LLM スコアリング処理
  - regime_detector.py             — マクロ + ETF MA によるレジーム判定
- monitoring/
  - monitoring_db.py               — SQLite 永続化層
  - system_monitor.py              — システム・データ鮮度監視
  - risk_monitor.py                — ドローダウン・ポジション監視
  - trade_monitor.py               — 発注ログ監視（滞留等）
  - kill_switch.py                 — kill.flag 管理
  - monitoring_engine.py           — 各 Monitor を束ねるエンジン
  - alert_manager.py               — （通知管理、実装参照）
- execution/                       — ExecutionEngine / OrderManager / BrokerFactory 等
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py    — ペーパートレード検証レポート
- utils/
  - logging_setup.py               — ログ初期化ユーティリティ
  - process_priority.py            — プロセス優先度設定ユーティリティ

補足 / 開発向けメモ
------------------
- DuckDB 接続を渡すことで研究系関数（ファクター計算等）はデータベースに依存して動きます。DuckDB 内のテーブル（prices_daily / raw_financials / raw_news 等）を用意してください。
- YAML ファイル（config/*.yaml）はオプションで、PyYAML があれば validate_config が中身のパース検証を行います。
- テストや CI で .env の自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス・貢献
----------------
- この README にはライセンス情報を含めていません。実際のリポジトリの LICENSE を参照してください。
- 貢献やバグ報告は通常の GitHub ワークフロー（Issue / PR）に従ってください。

以上。必要であれば README に含める具体的な .env のテンプレートやよくあるトラブルシューティング、さらに詳しい CLI 使用例や API 呼び出しサンプルを追記します。どの項目を詳しく追加しましょうか？