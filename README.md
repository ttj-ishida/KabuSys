# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視ツール群を集めた軽量フレームワークです。  
主な目的は、取引実行（ExecutionEngine）、監視（MonitoringEngine）、リサーチ（ファクター計算、特徴量解析）、AI を用いたニュースセンチメント評価などを一貫して扱えることです。

バージョン: 0.1.0

---

## 概要

- Python パッケージ構成で、Execution（発注/復旧/リスク管理）, Monitoring（システム監視・リスク監視・アラート）, Research（ファクター/特徴量/IC 解析）、Portfolio（銘柄選定・ウェイト・ポジションサイズ計算）、AI（ニュース NLP / レジーム判定）等の機能を提供します。
- ローカル DB に DuckDB（時系列・リサーチ用途）と SQLite（監視ログ・注文ログ等）を使用します。
- Paper Trading（模擬取引）モードをサポートし、本番 DB と分離して動作します。
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメントやマクロセンチメント評価のユーティリティを含みます（API キーが必要）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント抽象化（実ブローカー／MockBroker の切替）
  - OrderManager/OrderRepository による注文管理、Reconciler による自動復旧
  - リスク管理（RiskManager）による発注制御
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - 監視ログの永続化（SQLite）/ dashboard テーブルの upsert
  - LINE プッシュによるアラート送信（AlertManager）
  - kill.flag による ExecutionEngine 停止シグナル（KillSwitch）
  - Streamlit ベースの簡易ダッシュボード（streamlit_dashboard.py）
- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- Portfolio
  - 銘柄選定（スコア基準・順位基準）
  - ウェイト計算（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・aggregate cap など）
- AI
  - ニュース記事を集約して OpenAI に送信し銘柄ごとのセンチメントを ai_scores テーブルに書き込む（news_nlp.score_news）
  - マクロニュース + ETF MA200 を合成して市場レジームを判定し market_regime に書き込む（regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要条件（概略）

- Python 3.10+（typing の | 記法等を使用）
- 必要なパッケージ（抜粋）:
  - duckdb
  - psutil
  - openai
  - streamlit (ダッシュボードを使う場合)
  - requests
- SQLite は標準ライブラリで使用します。

（実際には pyproject.toml / requirements.txt があればそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows (PowerShell/Command Prompt)
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb psutil openai streamlit requests
   ```

4. 環境変数設定
   - 必須（実行するコンポーネントに依存）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY
   - その他（任意・デフォルト有り）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - PID_FILE_PATH / KILL_FLAG_PATH / 各種しきい値（CPU/MEM/DISK）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒。run_monitoring はこれで上書き可）

   .env / .env.local をプロジェクトルートに置けば自動で読み込まれます（環境による保護ルールあり）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. データディレクトリ準備
   ```bash
   mkdir -p data
   # 必要に応じて DuckDB や SQLite DB ファイルを用意
   ```

---

## 使い方

### 実行用スクリプト

- ExecutionEngine を起動（プロセス優先度を高に設定、paper_trading の場合は MockBroker を使用）
  ```bash
  # モジュールとして起動（推奨）
  python -m kabusys.run_execution

  # または直接
  python src/kabusys/run_execution.py
  ```

  特記事項:
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient が使われ、data/paper_trading.db に記録します（本番の monitoring.db と分離）。
  - プロセス優先度は set_process_priority("high") によって設定されます（権限不足や未サポート OS の場合はスキップされます）。
  - ExecutionEngine は PID ファイル（Settings.pid_file_path）を使用します。

- MonitoringEngine を起動（定期ポーリング）
  ```bash
  python -m kabusys.run_monitoring
  # MONITOR_POLL_INTERVAL を環境変数で変更可能（秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

  特記事項:
  - 監視ログは Settings.sqlite_path（デフォルト: data/monitoring.db）に書き込みます（環境にかかわらず本番 sqlite_path を使用する実装）。
  - MonitoringEngine は SystemMonitor / TradeMonitor / RiskMonitor を実行し、KillSwitch により kill.flag を書き込むことで ExecutionEngine に停止指示を送ります。
  - LINE の通知を行う場合は Settings.line_channel_access_token と Settings.line_user_id を設定してください。

### Streamlit ダッシュボード
- 監視 DB を読み込んでダッシュボード表示
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

### Paper Trading 検証レポート
- Paper Trading 用 SQLite を参照して簡易レポートを表示
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

### プログラム的な利用例（一部）
- AI ニューススコアの実行（DuckDB 接続を渡す）
  ```python
  from kabusys.ai.news_nlp import score_news
  # conn は duckdb.connect(...) の接続オブジェクト
  count = score_news(conn, target_date, api_key="sk-...")
  ```

- ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  results = calc_momentum(duckdb_conn, target_date)
  ```

- ポートフォリオ構築
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  ```

---

## 主要設定（Settings）と挙動のポイント

- .env 自動読み込み:
  - OS 環境変数 > .env.local > .env の優先順位で読み込む
  - プロジェクトルートは .git または pyproject.toml を基準に自動検出
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- KABUSYS_ENV:
  - 値: development / paper_trading / live
  - paper_trading の場合は発注処理がモックかつ DB が分離されます

- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）

- PAPER_FILL_MODE（paper_trading 用）:
  - instant / partial / never / reject（デフォルト: instant）

- 監視関連:
  - MONITOR_POLL_INTERVAL（run_monitoring で秒数を上書き）
  - PID_FILE_PATH / KILL_FLAG_PATH（ExecutionEngine と連携）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数 / 設定管理（.env のパーサを含む）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — MonitoringEngine 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント評価（OpenAI 呼び出し、ai_scores 書込）
  - regime_detector.py — レジーム判定（ETF + マクロセンチメント）
- execution/
  - order_manager.py, reconciler.py, ...（発注・状態同期・復旧ロジック）
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py
  - monitoring_engine.py — 各 Monitor を束ねる
  - alert_manager.py — LINE 通知
  - streamlit_dashboard.py — Streamlit ダッシュボード
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py — Momentum / Volatility / Value
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- monitoring/monitoring_db.py — 監視用 SQLite スキーマと MonitoringDB クラス

---

## 運用上の注意点

- 自動発注や実アカウント接続を行う場合は十分なテストとリスク管理（リスクパラメータ、kill.flag の挙動、ログ保存）を行ってください。
- OpenAI API の呼び出しにはレート制限やエラーが発生します。news_nlp・regime_detector はリトライ・フォールバックロジックを備えていますが、API キーの管理とコストに注意してください。
- paper_trading モードは本番 DB と明確に分離して動作するよう設計されています。環境変数を正しく設定して DB が混在しないように注意してください。
- monitoring_db.init_monitoring_db は冪等であり、既存 DB のマイグレーション（カラム追加）処理も含まれています。

---

## 貢献 / 拡張案

- ブローカープラグインの追加（実ブローカー / 他のモック戦略）
- 単元株（lot_size）の銘柄毎対応（stocks マスタの導入）
- より詳細なメトリクス（注文遅延、API レスポンス統計など）を DuckDB / Prometheus などに送る
- テストカバレッジの拡充（unit / integration）

---

この README はコードベースの主要機能と使い方をまとめたものです。細かな動作や API の詳細は各モジュールの docstring を参照してください。必要であれば、環境構築手順や運用手順をさらに細かくドキュメント化できます。