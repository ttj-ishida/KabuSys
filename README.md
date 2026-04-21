# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ兼起動スクリプト群）です。  
このリポジトリには、戦略構築／ポートフォリオ算出、発注エンジン、監視機構、研究用ユーティリティ、AI（ニュース NLP / レジーム判定）などが含まれます。

---

## 概要（Project overview）

KabuSys は以下の主要機能を持つモジュール設計になっています。

- 戦略・ポートフォリオ構成（銘柄選定、重み付け、ポジションサイズ算出）
- 発注実行エンジン（ExecutionEngine。実発注／ペーパートレードを切替可能）
- 監視系（システム健全性、注文ログ、リスク監視、Kill Switch）
- 研究用モジュール（ファクター計算、将来リターン、IC計算、特徴量探索）
- AI連携（ニュースのセンチメントスコア化、マクロセンチメントとレジーム判定）
- 運用支援ツール（.env 設定ウィザード、設定検証、ペーパー検証レポートなど）

設計方針の一例：
- データ永続化は SQLite（監視・発注ログ等）と DuckDB（時系列データ分析）を併用
- 環境変数 / .env による設定管理
- 本番／ペーパートレードの DB を明確に分離
- OpenAI 等外部 API 呼び出しは明示的にキーを渡して安全に扱う

---

## 主な機能一覧

- portfolio
  - 銘柄選定（select_candidates）
  - 等金額 / スコア加重重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ算出（calc_position_sizes）
  - セクターキャップ・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
- execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント抽象化（Paper / Live 切替）
  - リスク管理（RiskManager）・注文管理（OrderManager）
- monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス/データ鮮度監視）
  - TradeMonitor（注文滞留、異常約定検出）
  - RiskMonitor（ドローダウン・ポジション上限検出）
  - KillSwitch（フラグファイルによる強制停止）
  - MonitoringEngine（上記を束ねるポーリングループ）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC、統計サマリ（feature_exploration）
- ai
  - ニュース NLP（OpenAI を用いた銘柄センチメント、ai_scores テーブルへの書込）
  - レジーム判定（ETF MA とマクロセンチメントの合成）
- utils
  - ログ設定（setup_logging）
  - プロセス優先度 / CPU affinity 設定（set_process_priority, set_cpu_affinity）
- tools
  - .env ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート生成（tools/paper_verification_report.py）

---

## 必要条件（Dependencies）

推奨 Python バージョン: 3.10+

主な Python パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config ファイルの検証に任意）
- （その他、環境に応じて必要なパッケージ）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（実プロジェクトでは requirements.txt を用意して pip install -r することを推奨します）

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 依存ライブラリをインストール（上記参照）
4. .env の作成（推奨）
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（.env.example がある場合は参照）
5. 設定検証:
   ```
   python -m kabusys.validate_config
   # 警告も厳密に扱う場合:
   python -m kabusys.validate_config --strict
   ```
6. data/ および logs/ ディレクトリは起動時に自動で作成されますが、権限等で失敗する可能性があるため事前に作成しておくと確実です。

重要な環境変数（抜粋）:
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB, デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI モジュールを使う場合）
  - LOG_LEVEL（デフォルト: INFO）
  - LOG_DIR（デフォルト: logs/）
- 監視用
  - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）、デフォルト 60）
  - PID_FILE_PATH（ExecutionEngine の PID ファイルパス、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（KillSwitch のフラグファイルパス、デフォルト: data/kill.flag）

例: 最小 .env（安全上はトークン等は実値で設定してください）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（起動・ツール）

- 監視ループを起動（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（例: 30秒）
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します（`KABUSYS_ENV` に依存しない）。

- 発注エンジンを起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、記録先は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）になります（本番 DB と完全に分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 実行中は data/execution.pid に PID が書かれます。停止は stop フラグ（stop_requested.flag）または KillSwitch による kill.flag によって行われます。

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを個別指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
  ```

- AI 関連（プログラムから利用）
  - ニュースセンチメントを生成して ai_scores に書き込む:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...) の接続
    score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定（regime_detector.score_regime）も同様に呼べます（モジュール内説明参照）。

- ロギング
  - 各スクリプトは kabusys.utils.logging_setup.setup_logging を使ってログを stdout と logs/<app_name>.log（日次ローテーション）に出力します。
  - LOG_DIR を設定して出力先を変更可能。

- 停止フラグ / Kill Switch
  - run_monitoring.py / run_execution.py はプロジェクトの data/stop_requested.flag（場所はスクリプト内で定義）を監視し、存在を検知するとループ／エンジンを終了します。
  - KillSwitch（監視モジュール側）は条件を満たしたときに data/kill.flag を作成し、ExecutionEngine に停止を促します（ExecutionEngine は起動時に KILL_FLAG_CLEAR_ON_START の設定に応じてクリアするか制御可能）。

---

## 開発メモ / 実装上の注意

- monitoring は監視用 SQLite（settings.sqlite_path）を使用します。init_monitoring_db() は起動時にテーブル作成・マイグレーションを行います（冪等）。
- run_execution は KABUSYS_ENV によって paper_trading 用 DB を切り替え、MockBrokerClient を使う設計になっています（本番 DB と分離）。
- OpenAI 呼び出しを行う AI モジュールは、環境変数 OPENAI_API_KEY または引数でキーを受け取ります。APIエラーに対してはリトライ/フェイルセーフを実装しています（ログを参照）。
- DuckDB を使って時系列データ（prices_daily / raw_financials / raw_news 等）を SQL ベースで処理する実装が多く含まれます。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル／モジュールの構成（src/kabusys を想定）:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理、自動 .env ロード
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - portfolio/
    - portfolio_builder.py    — 銘柄選定・重み付け
    - position_sizing.py      — 株数決定 / キャップ / スケールダウン
    - risk_adjustment.py      — セクターキャップ / レジーム乗数
  - monitoring/
    - monitoring_db.py        — SQLite 用永続化層（テーブル作成・CRUD）
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （注文監視用: 滞留・価格異常など）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - monitoring_engine.py    — 各モニタを束ねるループ
    - kill_switch.py          — Kill Switch 実装（フラグファイル）
    - alert_manager.py        — （通知管理）
  - execution/
    - execution_engine.py     — 発注エンジン（EngineConfig, run_session など）
    - broker_factory.py       — BrokerClient の生成（Mock / Live 切替）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - research/
    - factor_research.py      — momentum / volatility / value 等
    - feature_exploration.py  — forward returns / IC / summary 等
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（MA + macro sentiment）
  - tools/
    - paper_verification_report.py — Paper Trading 用検証レポート生成
  - data/                     — （実行時に使用する DB・フラグファイル等を配置）
  - logs/                     — ログファイル出力先（デフォルト）

---

## よくある手順例

- 開発用（ペーパートレード）でエンジンを動かす
  1. .env で KABUSYS_ENV=paper_trading を設定
  2. 必要なトークンやパスを .env に設定
  3. 起動:
     ```
     python -m kabusys.run_execution
     ```
  4. 監視を別プロセスで起動:
     ```
     python -m kabusys.run_monitoring
     ```

- 停止方法
  - 監視／実行スクリプトは data/stop_requested.flag を監視しています。停止させたい場合はファイルを作成してください（あるいは kill -TERM PID）。
  - KillSwitch による強制停止は data/kill.flag を作成します（監視モジュールが作成）。

---

## 最後に

この README はコードベースに含まれるモジュール群の概要と運用上の注意をまとめたものです。各モジュールにはより詳細なドキュメント（モジュール内 docstring / コメント）が含まれています。運用前に必ず `python -m kabusys.validate_config` を実行して設定の整合性を確認してください。

必要であれば、README にサンプル .env、systemd unit ファイル例、Dockerfile などの運用資料を追加します。どの情報が欲しいか教えてください。