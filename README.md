# KabuSys (README)

KabuSys は日本株向けの自動売買システムのコアライブラリ群です。取引実行エンジン・監視機能・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント／レジーム判定）などを含むモジュール群で構成されています。

以下はこのリポジトリの概要、主な機能、セットアップ方法、実行方法、およびディレクトリ構成の説明です。

---

## プロジェクト概要

- 目的: 日本株の自動売買システムのコアロジック（発注・リスク管理・監視・データ処理・リサーチ・AI補助）を提供する。
- 設計方針:
  - 実行ロジック（Execution）と監視（Monitoring）を分離。
  - DuckDB を用いた時系列データ処理、SQLite を用いた監視・発注ログ永続化。
  - Paper Trading 用の完全分離 DB をサポート（KABUSYS_ENV）。
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメント/レジーム判定を実装（オプション）。
  - .env ファイルからの環境変数自動読み込み機構あり（必要に応じて無効化可能）。

---

## 主な機能一覧

- Execution（発注周り）
  - ExecutionEngine（エンジン起動 / セッション実行）
  - BrokerClientFactory（実ブローカ / モックの切り替え）
  - OrderManager / OrderRepository / Reconciler（注文管理・再同期）
  - RiskManager（発注前チェック）

- Monitoring（監視）
  - SystemMonitor（CPU/メモリ/ディスク・プロセス確認・データ鮮度チェック）
  - TradeMonitor（滞留注文、約定異常検出）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - MonitoringEngine（各 Monitor を束ねたポーリング）
  - AlertManager（LINE Push を使った通知）
  - streamlit ベースの監視ダッシュボード

- Portfolio（銘柄選定 / 配分）
  - 候補選定（スコア降順）
  - 等金額 / スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - 株数計算（risk_based / equal / score）

- Research（データ処理・ファクター）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算 / IC（Information Coefficient） / 統計サマリー

- AI
  - news_nlp.score_news: ニュース記事から銘柄別センチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースで市場レジームを判定して market_regime に保存

- Tools
  - paper_verification_report: Paper Trading 用 SQLite を解析して検証レポートを出力

---

## 必要要件・依存パッケージ

- Python 3.10 以上（型アノテーションの Union 演算子等を利用）
- 必須（ランタイムで必要になる主要パッケージ）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
- SQLite は標準ライブラリに含まれるため追加不要。

例（pip）:
```
pip install duckdb psutil requests openai streamlit
```

プロジェクトに requirements.txt があればそれを使ってインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存パッケージをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```
4. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと、起動時に自動で読み込まれます。
   - 自動読み込みを無効化するには、環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API トークン）
     - KABU_API_PASSWORD（kabuステーション API パスワード）
   - OpenAI を使用する場合:
     - OPENAI_API_KEY（AI 機能で使用）
   - その他の主な設定（デフォルト値は括弧内）:
     - KABUSYS_ENV: one of development | paper_trading | live （default: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - PAPER_FILL_MODE: instant | partial | never | reject （default: instant）
     - LOG_LEVEL: DEBUG|INFO|... （default: INFO）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default: 60）

5. data ディレクトリなど初期ファイル生成（任意）
   ```
   mkdir -p data
   ```

---

## 使い方（代表的なコマンド）

- 実行エンジン（Execution）を起動
  - 実運用（本番 DB を使用）:
    ```
    KABUSYS_ENV=live python -m kabusys.run_execution
    ```
  - Paper Trading（Mock broker + data/paper_trading.db を使用）:
    ```
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
  - 補足:
    - 起動時に data/stop_requested.flag が存在すると起動しません。
    - 実行中は data/execution.pid に PID を書きます。停止は kill flag 等で制御します。

- 監視プロセス（Monitoring）を起動
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を調整できます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を参照（KABUSYS_ENV に依存せず production DB を使う設計）。

- Paper Trading 検証レポートを出力（ツール）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で別 DB を指定できます。デフォルトは data/paper_trading.db。

- 監視ダッシュボード（Streamlit）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - ダッシュボードは監視 DB を読み取り専用で開きます。監視プロセスが DB を作成している必要があります。

- AI 機能（ニューススコアリング / レジーム判定）
  - Python から呼び出す例:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, date(2026, 4, 15), api_key="sk-...")
    ```
    ```py
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, date(2026, 4, 15), api_key="sk-...")
    ```
  - 注意: OPENAI_API_KEY または api_key 引数が必要です。API 呼び出しはリトライ・フェイルセーフ処理あり。

- 停止制御
  - ExecutionEngine を外部から安全に停止するには、`data/kill.flag` に停止理由を書き込む（KillSwitch が設定されている場合）。
  - 監視ループは `src` からプロジェクトルートの `data/stop_requested.flag` を検知して終了します。

---

## 主要な環境変数（Settings に基づく）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY（AI 機能で必要）
- LINE_CHANNEL_ACCESS_TOKEN（AlertManager が LINE を使う場合）
- LINE_USER_ID（AlertManager が LINE を使う場合）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject, default: instant)
- PID_FILE_PATH (default: data/execution.pid)
- KILL_FLAG_PATH (default: data/kill.flag)
- KABUSYS_ENV (development|paper_trading|live; default: development)
- LOG_LEVEL (DEBUG|INFO|..., default: INFO)
- CPU/MEMORY/DISK 閾値など監視パラメータも環境変数で上書き可（CPU_THRESHOLD_PCT 等）

---

## 停止 / フラグファイル

- data/stop_requested.flag: run_monitoring/run_execution が監視している停止フラグ（存在すれば安全に終了）。
- data/kill.flag: KillSwitch が書き込む停止要求（ExecutionEngine に通知する用途）。

---

## ディレクトリ構成（要約）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI 呼び出し、ai_scores 登録）
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - monitoring_db.py — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - alert_manager.py — LINE 通知
    - kill_switch.py — kill.flag 管理
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ... — 発注 / 再同期関連
    - broker_factory.py, execution_engine.py, order_repository.py, など（発注実装）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・解析
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (実行時に使用される想定ディレクトリ)
    - monitoring.db（SQLite）
    - paper_trading.db（Paper Trading 専用 SQLite）
    - kabusys.duckdb（DuckDB）
    - execution.pid / stop_requested.flag / kill.flag

（実際のリポジトリには上の他にも補助モジュールが含まれます。ここでは主要ファイルを抜粋しています。）

---

## 開発上の注意点 / 補足

- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を検出して行います。自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番データベースと完全に分離され、MockBrokerClient を使って注文処理をエミュレートします。
- データベースマイグレーションは簡易に実装されており、monitoring_db.init_monitoring_db() は必要なカラムの追加（例: peak_value、latency_ms）を冪等で行います。
- OpenAI 周りは API エラーに対するリトライやフェイルセーフ（失敗時は 0 相当で継続）を備えていますが、APIキーや料金に注意してください。
- process_priority.set_process_priority() を呼び出してプロセス優先度を設定します（権限不足等で失敗する可能性あり、その場合はログで警告して継続します）。

---

必要であれば README の各セクションを拡張して、詳細な環境変数一覧（例: .env.example）、より詳しい起動手順、テスト方法、API ドキュメント断片などを追記します。どの部分を詳しく書いてほしいか教えてください。