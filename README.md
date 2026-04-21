README
======

概要
----
KabuSys は日本株の自動売買／リサーチを想定した軽量なフレームワークです。  
主な目的は次の通りです。

- 株価データやファンダメンタル情報を用いたファクター計算・研究
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ決定）
- Execution エンジン（本番 / ペーパー）と発注管理（リスク制御を含む）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ニュース NLP（OpenAI を用いたセンチメント評価）やレジーム判定
- Paper Trading の検証レポート生成

特徴
----
- モジュール化された pure function ベースのポートフォリオ構築（テスト容易）
- DuckDB / SQLite を用いたデータ保管・分析
- ExecutionEngine は KABUSYS_ENV による本番 / ペーパートレード分離（ペーパートレードは専用 SQLite）
- 監視コンポーネントは監視用 DB（monitoring.db）に記録し、kill.flag を書き込むことで安全にエンジン停止可能
- OpenAI を使ったニュース NLP / レジーム判定を実装（API キーが必要）
- ログはコンソール + 日次ローテートファイル出力で統一

機能一覧
---------
- kabusys.config: 環境変数 / .env の自動読み込み・設定取得
- config_setup: 対話式ウィザードで .env を作成・更新
- validate_config: 起動前チェック（必須環境変数、パス、config/*.yaml の基本チェック）
- run_execution: ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBroker）
- run_monitoring: SystemMonitor のポーリング起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定）
- monitoring: System/Trade/Risk モニター群、KillSwitch、AlertManager（通知は実装に依存）
- portfolio: 候補選定、重み計算、ポジションサイズ計算、セクター制限、レジーム乗数
- research: ファクター計算、将来リターン、IC 計算、統計サマリー
- ai: news_nlp（OpenAI を使った銘柄別センチメント） / regime_detector（市場レジーム判定）
- tools: paper_verification_report（ペーパー取引結果の検証レポート出力）
- utils: logging_setup（統一ロギング）, process_priority（プロセス優先度設定）など
- monitoring_db: 監視用 SQLite テーブル定義 + 永続化 API

セットアップ手順
----------------

前提
- Python 3.9+ を推奨（ソース内の型注釈等に依存）
- 推奨パッケージ: duckdb, psutil, openai, pyyaml（検証用）
  例:
    pip install duckdb psutil openai PyYAML

手順例
1. リポジトリをクローンまたは展開し、開発環境を作る
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env の作成
   - 対話式ウィザード:
       python -m kabusys.config_setup
     ウィザードに従って J-Quants / kabuAPI 等を設定してください。
   - もしくは手動でプロジェクトルートに .env を作成（.env.example を参照）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
     --strict フラグを付けると警告も失敗扱い（exit 1）になります。

5. データディレクトリ / ログディレクトリ
   - デフォルトの DB / ログパスは .env で変更できます。存在しない親ディレクトリは自動作成されますが、権限などに注意してください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: OpenAI API キー（ai.* を使う場合）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（監視用 DB）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパー時の専用 DB）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定挙動）
- LOG_LEVEL: DEBUG/INFO/...
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番では 0 推奨）

注意: 自動 .env 読み込みはデフォルトで有効です（プロジェクトルートに .env を置くと起動時に読み込まれます）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方
------

対話的セットアップ
- python -m kabusys.config_setup
  → .env を生成 / 更新します。

設定検証
- python -m kabusys.validate_config
  → 環境変数・パス・config/*.yaml の存在（および簡易パース）をチェックします。
  - --strict を付けると警告があっても exit(1) になります。

ExecutionEngine の起動
- 本番/テスト実行
  - KABUSYS_ENV が paper_trading の場合、ペーパー専用 DB と MockBroker を使用します。
  例（シンプル起動）:
    KABUSYS_ENV=development python -m kabusys.run_execution
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  実行中に data/stop_requested.flag が作成されるとエンジンは停止します（同様に実行スレッドは停止フラグを監視）。

Monitoring の起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - Monitoring は KABUSYS_ENV に関わらず sqlite_path（デフォルト data/monitoring.db）を使用します。
  - data/stop_requested.flag が存在するとループを終了します。

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

AI 系（ニュース NLP / レジーム判定）
- OpenAI API キー（OPENAI_API_KEY）が必要です。関数はプログラムから呼び出す形で提供されています。
  例（ニューススコア算出を呼び出すプログラム内で）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

停止・Kill Switch
- kill.flag（Settings.kill_flag_path, デフォルト data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送れます（KillSwitch が評価して書き込む）。実行時の安全対策として、KILL_FLAG_CLEAR_ON_START の扱いに注意してください（本番では 0 推奨）。

ログ
- 共通ロギングユーティリティが用意されており、標準出力（stdout）と日次ローテーションファイル（logs/<app_name>.log）に出力します。ログディレクトリは環境変数 LOG_DIR で変更可能。

ディレクトリ構成（主なファイル）
--------------------------------
以下は src/kabusys 配下の主要ファイル・ディレクトリです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / .env 自動ロード・Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 起動前検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py          — 市場レジーム判定（OpenAI + ETF MA）
  - monitoring/
    - monitoring_db.py            — 監視 DB スキーマ + 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py            —（通知の抽象化、実装に依存）
  - execution/                     — Execution 系（Engine, OrderManager, BrokerFactory, RiskManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - data/                          — デフォルトの DB/フラグファイル保存先（runtime に生成）
    - monitoring.db (SQLite)
    - paper_trading.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - kill.flag
    - stop_requested.flag
    - execution.pid

サンプル .env（最低限）
----------------------
以下は最小構成例（プロジェクトルートの .env に保存）。必須値は環境に合わせて設定してください。

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

運用上の注意
-------------
- KABUSYS_ENV=live のときは特に設定値（LINE 通知・KILL_FLAG の扱いなど）を慎重に確認してください。validate_config の追加警告が役立ちます。
- 実行プロセスの優先度設定やログ出力に失敗した場合でもフェイルセーフで続行する実装が多いですが、権限やパスの問題は事前に解決してください。
- OpenAI を利用する処理は API の課金対象となります。レート制限や失敗時の挙動に注意してください（コード内でリトライ/フォールバックが実装されていますが、API コストは別途管理が必要です）。

貢献 / 開発
------------
- 新しい設定項目を追加した場合は config_setup.py / validate_config.py を更新してください。
- DB マイグレーションは monitoring_db.init_monitoring_db 内で行っています。既存のカラム追加などはここに追記してください。
- テストは各 pure function（portfolio/*, research/*）を単体でテストしやすい設計になっています。OpenAI / I/O を用いる部分はモックしやすいように分割されています。

ライセンス
---------
（ここにライセンス情報を記載してください）

---
この README はコードベースのソースを基に作成しました。さらに詳しい仕様（StrategyModel.md や PortfolioConstruction.md 等）がプロジェクトに含まれている場合は、それらを参照して実運用時の調整・確認を行ってください。