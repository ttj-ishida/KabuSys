# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）。  
ポートフォリオ構築／ポジションサイズ計算、監視（Monitoring）、Execution エンジン、研究用ファクター計算、AI（ニュース NLP / レジーム判定）などの機能を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群で構成されています。

- データ解析・研究（DuckDB を用いたファクター計算、将来リターン計算、IC 等）
- ポートフォリオ構築（候補選定、重み付け、セクター制約、ポジションサイズ計算）
- Execution エンジン（実口座／ペーパートレード用のブローカー抽象化）
- 監視（System / Trade / Risk の監視、Kill Switch、アラート連携）
- AI 機能（OpenAI を用いたニュースセンチメント、マクロセンチメント → レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計上、研究・シミュレーション用コードは本番発注ロジックにアクセスせず、データベースやファイルを介して明確に分離されています。

---

## 主な機能一覧

- config 管理（.env の自動ロード／ウィザード）
- 環境検証 CLI（`kabusys.validate_config`）
- Execution 起動スクリプト（本番 / paper_trading 切替、pid / stop フラグ制御）
- Monitoring 起動スクリプト（定期ポーリング、stop フラグ検知、MONITOR_POLL_INTERVAL 指定可）
- 監視 DB（SQLite）用の永続化層と操作 API（system_status, trade_logs, positions, risk_logs, dashboard）
- RiskMonitor（ドローダウン・ポジション上限監視）
- KillSwitch（条件に応じて `data/kill.flag` を書き込み Execution を停止）
- AI: ニュース NLP（OpenAI）を使った銘柄別センチメントスコア生成
- AI: レジーム判定（ETF + マクロニュース合成による daily レジーム）
- Portfolio モジュール（候補選定、等重／スコア加重、セクターキャップ、ポジションサイズ計算）
- Utilities: ログセットアップ、プロセス優先度 / CPU affinity 設定
- Tools: Paper Trading 検証レポート生成

---

## 前提・依存

（主な）ランタイム依存：

- Python 3.10+
- duckdb
- psutil
- openai（AI 機能を使用する場合）
- sqlite3（標準ライブラリ）
- （オプショナル）PyYAML（`validate_config` の YAML 検証を有効にする場合）

requirements.txt をプロジェクトに追加していればそちらを参照してください。ない場合は必要なパッケージを手動でインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / 展開し、仮想環境を作成して有効化する
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （開発用）pip install pyyaml

3. .env の作成（推奨: ウィザードを利用）
   - python -m kabusys.config_setup
     - 対話形式で .env を作成 / 更新します。
   - ウィザード終了後、`python -m kabusys.validate_config` で設定検証を行ってください。
     - 警告をエラー扱いにするには `--strict` を付けます。

4. データディレクトリを作成（自動生成される部分もありますが事前に用意しておくと安全）
   - mkdir -p data logs

5. 環境変数（主に .env に設定）
   - 必須:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY
   - 任意（デフォルト値があるもの）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — default: data/paper_trading.db
     - LOG_LEVEL — default: INFO
     - LOG_DIR — default: logs
     - MONITOR_POLL_INTERVAL — 監視ループの秒間隔（run_monitoring 用、default: 60）
   - 自動ロード:
     - プロジェクトルートに `.env` / `.env.local` があれば、起動時に自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

---

## 使い方

### 1) 設定の準備

- .env ウィザード
  - python -m kabusys.config_setup
  - 作成後: python -m kabusys.validate_config （`--strict` オプションで警告も失敗扱い）

### 2) 実行エンジン（Execution）を起動

- 起動:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient が使用され、発注・イベントは paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録され、本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動を行いません（停止フラグ）。
  - 実行中は PID ファイル（デフォルト: data/execution.pid）を作成します。
  - 実行エンジンは起動直後にプロセス優先度を "high" に設定しようとします（権限不足時は警告のみ）。

- 停止:
  - Execution は外部からの停止フラグ（data/stop_requested.flag または data/kill.flag の運用に依存）により安全停止します。`KillSwitch` は必要条件が満たされると `data/kill.flag` を書き込み Execution に停止シグナルを送ります。

### 3) 監視プロセスを起動

- 起動:
  - python -m kabusys.run_monitoring
- 特記事項:
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - Monitoring は KABUSYS_ENV に関わらず Settings.sqlite_path（本番監視 DB）を使用します（監視は本番 DB を見る想定）。
  - stop フラグファイル (project_root/data/stop_requested.flag) を検知するとループを終了します。

### 4) Paper Trading 検証レポート生成

- コマンド:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB:
  - 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
- 出力:
  - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を標準出力に表示し PASS/FAIL 判定を行います。

### 5) AI 機能（ニュース NLP / レジーム判定）

- OpenAI API キーが必要（OPENAI_API_KEY または関数引数で指定）。
- プログラム API:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - レスポンスのリトライやフォールバックロジックを備えていますが、API キー未設定時は例外になります。

### 6) ログ

- ログ設定は统一化されており、各アプリ（app_name）ごとに日次ローテートのログファイルを生成します。
- デフォルトログディレクトリ: logs/
- 起動例（デバッグ用）:
  - LOG_LEVEL=DEBUG python -m kabusys.run_execution

---

## 停止／フラグ制御

- stop_requested.flag
  - run_execution / run_monitoring がループを終了するために参照するフラグファイル。ファイルパスはスクリプト内で project/data/stop_requested.flag として参照されています。
- kill.flag
  - KillSwitch（監視側）によって作成されるフラグ。存在すると Execution 側は停止する仕組み（Execution は起動時に設定を参照して処理します）。
  - Settings.kill_flag_clear_on_start = "1" にすると起動時に kill.flag を自動クリア（本番環境では 0 推奨）。

---

## ディレクトリ構成

（src 以下を基にした主要ファイル・パッケージ構成）

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 設定検証 CLI
  - run_execution.py       — Execution エンジン起動スクリプト
  - run_monitoring.py      — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py       (ファイルはこのリポジトリに含まれている想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       (アラート処理実装がある想定)
  - execution/
    - execution_engine.py    (Execution ロジック)
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - data/                   — デフォルトで使用される DB / フラグファイル / PID 等
    - monitoring.db         (SQLITE_PATH)
    - paper_trading.db      (PAPER_TRADING_SQLITE_PATH)
    - kabusys.duckdb        (DUCKDB_PATH)
    - execution.pid
    - kill.flag
    - stop_requested.flag
  - config/                 — yaml 設定群（system_config.yaml 等）

（上記は主要ファイル列挙です。実際のレイアウトはリポジトリの内容に依存します。）

---

## 開発・デバッグのヒント

- 設定を変更したらまず validate_config でチェック：
  - python -m kabusys.validate_config --strict
- ログを詳細に見るには LOG_LEVEL=DEBUG またはアプリ起動時に level 引数を渡します。
- AI 機能の単体テストでは OpenAI 呼び出し関数（_call_openai_api 等）をモックすることを推奨します（ソース内でもモックしやすい設計にしています）。
- DuckDB のクエリは研究モジュール内で行われるため、ローカルで DuckDB ファイルを準備してから実行すると再現性が高くなります。

---

この README はプロジェクト中の docstring / 起動スクリプトの挙動を基に作成しています。運用に際しては `.env.example`（存在する場合）や config/*.yaml、実際のドキュメント（PortfolioConstruction.md 等）も併せて参照してください。質問や補足が必要であれば教えてください。