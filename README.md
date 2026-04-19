KabuSys — 日本株自動売買プラットフォーム（簡易ドキュメント）
================================================================

概要
----
KabuSys は日本株の自動売買・研究・モニタリングを目的とした Python ベースのプロジェクトです。
本リポジトリには以下の主要機能が含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードを切り替え可能（KABUSYS_ENV）
  - ブローカークライアントの抽象／モックを利用
- 監視デーモン（System / Trade / Risk モニタリング）起動スクリプト（run_monitoring.py）
  - 監視ログを SQLite に永続化
  - Kill Switch による ExecutionEngine 強制停止機構
- 研究／リサーチ用モジュール（ファクター計算、IC 計算など）
- AI 支援モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- 各種ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード・設定検証）
- 運用補助ツール（Paper Trading 検証レポート生成スクリプト等）

主要な機能一覧
----------------
- run_execution.py
  - ExecutionEngine を起動し注文処理を行う（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）
  - paper_trading の場合は data/paper_trading.db に記録して本番 DB と完全分離
- run_monitoring.py
  - SystemMonitor のポーリングループを実行
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視ログは sqlite_path（Settings.sqlite_path）へ永続化（監視は環境に依らず本番 sqlite を使用）
- config_setup.py
  - 対話式ウィザードで .env を初期作成 / 更新
- validate_config.py
  - .env や config/*.yaml を起動前に検証（--strict で警告も FAIL 扱い）
- tools/paper_verification_report.py
  - ペーパートレード DB を集計して検証レポートを出力（稼働率、成功率、レイテンシ等）
- ai/news_nlp.py, ai/regime_detector.py
  - OpenAI を使ったニュースセンチメント集計／市場レジーム判定（OPENAI_API_KEY 必須）
- portfolio/**
  - 候補選定 / 重み計算 / セクターキャップ / ポジションサイズ計算
- monitoring/**
  - MonitoringDB（SQLite テーブル初期化・読み書き）
  - SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine
- utils/**
  - ログ設定（setup_logging）/ プロセス優先度・CPU affinity 設定（set_process_priority / set_cpu_affinity）

セットアップ手順
----------------
前提: Python 3.10+ を想定（typing の | 演算子を使用）。

1. リポジトリをクローン
   - git clone ... && cd <project>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要な外部依存（少なくとも）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（validate_config の YAML 検証に必要、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式で作成する: python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参照して .env を用意してください（必須環境変数は後述）。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合は: python -m kabusys.validate_config --strict

6. データディレクトリの作成
   - ログディレクトリ（デフォルト: logs/）や data/ は起動時に自動生成されることが多いですが、権限等で失敗する場合があるので確認してください。

必須環境変数（例）
------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を利用する場合必須)

主な任意 / デフォルト値
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- MONITOR_POLL_INTERVAL: ポーリング間隔（秒）を環境変数で上書き可（run_monitoring 用。デフォルト 60）

使い方（よく使うコマンド）
-------------------------
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（注文処理）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV によって本番かペーパートレードかが変わります。
    - paper_trading の場合は data/paper_trading.db に記録され、本番 DB と分離されます。

- 監視デーモン起動（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒単位のポーリング間隔を上書きできます。
  - 停止: プロセスに SIGINT（Ctrl-C）を送るか、リポジトリ内 data/stop_requested.flag を作成すると安全に停止します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI スコアリング（プログラム的利用）
  - 例:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

運用上のファイル / フラグ
------------------------
- data/stop_requested.flag
  - run_execution / run_monitoring 停止検出用のファイル（存在すると起動中のループが終了します）
- data/kill.flag
  - KillSwitch による ExecutionEngine 強制停止トリガー（監視が発動した場合に書き込まれる）
- data/execution.pid（または Settings.pid_file_path による場所）
  - ExecutionEngine の PID ファイル（プロセス管理用）
- logs/
  - ログファイルはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます

データベースとマイグレーション
----------------------------
- monitoring.db（SQLite）
  - monitoring_db.init_monitoring_db() が存在しないテーブルを作成します（冪等処理）。
  - マイグレーション: dashboard に peak_value カラム、trade_logs に latency_ms カラムがなければ追加されます（自動で ALTER 実行）。

- DuckDB
  - 解析用に DuckDB ファイルを使用（デフォルト data/kabusys.duckdb）。
  - research / ai モジュールは DuckDB 接続を受け取り prices_daily, raw_financials, raw_news 等のテーブルを参照します。

ディレクトリ構成（概要）
----------------------
以下は主要なソースファイルとモジュールの一覧（src/kabusys 配下）。実際のファイル数はこの他にもありますが、代表的なものを示します。

- src/kabusys/
  - __init__.py
  - config.py               — 環境設定読み込み / Settings クラス
  - config_setup.py         — .env 対話ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py           — ニュース NLP（OpenAI）によるセンチメント集計
    - regime_detector.py    — レジーム判定（MA + マクロセンチメント）
  - research/
    - factor_research.py    — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - portfolio/
    - portfolio_builder.py  — 候補選定・重み付け
    - position_sizing.py    — 株数決定・スケール調整
    - risk_adjustment.py    — セクターキャップ・レジーム乗数
  - monitoring/
    - monitoring_db.py      — SQLite テーブル初期化・永続化層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （注文・約定の監視） ※実装参照
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — kill.flag 制御
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
  - utils/
    - logging_setup.py      — 統一ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定

注意事項 / 運用上のヒント
--------------------------
- 本番運用時は KABUSYS_ENV=live を使用します。validate_config は live の場合に追加の警告を出します（LINE 通知設定など）。
- run_monitoring は監視用 DB（Settings.sqlite_path）を使用します。監視は環境に関わらず本番の sqlite_path を参照しますので運用上の注意が必要です。
- ペーパートレードでは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を分離しているため本番 DB を汚さずに検証できます。
- AI 機能を使うには OPENAI_API_KEY を設定してください。API 呼び出しにはレート制限やネットワークエラーを考慮したリトライ実装が含まれます。
- ローカルで動かす際は .env に機密情報を記載しますが、.env は Git にコミットしないでください（config_setup でも注意書きを出しています）。
- ログディレクトリ作成に失敗した場合はファイルログが利用できなくなり、コンソール出力のみになります（setup_logging の挙動）。

追加の開発情報
----------------
- テストや CI から環境ロードを防ぎたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます（config.py の自動 .env ロードを無効化）。
- DuckDB / SQLite / OpenAI 呼び出し等は外部依存なので、ユニットテスト時はモック化することを推奨します。ai.news_nlp / ai.regime_detector では API 呼び出し箇所を差し替えやすい設計になっています。

お問い合わせ / 貢献
------------------
バグ報告や機能追加、改善提案は Issue / PR を通じてお願いします。README の追記やドキュメント改善も歓迎します。

以上。必要であれば README の英語版や各モジュールごとの詳細ドキュメント（API 使用例・型仕様・より詳しい運用手順）も作成します。どのセクションを拡張したいか教えてください。