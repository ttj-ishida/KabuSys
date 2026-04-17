# KabuSys

日本株自動売買システムのコードベース（モジュール群）の README。  
この README はリポジトリ内の主要コンポーネント・起動スクリプト・設定方法・運用上の注意点をまとめたものです。

※ この README は src/kabusys 以下の実装を元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な要素は次の通りです。

- Execution: ブローカーへの発注、注文状態管理、リコンシリエーション（再同期）
- Monitoring: システム稼働監視、注文監視、リスク監視、アラート送信（LINE）
- Portfolio: 候補選定、ウェイト計算、ポジションサイズ決定、セクター制約などのポートフォリオ構築ロジック
- Research: ファクター計算・特徴量探索・将来リターン計算などの分析ロジック（DuckDB を想定）
- AI: ニュースの NLP 集約（OpenAI）や市場レジーム判定
- Tools: Paper Trading 検証レポートなどのユーティリティスクリプト

設計方針として、DB（SQLite / DuckDB）を用いた永続化、外部 API 呼び出しの分離、フェイルセーフ（API失敗時のフォールバック）、およびルックアヘッドバイアス防止が考慮されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（本番 / Paper Trading 切替対応）
  - run_monitoring.py: SystemMonitor のポーリングループ起動
- 監視関連
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor: 滞留注文や約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: 条件達成で data/kill.flag を書いて Execution を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringDB: monitoring 用 SQLite のスキーマ初期化・読み書き
  - streamlit_dashboard.py: 監視ダッシュボードを Streamlit で表示
- Execution（概要）
  - ブローカークライアントの生成（本番/モック）
  - OrderManager / OrderRepository: 注文作成・保存・同期
  - Reconciler: 起動時の注文 / ポジション突合せ
  - RiskManager: 発注前リスク制約（rate limit 等）
- Portfolio（純粋関数）
  - 銘柄選定、等重・スコア重み付け、セクター制約、ポジションサイズ計算（lot 単位丸め、aggregate cap）
- Research
  - ファクター（Momentum / Volatility / Value）計算
  - 将来リターン、IC（スピアマン）、統計サマリー
- AI
  - news_nlp.score_news: raw_news を OpenAI で解析し ai_scores へ書き込み
  - regime_detector.score_regime: ETF MA とマクロニュース LLM を合成してレジーム判定
- Tools
  - paper_verification_report: paper_trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ等）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の union 表記（X | Y）を利用しているため）
- SQLite は標準搭載、DuckDB 等は外部パッケージ

推奨手順（例）:

1. リポジトリをクローンし、仮想環境を作成・有効化
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要な Python パッケージをインストール
   （requirements.txt がない場合は以下をインストール）
   ```bash
   pip install duckdb psutil requests openai streamlit
   ```
   - duckdb: 研究用データアクセス
   - psutil: プロセス優先度 / CPU 情報取得
   - requests: LINE API 呼び出し
   - openai: OpenAI API クライアント
   - streamlit: ダッシュボード起動

3. データディレクトリの作成
   ```bash
   mkdir -p data
   ```
   デフォルト DB パス:
   - monitoring (SQLite): data/monitoring.db
   - paper trading SQLite: data/paper_trading.db
   - DuckDB: data/kabusys.duckdb
   - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag

4. 環境変数設定
   プロジェクトルートの `.env` / `.env.local` を用意できます。自動読み込みが有効（Settings モジュール）です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: （必須）J-Quants API トークン
   - KABU_API_PASSWORD: （必須）kabu API パスワード
   - OPENAI_API_KEY: OpenAI 利用時に必要（AI 機能）
   - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
     - `paper_trading` のとき Execution は MockBrokerClient を使い、Paper 用 SQLite を使用
   - PAPER_FILL_MODE: paper_trading 時の fill 動作 ("instant"|"partial"|"never"|"reject")（デフォルト: instant）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite パス（デフォルト: data/paper_trading.db）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定なら通知は行われない）
   - LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"

   .env の書式についてはプロジェクト内の Settings ロジックがサポートする形式（export 付き、クォート、コメント）に従えます。

---

## 使い方

以下は代表的な実行例です。Python モジュールとして起動できます（src が PYTHONPATH に含まれている状態を想定／リポジトリルートから実行）。

- ExecutionEngine 起動（本番または Paper Trading）
  ```bash
  # 本番モード（KABUSYS_ENV=live）
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

  # Paper Trading モード
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  注意:
  - `paper_trading` の場合、Execution は `PAPER_TRADING_SQLITE_PATH`（デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - Execution 起動時に `data/stop_requested.flag` が存在すると起動を行いません。
  - 実行中は `data/execution.pid` に PID を書き込みます。PID ファイルが stale かどうかは SystemMonitor が検出・処理します。

- Monitoring 起動（SystemMonitor のポーリング）
  ```bash
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で指定可能（デフォルト 60 秒）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  注意:
  - Monitoring は KABUSYS_ENV にかかわらず `Settings.sqlite_path`（デフォルト data/monitoring.db）を使用して監視ログを記録します（監視 DB は常に本番 DB を参照する想定）。
  - 停止は `data/stop_requested.flag` を作成するか Ctrl+C。

- Streamlit ダッシュボード
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 読み取り専用で SQLite DB を開きます。MonitoringEngine が稼働していることが前提です。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を明示する
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して標準出力にレポートを出します。

- AI 機能（プログラムから呼び出す）
  - OpenAI を使う関数は api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定して呼び出します。
  - 例: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)

---

## 運用上・実装上の注意

- 自動ロードされる .env の優先順位は:
  OS 環境変数 > .env.local > .env
  自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- KABUSYS_ENV の値は "development" | "paper_trading" | "live" のいずれかである必要があります。
- Monitoring と Execution は停止フラグ管理を行います:
  - run_* スクリプトはプロジェクトの data/stop_requested.flag を監視します。ファイルが存在するとループを抜けて終了します。
  - KillSwitch は条件に応じて `data/kill.flag` を作成し、ExecutionEngine に停止シグナルを送ります（Execution は起動時に kill.flag を確認して起動判断をする想定）。
- ProcessPriority: 起動時にプロセス優先度を "high" に設定しようとします（psutil による設定）。権限不足や未対応 OS の場合は警告が出ます。
- DB マイグレーション: init_monitoring_db は冪等にスキーマを作成し、既存カラムがなければ ALTER TABLE による簡易マイグレーションを行います（例: latency_ms, peak_value の追加）。
- AI 呼び出しは外部 API（OpenAI）を利用するためレート制限やネットワーク障害をハンドリングするよう設計されています（指数バックオフ等）。

---

## 主要な環境変数（サマリ）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能で必要)
- KABUSYS_ENV (development|paper_trading|live) — default development
- DUCKDB_PATH — default data/kabusys.duckdb
- SQLITE_PATH — monitoring DB, default data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper trading DB, default data/paper_trading.db
- PAPER_FILL_MODE — instant|partial|never|reject
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START 等は Settings で詳細管理

---

## ディレクトリ構成

（src/kabusys 配下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                        — 環境変数 / Settings
    - run_execution.py                  — ExecutionEngine 起動スクリプト
    - run_monitoring.py                 — SystemMonitor 起動スクリプト
    - tools/
      - paper_verification_report.py    — Paper Trading 検証レポート
    - ai/
      - news_nlp.py                     — ニュース NLP / OpenAI スコアリング
      - regime_detector.py              — 市場レジーム判定（MA + LLM）
    - monitoring/
      - monitoring_db.py                — SQLite ベースの監視 DB 層
      - system_monitor.py               — システム状態 / データ鮮度監視
      - trade_monitor.py                — 注文滞留・約定異常監視
      - risk_monitor.py                 — ドローダウン / ポジション上限監視
      - kill_switch.py                  — kill.flag 書き込みロジック
      - alert_manager.py                — LINE 通知ラッパー
      - monitoring_engine.py            — 各 Monitor を束ねるランナー
      - streamlit_dashboard.py          — Streamlit ダッシュボード
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - ... (broker factory / engine 等)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - process_priority.py
    - data/ (ランタイム生成想定)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - kill.flag
      - stop_requested.flag

---

## よくある運用フロー

1. .env を用意して必要なキーを設定
2. DuckDB に prices_daily / raw_financials / raw_news 等のデータをロード（Research / AI に必要）
3. Monitoring を起動して system_status / trade_logs 等のテーブルを初期化・記録
4. Execution を起動（paper_trading で動作確認 → live へ移行）
5. 必要に応じて streamlit ダッシュボードで状況確認
6. Paper Trading 実行後は tools.paper_verification_report で検証

---

## 参考（トラブルシューティング）

- "OpenAI API キーが未設定です" のエラー → OPENAI_API_KEY を設定してください（AI 機能呼び出し時）。
- Monitoring が起動しない / DB が開けない → SQLITE_PATH の権限・パスを確認。streamlit は読み取り専用で開くため URI を付けて起動します。
- PID ファイルが残っていて Execution を起動できない / stale PID 検出 → SystemMonitor が stale を検出して削除しますが、手動で `rm data/execution.pid` も可能です。
- LINE 通知が送れない → LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID の値と送信先を確認、ネットワーク疎通確認。

---

この README はコード内コメントとスクリプトの振る舞いに基づいて作成しています。詳細な実行パラメータや broker 実装の差分（本番 API / Mock）については該当モジュールの実装コメントを参照してください。必要であれば README に具体的な .env.example や requirements.txt を追加することもできます。