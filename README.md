# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向けREADME。

この README はコードベースの主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連するリサーチ／監視（Monitoring）機能を提供する Python パッケージです。  
主な役割は以下のとおりです。

- 戦略に基づく銘柄選定・配分（Portfolio construction）
- ポジションサイズ計算（position sizing）やセクター集中制限
- 実際の発注エンジン（ExecutionEngine）：kabuステーション等への発注を行う（本番 / ペーパートレード切替対応）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch（危険時に発注を停止）
- リサーチ用モジュール（ファクター計算、特徴量解析）
- AI モジュール（ニュースの NLP によるセンチメント評価、レジーム判定）
- ツール類（.env 設定ウィザード、設定検証、ペーパー検証レポート生成 など）

設計上、データ永続化は DuckDB（分析用）と SQLite（監視・ペーパートレード用）を使用します。OpenAI（LLM）を使った処理も一部に含まれます（APIキー必須）。

---

## 機能一覧

- Execution
  - ExecutionEngine（発注ロジック、リスク管理、オーダー管理、リコンサイル）
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、データを専用 SQLite（data/paper_trading.db）に分離
  - Kill Switch / stop フラグによる安全停止

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: オーダー滞留や異常約定の検出（trade_logs テーブル参照）
  - RiskMonitor: ドローダウン検知、ポジション上限チェック（dashboard / positions を参照）
  - AlertManager（通知）と KillSwitch の連携

- Portfolio
  - 銘柄選定、スコア／等配分による重み計算
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（ロット丸め、aggregate cap）

- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- AI
  - news_nlp: raw_news を LLM（OpenAI）でセンチメントスコア化し ai_scores テーブルへ書込
  - regime_detector: ETF 等の MA 乖離とマクロニュースの LLM センチメントを統合して市場レジーム判定

- ツール
  - .env 設定ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

- ロギング / プロセス制御
  - 共通ログ設定（logs/<app_name>.log、日次ローテーション）
  - プロセス優先度設定（高優先度化）・CPU affinity 設定ユーティリティ

---

## セットアップ

前提:
- Python 3.9+（コードは型注釈を使用）
- SQLite は標準ライブラリで利用可能
- OS によっては psutil の一部機能（プロセス優先度設定等）で権限が必要

1. リポジトリをクローン
   - git clone <repo_url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - プロジェクトに requirements.txt がある場合はそれを使ってください。なければ最低限以下をインストールします:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env 作成
   - ./config_setup を使うと対話的に .env を生成できます（推奨）:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考にしてください。

5. DB / ディレクトリ作成
   - デフォルトでは以下ファイル・ディレクトリを使用します:
     - data/ (実行時に自動作成される場合あり)
     - data/monitoring.db (SQLite, 監視データ)
     - data/paper_trading.db (ペーパートレード用 SQLite)
     - data/kabusys.duckdb（デフォルトの DuckDB は data/kabusys.duckdb）
     - logs/ （ログ）

6. 環境変数（重要）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を使う場合:
     - OPENAI_API_KEY
   - よく使うオプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア。開発時のみ注意）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）

---

## 使い方

以下は主要な実行エントリポイントと例です。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）の起動
  - python -m kabusys.run_execution
  - 補足:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます
    - 起動時に data/stop_requested.flag が存在すると起動しません
    - 実行中に data/stop_requested.flag が作成されるとエンジンが停止します
    - プロセス優先度は起動時に high に設定されます（可能な環境で）

- Monitoring（監視ループ）の起動
  - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 補足:
    - Monitoring は環境にかかわらず本番 sqlite_path を参照して監視用テーブルを初期化します
    - stop フラグファイル: data/stop_requested.flag を検知してループを終了

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI / リサーチ API（プログラムから呼び出す）
  - news_nlp のスコアリング:
    - Python から呼び出す例:
      - from kabusys.ai.news_nlp import score_news
      - import duckdb
      - conn = duckdb.connect("data/kabusys.duckdb")
      - from datetime import date
      - score_news(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, date(2026,4,1), api_key="YOUR_OPENAI_KEY")

- ログ
  - logs/<app_name>.log に日次ローテートでログが蓄積されます（例: logs/execution.log, logs/monitoring.log）
  - コンソールへは stdout にログを出力します（stderr ではない点に注意）

- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込むことで実行中の ExecutionEngine に停止シグナルを送ります
  - ExecutionEngine / Monitoring は stop_requested.flag（data/stop_requested.flag）を検知して終了します
  - kill.flag の場所は Settings.kill_flag_path（デフォルト data/kill.flag）

---

## よく使う環境変数（まとめ）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行制御 / 環境
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
  - KILL_FLAG_CLEAR_ON_START: 0|1

- DB / パス
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
  - PID_FILE_PATH (デフォルト data/execution.pid)
  - KILL_FLAG_PATH (デフォルト data/kill.flag)

- Paper trading
  - PAPER_FILL_MODE: instant|partial|never|reject

- OpenAI
  - OPENAI_API_KEY（news_nlp / regime_detector を使用する場合は必須）

- Monitoring
  - MONITOR_POLL_INTERVAL（秒、デフォルト 60）

---

## ディレクトリ構成（要約）

以下は src/kabusys 以下の主なファイル・パッケージとその説明です（抜粋）。

- kabusys/
  - __init__.py — パッケージ定義（__version__ 等）
  - config.py — 環境変数・設定読み込み・Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py — ニュースの LLM センチメントスコアリング
    - regime_detector.py — 市場レジーム判定
    - __init__.py

  - monitoring/
    - monitoring_db.py — SQLite 監視 DB レイヤー（テーブル初期化・読み書き）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文関連監視（file 参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 複数モニタの統合ループ
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — 通知送信（LINE 等）※実装ファイルが存在する想定

  - execution/
    - execution_engine.py — 発注エンジン本体（EngineConfig など）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      （発注・リスク管理・ブローカ抽象化）
    - ...（派生ファイル）

  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算（ロット丸め・aggregate cap）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
    - __init__.py

  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity
    - __init__.py

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
    - validate_config.py で存在チェックとパース検証（PyYAML 必須）を行います

- data/
  - monitoring.db, paper_trading.db, kabusys.duckdb, execution.pid, kill.flag, stop_requested.flag など（実行時に使用）

- logs/
  - <app_name>.log（例: execution.log, monitoring.log）

---

## トラブルシューティング / 注意点

- 必須環境変数が未設定だと起動時にエラーになります。まずは `python -m kabusys.config_setup` と `python -m kabusys.validate_config` を実行して確認してください。
- OpenAI を使う機能は API キー（OPENAI_API_KEY）を必要とします。使用しない場合は該当モジュールを呼ばないでください。
- psutil によるプロセス優先度設定は OS によっては権限不足で失敗します。失敗時は警告を出して続行します。
- データベースのマイグレーション（monitoring_db.init_monitoring_db）は冪等に設計されています。初回起動時にテーブルを作成します。
- ペーパートレードと本番の DB は分離されます（KABUSYS_ENV=paper_trading の場合のみ paper_sqlite_path を使用）。

---

## 参考コマンドまとめ

- .env ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution 起動:
  - python -m kabusys.run_execution

- Monitoring 起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 呼び出し（例: news scoring の簡易実行）
  - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, os; from datetime import date; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, date(2026,4,1), api_key=os.environ.get('OPENAI_API_KEY')))"

---

必要であれば、この README の英語版や、各モジュール（ExecutionEngine の起動オプション、AlertManager の設定方法、DB スキーマ詳細等）の詳細ドキュメントも作成します。どの箇所を深掘りしたいか教えてください。