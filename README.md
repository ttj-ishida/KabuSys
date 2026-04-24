# KabuSys

日本株自動売買システムのコアライブラリ群と起動スクリプト集です。  
本リポジトリはトレーディング戦略・ポートフォリオ構築、監視、ペーパートレード検証、AI を用いたニュース評価などの機能を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

- DuckDB / SQLite を使った時系列データ分析・永続化
- 注文発行（本番 / ペーパートレード切替可能）を担う ExecutionEngine
- システム稼働状況や注文・リスクを監視する Monitoring
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- リサーチ用のファクター計算・特徴量解析
- OpenAI を利用したニュースセンチメント評価 / 市場レジーム判定
- 簡易 CLI ツール（設定ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として、可能な限り副作用を分離した純粋関数群、DB 書き込みは永続化層に集約、外部 API は必要箇所で明確に扱います。

---

## 主な機能一覧

- 設定
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行エンジン
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - KABUSYS_ENV による挙動切替（development / paper_trading / live）
  - paper_trading 時は MockBroker を利用し、専用 SQLite（data/paper_trading.db）に記録

- 監視
  - System / Trade / Risk 各モニタ実装
  - MonitoringEngine と単体起動用スクリプト: python -m kabusys.run_monitoring
  - kill.flag による ExecutionEngine 停止指令（KillSwitch）
  - 監視ログ永続化（SQLite）およびダッシュボード row 保持

- ポートフォリオ
  - 候補選定（select_candidates）
  - 等重・スコア加重の重み計算
  - ポジションサイズ算出（risk_based / equal / score）
  - セクター上限適用・レジーム乗数

- リサーチ
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL 実行）
  - 将来リターン, IC 計算, ファクター要約

- AI（OpenAI）
  - ニュースをまとめて銘柄別センチメントを取得（news_nlp.score_news）
  - マクロニュース + ETF MA を使った市場レジーム判定（regime_detector.score_regime）

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（開発 / 実行）

下記は一般的な手順例です。実環境向けには .env を適切に設定してください。

1. Python 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存ライブラリのインストール（プロジェクトに requirements.txt がある想定）
   - 必須（主に本リポジトリで参照されるもの）:
     - duckdb
     - psutil
     - openai (AI 機能を使う場合)
     - PyYAML（設定検証で YAML をチェックする場合に任意）
   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

3. .env の作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - または手動で `.env` を作成（.env.example を参照してください）

4. 設定検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ（必要に応じて）:
   - `data/` や `logs/` は自動作成されますが、パーミッションに注意してください。

---

## 主要な環境変数（重要なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境切替
  - KABUSYS_ENV — "development" (デフォルト) / "paper_trading" / "live"

- DB / ログ
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_DIR — ログ保存先（デフォルト: logs/）
  - LOG_LEVEL — ログレベル（デフォルト: INFO）

- AI
  - OPENAI_API_KEY — OpenAI API キー（ニュースNLP / レジーム判定で使用）

- ペーパートレード挙動
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト: instant）

- プロセス / 制御
  - PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — KillSwitch が書込むフラグ（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする（"1" で有効、デフォルト: "0"）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）

注意: 必須環境変数が未設定だと Settings からの取得でエラーになります。config_setup で安全に設定してください。

---

## 使い方（起動例）

- 環境準備（例）
  ```
  source .venv/bin/activate
  python -m kabusys.config_setup   # .env を作る
  python -m kabusys.validate_config
  ```

- ExecutionEngine 起動（常用）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を用い、data/paper_trading.db に記録します。
  - 起動中に `data/stop_requested.flag` が作成されると安全に停止します。

- Monitoring 起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止は `data/stop_requested.flag` を作ることで行います（監視プロセスは検知して終了します）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（Python API）
  - ニューススコアリング:
    ```py
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn は duckdb.connect(...)
    score_news(duckdb_conn, target_date, api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="sk-...")
    ```

---

## 監視 DB（SQLite）スキーマ概要

monitoring_db.init_monitoring_db により作成される主要テーブル:

- system_status
  - recorded_at, cpu_percent, memory_percent, disk_percent, process_ok

- trade_logs
  - logged_at, event_type (Created/Sent/Filled など), client_order_id, code, side, qty, price, filled_qty, state, latency_ms

- positions
  - code (PRIMARY KEY), qty, avg_price, current_price, updated_at

- risk_logs
  - logged_at, event_type, metric_name, metric_value, threshold, detail

- dashboard
  - 単一行（id=1）で集計保持: updated_at, portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value

これらは MonitoringDB クラス経由で読み書きされることを想定しています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは `src/kabusys` 配下に実装があります。代表的なファイル・モジュールを示します。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定読み込み（Settings）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト

  - ai/
    - news_nlp.py             — ニュースを LLM でスコア化
    - regime_detector.py      — 市場レジーム判定
  - monitoring/
    - monitoring_db.py        — 監視 DB 操作
    - monitoring_engine.py    — MonitoringEngine（各モニタ束ねる）
    - system_monitor.py       — システム監視
    - trade_monitor.py        — （取引監視）※実装参照
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag の管理
    - alert_manager.py        — 通知管理（LINE 等）
  - execution/
    - execution_engine.py     — ExecutionEngine（主要処理）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/                (上記)
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ（logs/<app>.log）
    - process_priority.py     — プロセス優先度 / CPU affinity 設定

（補足）実装の詳細は各モジュールの docstring を参照してください。

---

## 運用上の注意 / ヒント

- 本番環境（KABUSYS_ENV=live）の場合は .env の取り扱いに注意し、機密情報は安全に保管してください。
- kill.flag による停止/自動クリア設定（KILL_FLAG_CLEAR_ON_START）は本番で自動クリアを有効にすると危険です。デフォルトは無効（"0"）。
- run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限により警告になることがありますが、処理自体は継続します。
- logs/ ディレクトリにアプリケーションごとの日次ローテートされたログが出力されます（30 日保持）。
- OpenAI を使う機能は API キーと利用コストを確認してから運用してください。API エラー時のフェイルセーフが組み込まれていますが、リトライやログに注意。

---

## さらに詳しく

- 各モジュールのドキュメント（docstring）には設計方針・アルゴリズムの詳細が記載されています。特に portfolio/*.py、research/*.py、ai/*.py はアルゴリズムに関する注釈を多く含みます。
- DB スキーマやマイグレーションの扱いは monitoring/monitoring_db.py を参照してください。

---

この README はコードベースの主要ポイントをまとめたものです。使い方や運用で不明点があれば、特定のモジュール・機能についてさらに詳しいドキュメントを作成しますのでお知らせください。