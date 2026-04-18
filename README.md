KabuSys — 自動日本株取引システム
=================================

この README はリポジトリ内の主要スクリプトとモジュール群をまとめた簡易ドキュメントです。
実行/運用に必要な設定や使い方、主要コンポーネント構成を日本語で説明します。

概要
----
KabuSys は日本株自動売買システムのコアライブラリ/ツール群です。主な機能は次のとおりです。

- ExecutionEngine（発注エンジン）: 実際の発注処理を行う（実口座 / ペーパートレード対応）
- Monitoring（監視）: システム状態・データ鮮度・発注ログ等の監視、Kill Switch による安全停止
- Portfolio Construction（銘柄選定 / 配分 / ポジションサイズ計算）
- Research（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 運用支援ツール（.env 設定ウィザード、設定検証、Paper Trading レポート等）
- 永続化: SQLite（監視・注文ログ）および DuckDB（分析用）

主な機能一覧
--------------
- 環境設定ウィザード: python -m kabusys.config_setup により対話的に .env を作成
- 設定検証: python -m kabusys.validate_config で環境変数と config/*.yaml の整合性チェック
- Execution 起動: python -m kabusys.run_execution（KABUSYS_ENV によりペーパー/本番切替）
- Monitoring 起動: python -m kabusys.run_monitoring（監視ポーリングループ）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.score_news: raw_news を LLM でスコア化して ai_scores に保存
  - kabusys.ai.regime_detector.score_regime: マクロニュース + ETF ma200 から市場レジーム判定
- Portfolio 実装（純粋関数）:
  - 候補選定、等重/スコア加重、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ計算
- ユーティリティ:
  - ログ設定（stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - MonitoringDB: SQLite を用いた監視ログ操作ラッパー

セットアップ手順
----------------
以下はローカル実行の最小セットアップ例です。

1. Python 環境準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - requirements.txt がない場合は代表的な依存をインストールしてください:
     pip install duckdb psutil openai PyYAML
   - sqlite3 は標準ライブラリ、その他パッケージは用途に応じて追加してください。

3. プロジェクトルートを PATH に含める / install
   - 開発時は repo のルート（src を含む）を PYTHONPATH に追加するかパッケージをインストールします。
     例: export PYTHONPATH=$(pwd)/src
   - または pip install -e .（pyproject.toml があれば）で開発インストール。

4. .env の作成
   - 対話ウィザードで作成:
     python -m kabusys.config_setup
   - あるいは手動で .env を作成（例）:
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

6. データディレクトリ作成（必要に応じて）
   - SQLite / DuckDB / logs ディレクトリは通常自動作成されますが、権限に注意してください。

主要環境変数と設定
-------------------
重要な環境変数（抜粋）:

- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading: MockBroker を使用し data/paper_trading.db を利用（実 DB と分離）
  - live: 本番モード（実際に発注されます）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: MockBroker の約定挙動 ("instant" | "partial" | "never" | "reject")
- KILL_FLAG_CLEAR_ON_START: 起動時に data/kill.flag を自動クリアするか（"1" でクリア）

使い方（起動 / CLI）
-------------------

- 環境変数読み込みに関して
  - .env と .env.local は自動ロードされます（OS 環境変数が優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - exit code が 0 なら OK

- ExecutionEngine（発注エンジン）起動
  - 例（ペーパートレード）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 例（本番）:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - 注意:
    - paper_trading の場合、MockBrokerClient を使用しデータは PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録され、本番 DB と分離されます。
    - 起動時に data/stop_requested.flag が既に存在する場合は起動しません。
    - 実行中は data/stop_requested.flag を作成してエンジンを停止できます（グレースフル停止）。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（例: export MONITOR_POLL_INTERVAL=30）
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / Regime スコアリング（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - conn: duckdb connection
    - target_date: date オブジェクト（スコア対象日）
    - api_key: None の場合は OPENAI_API_KEY を参照
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 同様に DuckDB と API キーを渡す

停止 / Kill Switch
------------------
- 実行スクリプトは data/stop_requested.flag の存在をチェックしてグレースフルに停止します（手動停止要求）。
- Kill Switch（自動停止条件）:
  - RiskMonitor 等が条件を満たすと kill.flag（Settings.kill_flag_path、既定 data/kill.flag）を書き込み、ExecutionEngine に停止シグナルを送ります。
  - KillSwitch.clear() でフラグを削除できます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動クリアされます（本番では 0 推奨）。

ログ / PID / DB
---------------
- ログ:
  - デフォルト: logs/<app_name>.log（TimedRotatingFileHandler による日次ローテーション、30日保持）
  - stdout へも出力（StreamHandler）。LOG_DIR 環境変数でログディレクトリを変更可能。
- PID ファイル:
  - Execution 作成: data/execution.pid（Settings.pid_file_path）
- DB:
  - 監視用 SQLite: data/monitoring.db（Settings.sqlite_path）
  - ペーパートレード SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - 分析用 DuckDB: data/kabusys.duckdb（Settings.duckdb_path）

ディレクトリ構成（主なファイル・モジュール）
---------------------------------------
（src/kabusys をルートとした簡易ツリー）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト

  - execution/               — 発注周り（Engine / BrokerFactory / OrderManager 等）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / CRUD
    - system_monitor.py      — CPU/メモリ/Disk/データ鮮度監視
    - risk_monitor.py        — ドローダウン／ポジション上限監視
    - trade_monitor.py       — 発注ログ監視（滞留注文等）
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各モニタを束ねる
    - alert_manager.py       —（通知ロジック、LINE 等を想定）
  - portfolio/
    - portfolio_builder.py   — 候補選定、等重・スコア加重
    - position_sizing.py     — 株数決定、aggregate cap、lot で丸め
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算（DuckDB 使用）
    - feature_exploration.py — IC / forward returns / summary
  - ai/
    - news_nlp.py            — raw_news を OpenAI でセンチメント化して ai_scores に保存
    - regime_detector.py     — ma200 + マクロセンチメントから regime 判定
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py       — 共通ロギング設定（stdout + 日次ファイル）
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

開発上の注意 / ベストプラクティス
---------------------------------
- .env は絶対にバージョン管理にコミットしない（config_setup.py でも注記あり）。
- 本番環境 (KABUSYS_ENV=live) では KILL_FLAG_CLEAR_ON_START=0 を推奨（誤って Kill Switch をクリアしない）。
- Monitoring は本番 sqlite_path を使用するため、Monitoring の DB 操作が本番 DB に影響する点に注意。
- AI 機能は外部 API（OpenAI）に依存するため、API キー管理とコストに注意。
- DuckDB をデータ分析基盤として使用するため、prices_daily / raw_financials / raw_news 等のテーブル構成を事前に整備してください。
- 依存パッケージのバージョン制御や requirements.txt / pyproject.toml の管理を推奨します。

よくあるコマンド例
------------------
- .env を作って検証する:
  python -m kabusys.config_setup
  python -m kabusys.validate_config

- ペーパートレード実行（別ターミナルで）:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

- 監視開始（デフォルト 60 秒間隔）:
  python -m kabusys.run_monitoring
  # 間隔を 30 秒にしたい場合:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
-----------------------
- パッケージバージョン: kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートに置いてください（この README には含めていません）。

補足
----
この README はコードベース内の docstring / コメントを元に要点を纏めています。実運用の前に必ず python -m kabusys.validate_config による検証と、少量データでの動作確認を行ってください。質問や追加で記載したい箇所があれば教えてください。