README
======

概要
----
KabuSys は日本株向けの自動売買・研究基盤です。本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine）
- 監視・アラート（Monitoring）
- ポートフォリオ構築（選定・重み・ポジションサイズ）
- リサーチ（ファクター計算・特徴量探索）
- AI 補助（ニュース NLP によるセンチメント評価、レジーム判定）
- 各種ユーティリティ（設定ウィザード、設定検証、ログ設定 等）
- ペーパートレード検証レポート生成ツール

主な設計方針
- 実行時の環境依存設定は .env / 環境変数で管理
- Paper Trading と Live は DB を分離（paper_trading 用の専用 SQLite を使用）
- AI モジュールは OpenAI（gpt-4o-mini）を利用（API キー必須）。失敗時はフェイルセーフ動作
- DuckDB を分析用 DB、SQLite を監視・発注履歴用 DB に利用

機能一覧
--------
主要な機能（抜粋）:

- 実行（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBrokerClient）/ live/ development を切替
  - RiskManager・OrderManager・Reconciler 等を組み立てて ExecutionEngine を起動
  - 停止フラグ（data/stop_requested.flag）検知で安全停止
  - PID ファイル管理（data/execution.pid）

- 監視（run_monitoring.py, monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度を監視
  - TradeMonitor: 注文状態や約定の検査（滞留/異常約定 等）
  - RiskMonitor: ドローダウン・ポジション数上限の監視、Dashboard の更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る
  - AlertManager 経由で通知（LINE 等の実装は設定次第）

- ポートフォリオ（portfolio パッケージ）
  - 候補選定（select_candidates）
  - 等ウェイト / スコア加重（calc_equal_weights / calc_score_weights）
  - セクター上限適用（apply_sector_cap）
  - ポジションサイズ算出（calc_position_sizes）

- リサーチ（research パッケージ）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- AI（ai パッケージ）
  - news_nlp.score_news: raw_news を LLM に投げて銘柄別センチメントを ai_scores に書き込む
  - regime_detector.score_regime: ma200 とマクロセンチメントを合成して market_regime に書込む
  - OpenAI API (gpt-4o-mini) 使用。API キーは OPENAI_API_KEY または引数で指定

- ツール
  - config_setup: 対話形式で .env を作成・更新
  - validate_config: .env と config/*.yaml の整合性チェック
  - tools.paper_verification_report: ペーパートレードの検証レポート出力

セットアップ手順
--------------
1. リポジトリをクローン
   - git clone ...

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必須の主なパッケージ:
     - duckdb, psutil, openai
     - （監視・レポート用に sqlite3 は標準ライブラリ）
     - PyYAML は config 検証で任意（インストールされていない場合は YAML 検証をスキップ）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt がある場合はそれを利用してください:
     - pip install -r requirements.txt

4. ディレクトリ作成（ログ・データ）
   - data/ と logs/ は自動生成されることが多いですが、手動で存在を確認しておくと良いです:
     - mkdir -p data logs

5. .env 作成（推奨: 対話ウィザード）
   - python -m kabusys.config_setup
   - あるいは手動で .env を作成（以下に例あり）

6. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

注意: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込む挙動を抑止できます（テスト等で利用）。

環境変数（主要）
----------------
- KABUSYS_ENV: execution 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading の場合 run_execution は PAPER_TRADING 用の DB を使用し MockBrokerClient を使う
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.* を使うとき必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading の SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定振る舞い（"instant"|"partial"|"never"|"reject"、デフォルト: "instant"）
- LOG_LEVEL: ログレベル ("DEBUG"|"INFO"|"WARNING"|"ERROR"|"CRITICAL")
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"0" または "1"、本番は "0" 推奨）

使い方（コマンド例）
-------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - MONITOR_POLL_INTERVAL を指定してポーリング間隔を変更可:
    - export MONITOR_POLL_INTERVAL=30
    - python -m kabusys.run_monitoring
  - 監視は data/stop_requested.flag が存在するとループを抜けます

- 実行エンジン起動
  - KABUSYS_ENV を設定して実行モードを切替:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - ペーパートレードでは PAPER_TRADING_SQLITE_PATH（data/paper_trading.db がデフォルト）へ記録
  - 実行中に data/stop_requested.flag が作成されると安全停止します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール例
  - ニューススコアを生成:
    - 事前に OPENAI_API_KEY を設定
    - Python スクリプト内で:
      from kabusys.ai.news_nlp import score_news
      score_news(duckdb_conn, target_date, api_key=None)  # api_key None → 環境変数参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

ログとファイル
---------------
- ログ:
  - デフォルト出力先: logs/<app_name>.log（app_name 例: execution, monitoring）
  - ログは日次ローテーション（30 日分保持）
- DB:
  - DuckDB: data/kabusys.duckdb（環境変数 DUCKDB_PATH で変更可）
  - SQLite（監視）: data/monitoring.db（SQLITE_PATH）
  - SQLite（paper_trading）: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- フラグ / PID:
  - 停止フラグ（run_* が参照）: data/stop_requested.flag
  - Kill スイッチ（監視 → Execution 停止トリガ）: data/kill.flag
  - Execution PID ファイル: data/execution.pid

重要な挙動メモ
---------------
- run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用します（監視 DB は環境で分離しない設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合に専用 paper_trading DB を使用して本番 DB と分離します。
- AI モジュールは OpenAI API を呼ぶため API キーが必須。API 呼び出しが失敗してもシステム全体を停止させない（フェイルセーフ）設計です。
- デフォルトのポーリング間隔は 60 秒（MONITOR_POLL_INTERVAL で上書き可能）。0 以下の値は無視されデフォルトにフォールバックします。

ディレクトリ構成（概要）
----------------------
プロジェクトの主要ファイル/ディレクトリ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロード・Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）
    - regime_detector.py     — レジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / CRUD
    - monitoring_engine.py   — 各 Monitor 統合ループ
    - system_monitor.py      — システム状態監視
    - trade_monitor.py       — 注文監視（存在）
    - risk_monitor.py        — ドローダウン/ポジション監視
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — （通知管理）
  - execution/
    - execution_engine.py    — ExecutionEngine（存在）
    - broker_factory.py      — BrokerClientFactory（Mock / 実ブローカー）
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
  - utils/
    - logging_setup.py       — ロギング設定ユーティリティ
    - process_priority.py    — プロセス優先度設定ユーティリティ
  - data/                    — 実行時に使用する data ファイル（DB / flag / pid 等、リポジトリに含めない）

サンプル .env（抜粋）
--------------------
以下は .env の一例（実運用では機密情報は絶対にコミットしないこと）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

よくある運用フロー（例）
-----------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. データ取り込み / DuckDB の準備（外部スクリプト）
4. 監視プロセスを起動（systemd / Supervisor / docker などで）
   - python -m kabusys.run_monitoring
5. 実行エンジンを起動
   - python -m kabusys.run_execution
6. 必要に応じて AI スコアやレジーム判定を定期実行（cron / Scheduler）
7. data/kill.flag を書き込むことで ExecutionEngine を停止させる（監視が判定して書き込む/手動でも可能）

その他
-----
- 開発・テスト時は KABUSYS_ENV=development を推奨（発注ロジックの安全弁が働く）
- 本番では KABUSYS_ENV=live に設定する前に validate_config で設定を慎重に確認すること
- config/*.yaml（system_config.yaml 等）は設定テンプレート生成スクリプトやドキュメントを参照してください

必要であれば README に追記してほしい項目（例：requirements.txt の具体的依存一覧、systemd ユニット例、Docker 化手順、CI 設定など）を教えてください。