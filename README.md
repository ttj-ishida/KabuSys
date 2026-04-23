# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買・リサーチ・監視ツール群（KabuSys）です。本 README はコードベースの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

注意: README はソースの主要部分（src/kabusys/**）を元に作成しています。実運用前に必ず `python -m kabusys.validate_config` で設定検証を行ってください。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントを含むモジュール群です。

- ExecutionEngine: ブローカークライアントを使った発注エンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働・注文・リスクを監視し、Kill Switch（停止フラグ）やアラートを生成
- Portfolio: 候補選定・配分・ポジションサイズ計算などポートフォリオ構築ロジック
- Research: DuckDB を用いたファクター計算・特徴量探索
- AI: ニュースの自然言語処理（OpenAI）を用いたセンチメント評価・レジーム判定
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト
- Utilities: ロギング設定、プロセス優先度設定、設定読み込み等

設計上のポイント:
- .env ファイル / 環境変数から設定を読み込み、Settings クラスでアクセス
- DuckDB は分析用（prices_daily 等のテーブル参照）、SQLite は監視・トレードログ保存用
- Paper Trading は本番 DB と分離（デフォルト: data/paper_trading.db）
- AI 機能は OpenAI API キーが必要（失敗時はフォールバック動作）

---

## 主な機能一覧

- run_execution.py
  - ExecutionEngine の起動スクリプト
  - KABUSYS_ENV=paper_trading の場合は MockBroker 使用・別 SQLite に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ対応

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60s）
  - 監視データは Settings.sqlite_path（監視 DB）へ永続化

- config_setup.py
  - 対話式 .env 作成ウィザード（必須環境変数の入力支援）

- validate_config.py
  - .env と config/*.yaml の検証（--strict で警告も FAIL 扱い）

- tools/paper_verification_report.py
  - Paper Trading DB（デフォルト data/paper_trading.db）から統計を集計し PASS/FAIL 判定レポートを出力

- portfolio/*
  - 候補選定、重み計算（等配分／スコア重み）、セクターキャップ、レジーム乗数、ポジションサイズ計算（単元丸め含む）

- research/*
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 接続を受ける純粋関数群）
  - 将来リターン計算、IC 計算、統計サマリー

- ai/*
  - news_nlp: raw_news から銘柄ごとのニュースをまとめて LLM へ送信しセンチメントを ai_scores へ書き込み
  - regime_detector: ETF（1321）MA200 と LLM マクロセンチメントを合成して日次レジームを判定、market_regime テーブルへ保存

- monitoring/*
  - monitoring_db: SQLite スキーマ初期化・CRUD ユーティリティ
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager 等

- utils/*
  - logging_setup: stdout + 日次ローテーションログハンドラ設定
  - process_priority: クロスプラットフォームでプロセス優先度・CPU affinity を設定

---

## 前提条件 / インストール

推奨 Python バージョン: 3.10 以上（型注釈の構文等のため）

主要依存パッケージ（例）:
- duckdb
- psutil
- openai（AI 機能利用時）
- PyYAML（validate_config で YAML 検証を行う場合、任意）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# またはプロジェクトに requirements.txt がある場合は:
# pip install -r requirements.txt
```

注意:
- SQLite は標準ライブラリとして Python に同梱されています。
- 自動で .env をロードする挙動はデフォルトで有効です（プロジェクトルートの .env / .env.local を読み込み）。テスト等で無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要 / 推奨:
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: AI 機能（news_nlp, regime_detector）を利用する場合に必要
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 環境で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）
- PAPER_FILL_MODE: paper_trading の MockBroker のフィルモード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: ファイルパス上書き可能

詳細は `src/kabusys/config.py` の Settings クラスを参照してください。

.env 作成支援:
```bash
python -m kabusys.config_setup
```

設定検証:
```bash
python -m kabusys.validate_config        # 警告は許容
python -m kabusys.validate_config --strict  # 警告もエラー扱い
```

---

## セットアップ（初期手順の例）

1. リポジトリをクローンし、仮想環境を作成して依存をインストール
2. `.env` を作成（`python -m kabusys.config_setup` を推奨）
3. 必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を設定
4. DuckDB / SQLite のファイルパス（デフォルトは data/ 以下）を確認
5. 設定検証を実行
   ```bash
   python -m kabusys.validate_config
   ```
6. （任意）データベース・テーブルの作成やデータ投入（prices_daily や raw_news 等は分析/AI 機能で参照）

---

## 使い方（起動例）

- ExecutionEngine（本番または paper_trading）起動:
  ```bash
  # .env を用意した上で
  python -m kabusys.run_execution
  ```

  - Paper Trading の場合は KABUSYS_ENV=paper_trading を設定すると専用の PAPER_TRADING_SQLITE_PATH を使用します。
  - 起動時に data/execution.pid（デフォルト）が作成されます。停止は monitoring の KillSwitch / stop フラグで行います（stop_requested.flag）。

- System Monitor 起動:
  ```bash
  # デフォルトポーリング間隔 60 秒（MONITOR_POLL_INTERVAL で上書き可）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  - 監視は Settings.sqlite_path に書き込みます（monitoring DB）。
  - run_monitoring は stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成:
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/db
  ```

- AI 機能（ニューススコア算出 / レジーム判定）
  - OpenAI API キーを設定（OPENAI_API_KEY）。
  - DuckDB に raw_news / news_symbols / prices_daily 等のテーブルが必要。
  - 呼び出し例（モジュール関数をスクリプト等から使う）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ログ
  - デフォルト: stdout と logs/<app_name>.log（日次ローテーション）へ出力
  - ログディレクトリは LOG_DIR 環境変数で上書き可能

---

## 停止・Kill Switch

- Kill Switch は監視モジュールが発動すると `data/kill.flag`（デフォルト）を書き込み、ExecutionEngine に停止シグナルを送ります。
- 外部から強制停止を行う場合は stop フラグ `data/stop_requested.flag`（run_* スクリプトで使用）を作成すると各プロセスが検知して終了します。
- ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では危険なので 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主なディレクトリ / ファイル（src/kabusys を基準）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

  - execution/               — Execution 関連（broker_factory 等）
    - (発注エンジン / OrderManager / Reconciler / RiskManager など)

  - monitoring/
    - monitoring_db.py       — SQLite スキーマ初期化 / 永続層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py

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
    - news_nlp.py
    - regime_detector.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (存在しない場合は validate_config が警告を出します。)

- data/
  - デフォルトの DB / フラグ / PID 等を格納（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## 開発時の注意点 / ヒント

- データのルックアヘッドバイアスに注意: research / ai / regime_detector などは target_date より以前のデータのみを参照する実装方針です。関数は明示的に target_date を受け取るので、テスト時も日付を固定して実行してください。
- ペーパートレードは本番 DB と明確に分離されるよう設計されています。KABUSYS_ENV=paper_trading を利用してください。
- ログレベル等は .env の LOG_LEVEL で変更できます。
- OpenAI 呼び出し部分はリトライやバックオフ制御を行っていますが、API 使用量・レート制限に注意してください。
- monitor / execution のスクリプトは stop フラグファイルを使用するため、CI / 管理スクリプトからファイルを作成 / 削除することにより運用できます。

---

## 参考コマンドまとめ

- .env ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動:
  python -m kabusys.run_execution

- Monitoring 起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はソースコードの解説を簡潔にまとめたものです。各モジュールの詳細な仕様・数式・設計意図はソース内の docstring（コメント）をご参照ください。運用前には必ず設定検証と（可能であれば）ステージング環境での検証を行ってください。