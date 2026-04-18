# KabuSys — README (日本語)

本ドキュメントは、このリポジトリに含まれる KabuSys コードベースの使い方・セットアップ手順・ディレクトリ構成を日本語でまとめた README です。

概要
---
KabuSys は日本株向けの自動売買 / 研究基盤の一部を実装した Python パッケージです。本リポジトリには、以下のような機能群が含まれます。

- ExecutionEngine（発注エンジン）起動スクリプト
- System / Trade / Risk の監視コンポーネントとモニタリングエンジン
- ポートフォリオ構成（候補選定・重み計算・ポジションサイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI を用いたニュースセンチメント（OpenAI）連携
- 設定ウィザード（`.env` 生成）と設定検証 CLI
- ペーパートレード検証レポート生成ツール

主な特徴
---
- モジュール化された監視・発注ロジック（MonitoringEngine, ExecutionEngine）
- Paper Trading（本番と分離された SQLite DB を利用）モードをサポート
- DuckDB を用いた分析向けテーブル参照（prices_daily, raw_financials 等）
- OpenAI を利用したニュース NLP / レジーム判定の実装（フェイルセーフ・リトライ機構つき）
- ロギング設定ユーティリティ（console + 日次ローテーションファイル）
- 環境設定の対話式ウィザード（`.env` 書き出し）と起動前検証ツール

前提依存ライブラリ（例）
---
実行にはいくつかの外部ライブラリが必要です。プロジェクトに requirements.txt がない場合は下のようにインストールしてください（例）:

pip install duckdb psutil openai PyYAML

注意: sqlite3 は標準ライブラリです。OpenAI を用いる機能を使う場合は openai パッケージが必須です。YAML のパースはオプション（validate_config の一部チェック）です。

セットアップ手順
---
1. リポジトリをクローンして作業ディレクトリをルートに移動します。

2. Python 環境を用意して依存ライブラリをインストールします（pipenv/venv/poetry 等を推奨）。

3. .env を作成する
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - もしくは手動でルートに `.env` を置く（.env.example を参照）。

4. 重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (OpenAI を使う機能を利用する場合)
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - paper_trading の場合、mock broker を使い `data/paper_trading.db` を使用
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
   - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - LOG_DIR（ログ保存先、デフォルト: logs/）
   - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト: 60）

5. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります。

使い方（起動 / ツール）
---
- 実行エンジン（ExecutionEngine）起動
  - 本番（または設定された KABUSYS_ENV に従う）:
    python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper DB に記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は pid ファイル（デフォルト: data/execution.pid）を使用します。

- 監視ループ（SystemMonitor）起動
  python -m kabusys.run_monitoring
  - 監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書きできます（秒、デフォルト 60）。
  - 監視は常に本番の sqlite_path を使用して監視データを格納します（KABUSYS_ENV に関係なく）。
  - 停止は data/stop_requested.flag の作成で検知してループ終了します。

- 設定ウィザード（.env 作成・更新）
  python -m kabusys.config_setup

- 設定検証 CLI
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート出力
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - 引数 --db で DB パスを明示することも可能。環境変数 PAPER_TRADING_SQLITE_PATH を優先して参照します。

- AI 関連（プログラム的に呼び出す）
  - ニューススコアリング（ai/news_nlp.py）:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定（ai/regime_detector.py）:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらを呼ぶには DuckDB 接続を渡す必要があります（duckdb.connect）。

停止・Kill Switch
---
- data/stop_requested.flag
  - run_monitoring / run_execution の両スクリプトでループ中にこのファイルの存在を確認して graceful に停止します。手動停止やシステム終了用の簡易フラグです。

- data/kill.flag
  - KillSwitch（監視機能）から書き込まれるファイルです。リスク条件（ドローダウン超過やポジション上限超過）により ExecutionEngine に停止シグナルを送るために作成されます。ExecutionEngine は KillSwitch を監視して自分を停止するように設計されています（KillSwitch.write は冪等）。

ロギング
---
- setup_logging(app_name="...") が標準的なロギング初期化関数です。
- デフォルトで stdout（StreamHandler）と日次ローテーションファイル（logs/<app_name>.log）を設定します。
- ログレベルは LOG_LEVEL（環境変数）または引数で指定できます。

DB 初期化
---
- monitoring_db.init_monitoring_db(conn) は監視用 SQLite のテーブル群を冪等に作成します（テーブル・インデックス・マイグレーション含む）。run_execution/run_monitoring 内で自動的に呼び出されます。

サンプル .env（最小例）
---
以下は .env の最小例（実際の運用ではトークン・パスワードを適切に設定してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

ディレクトリ構成（主要ファイル）
---
以下は src/kabusys 以下の主要なファイル群の概要です（抜粋）。

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定取得
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層 / MonitoringDB クラス
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （取引監視; 実装有無はコードを参照）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — （アラート送信; 実装有無はコードを参照）
  - execution/
    - execution_engine.py    — ExecutionEngine（発注ロジックの中核）
    - broker_factory.py      — ブローカークライアント生成（Mock/実ブローカー切替）
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
    - news_nlp.py            — ニュース文章をLLMでスコアリング
    - regime_detector.py     — マーケットレジーム判定（MA + マクロNLP）
    - __init__.py
  - data/ (実行時に生成される想定)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (デフォルトログ出力先)

補足・運用上の注意
---
- デフォルトでは .env がプロジェクトルートに存在すると自動読み込みされますが、環境によっては KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化できます（テスト等で利用）。
- KABUSYS_ENV が `live` の場合は本番動作になります。validate_config により追加の注意喚起チェックを行います。特に KILL_FLAG_CLEAR_ON_START は本番では 0 を推奨します。
- OpenAI を用いる処理は API キーのレート制限や一時的失敗を考慮した実装（リトライ・バックオフ）になっていますが、API 呼び出しのコスト・遅延を考慮して運用してください。
- DuckDB / SQLite ファイルのパスは .env で指定可能です。バックアップや永続化ポリシーを検討してください。

トラブルシュート（簡易）
---
- ログが出力されない / ファイルが作成されない:
  - LOG_DIR 環境変数やログディレクトリの権限を確認。ログディレクトリ作成に失敗するとコンソール出力のみになります。
- 起動スクリプトが即終了する:
  - data/stop_requested.flag が存在していないか確認。
  - validate_config で必須環境変数が設定されているか確認。
- Paper Trading と本番の DB を混同しないでください。paper_trading モードでは paper_sqlite_path を使用します。

最後に
---
この README はコードベースの主要な使い方と構成の概要をまとめたものです。各モジュール（monitoring, execution, ai, research, portfolio 等）の詳細な仕様やパラメータ調整は該当するソースファイル内の docstring / コメントを参照してください。メンテナンスや拡張を行う際は、まず config_setup と validate_config を使って環境変数・設定を整え、少なくとも開発モードで動作検証を行うことを推奨します。