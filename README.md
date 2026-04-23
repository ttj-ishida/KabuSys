README
======

概要
----
KabuSys は日本株の自動売買・リサーチ基盤を想定した Python パッケージです。  
主な機能は以下の通りです。

- 実行エンジン（ExecutionEngine）の起動スクリプト（本番 / ペーパートレード切替）
- システム監視（SystemMonitor / MonitoringEngine）とアラート・Kill Switch
- ポートフォリオ構築（候補選定・重み付け・ロット丸め・リスク適用）
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）
- AI 連携（OpenAI を利用したニュースセンチメント評価 / レジーム判定）
- ペーパートレード検証レポート生成ツール
- 設定ウィザード（.env 生成）と設定検証 CLI

特徴
----
- 実行 / 監視はスクリプト（python -m kabusys.run_execution / run_monitoring）で起動可能
- 環境変数 / .env による柔軟な設定（自動ロード機能あり）
- ペーパートレード時は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を用いた分析用データ層、SQLite を監視 / 履歴保存用に利用
- OpenAI API 呼び出しはリトライやレスポンス検証を行いフェイルセーフ設計
- ロギングは統一的にセットアップ（コンソール + 日次ローテーションファイル）

セットアップ手順
----------------

1. Python 環境
   - 推奨: Python 3.10 以上（typing の新表記や依存パッケージを考慮）
2. 依存パッケージをインストール
   - 代表的な必要パッケージ:
     - duckdb
     - psutil
     - openai
     - (任意) pyyaml — validate_config の YAML 検証用
   - 例:
     - pip install duckdb psutil openai pyyaml
     - またはプロジェクトに requirements.txt がある場合: pip install -r requirements.txt
3. プロジェクトルートに data / logs 等のディレクトリを作成（起動時に自動作成される場合あり）
   - デフォルト:
     - data/kabusys.duckdb (DUCKDB_PATH)
     - data/monitoring.db (SQLITE_PATH)
     - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
     - logs/ (LOG_DIR)
4. .env の準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して必要値を設定してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（抜粋）:
     - KABUSYS_ENV (development | paper_trading | live)
     - OPENAI_API_KEY (AI 機能を使う場合)
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか)
5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションで警告もエラー扱いにできます

使い方
------

起動スクリプト（長時間プロセス）
- 実行エンジン（発注ロジックを含む）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に書き込みます（本番 DB と分離）。
    - 起動前に data/stop_requested.flag が存在すると起動せず即終了します。
    - エンジンは data/execution.pid に PID を書き込みます。
- 監視ループ（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 特記事項:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）。
    - 監視は本番 sqlite_path を常に使用します（環境に関係なく）。

設定関連コマンド
- 対話式 .env 作成 / 更新:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]

ツール
- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

監視 / Kill Switch
- KillSwitch はルール（ドローダウンやポジション上限など）に基づき data/kill.flag を出力します。ExecutionEngine はこのフラグを検知して安全に停止する仕組みです。
- 手動停止用フラグ:
  - data/stop_requested.flag — これを置くと run_monitoring / run_execution のループが終了します。
  - data/kill.flag — KillSwitch が書き込む停止指示ファイル。KILL_FLAG_CLEAR_ON_START=1 で起動時に自動クリアできます（本番では 0 推奨）。

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI を使う AI 機能用
- KABUSYS_ENV — execution の動作モード（development | paper_trading | live）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL, LOG_DIR — ログ出力制御
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — プロセス管理 / Kill Switch

ディレクトリ構成（主なファイル）
--------------------------------
以下は package 内の主要モジュールとファイル例です（省略あり）。実際のソースは src/kabusys 以下に格納されています。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env の自動読み込みと Settings クラス
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ統一セットアップ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 用永続層
    - system_monitor.py      — システム状態 / データ鮮度チェック
    - trade_monitor.py       — （取引監視ロジック; 実装ファイルあり）
    - risk_monitor.py        — ドローダウン / ポジション数監視
    - kill_switch.py         — Kill Switch（flag ファイル制御）
    - monitoring_engine.py   — モニターを束ねるループ
    - alert_manager.py       — （通知管理; 実装ファイルあり）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py
  - (execution/, data/ 等のサブパッケージ — 実行ロジックやデータ処理コード)

開発上の注意
-------------
- 本リポジトリは本番発注に関連する機能を含みます。KABUSYS_ENV を誤って live にしたまま外部接続しないよう注意してください。
- .env は絶対にリポジトリへコミットしないでください（config_setup でもその旨のコメントを出力します）。
- OpenAI / 外部 API キーは安全に管理してください。
- run_monitoring は監視用 SQLite を常に本番 sqlite_path で使用します。監視が本番 DB を参照する設計です。

トラブルシュート
-----------------
- ログ出力先が作成できない場合はコンソールのみで動作します（警告が出ます）。
- validate_config で YAML 検証がスキップされた場合は PyYAML をインストールしてください。
- MONITOR_POLL_INTERVAL に 0 や負値を入れるとデフォルト（60 秒）にフォールバックします。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（ソース内定義）。

よくあるコマンド早見
--------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

以上。セットアップや実行で不明点があれば、使いたい機能（例: ペーパートレード実行 / AI スコア計算 / レポート作成）を教えてください。具体的な手順を補足します。