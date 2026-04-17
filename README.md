# KabuSys

日本株向けの自動売買システム（ライブラリ兼ランタイム）。戦略のポートフォリオ構築、ポジションサイズ算出、注文実行管理、監視・アラート、研究用ファクター計算、AIを使ったニュースセンチメント評価などのコンポーネントを含みます。

## 概要

KabuSys は以下を目的としたモジュール群です。

- 株式自動売買に必要なポートフォリオ構築（候補選定・重み付け・単元丸め）
- 注文の作成・送信・状態管理・再同期（Reconciler）
- Paper Trading と Live の分離運用（DB を分離）
- システム／取引／リスクの監視、LINE による通知、停止フラグ生成（Kill Switch）
- DuckDB を使ったファクター計算・リサーチ機能
- OpenAI を用いたニュース NLP（銘柄ごとのセンチメント）と市場レジーム判定
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール

プロジェクトはライブラリとしても機能し、スクリプト/エントリポイント（ExecutionEngine、Monitoring 等）を備えます。

---

## 主な機能一覧

- portfolio
  - 候補選定(select_candidates)
  - 等金額／スコア加重ウェイト(calc_equal_weights / calc_score_weights)
  - 単元丸め・リスクベース発注量算出(calc_position_sizes)
  - セクター上限適用、レジーム乗数(apply_sector_cap / calc_regime_multiplier)
- execution
  - OrderManager: 発注ワークフロー（重複防止、状態遷移）
  - Reconciler: 再起動時の注文・ポジション同期
  - Broker クライアント抽象化（paper_trading では MockBroker を使用）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringDB：SQLite に監視ログを永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch: ドローダウンやポジション上限で停止フラグを出力
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウンあり）
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
  - Streamlit ダッシュボード（監視用）
- research
  - DuckDB を用いたファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計算、統計サマリ
- ai
  - news_nlp.score_news: OpenAI によるニュースセンチメント評価 → ai_scores に書き込み
  - regime_detector.score_regime: MA200 とマクロニュースを合成して市場レジームを判定
- tools
  - paper_verification_report: Paper Trading DB の検証レポート生成（稼働率、成功率、レイテンシ等）

---

## 必要要件（想定）

- Python 3.9+
- 外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- 標準ライブラリ: sqlite3, logging, threading, datetime 等

（プロジェクトに requirements.txt がない場合は上記を pip でインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順

1. リポジトリをクローン／展開してプロジェクトルートに移動する。
2. 仮想環境を作成し必要パッケージをインストール（上記参照）。
3. data ディレクトリを作成（実行スクリプトが自動で作成することもありますが手動で作ると安全です）:
   ```bash
   mkdir -p data
   ```
4. 環境変数を用意する（.env をプロジェクトルートに置くことで自動読み込みされます）。
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能利用時必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の挙動）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
     - PID_FILE_PATH（Execution pid ファイル、デフォルト data/execution.pid）
     - KILL_FLAG_PATH（KillSwitch が書き込むフラグパス、デフォルト data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（AlertManager 用）

5. （paper_trading を使う場合）paper_trading 用 DB を初期化するか、Execution を起動すると必要なテーブルが作成されます。

注意:
- run_monitoring は常に（KABUSYS_ENV に関わらず）プロダクションの sqlite_path を使って監視 DB を初期化します（監視ログは本番 DB を参照する設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、専用の paper_trading DB を使用します（本番 DB と分離）。

---

## 使い方（よく使うコマンド）

プロジェクトのルートから実行することを想定します。

- ExecutionEngine（注文実行エンジン）起動
  ```bash
  python -m kabusys.run_execution
  ```
  - 動作は KABUSYS_ENV に依存します。paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH（既定: data/paper_trading.db）に記録します。
  - 実行中の停止は data/stop_requested.flag を作成するとエンジンが検知して停止します（run_execution は起動時に既存フラグを検知すると起動しません）。

- Monitoring（監視ポーリング）起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒数で上書き（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使ってログを残します。
  - 停止フラグ: data/stop_requested.flag を作るとループを抜けます。

- Streamlit ダッシュボード（監視）
  起動方法（推奨）:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - read-only モードで SQLite を開きます。MonitoringEngine を起動してから閲覧してください。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

- AI 機能（プログラムから呼ぶ例）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

- ライブラリ／ユーティリティの利用
  - ポートフォリオ構築: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ: from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

---

## 主要な環境変数と説明

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の約定モード）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: Execution pid ファイルのパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループ間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（例: INFO）

自動 .env ロード:
- プロジェクトルートに .env / .env.local があれば自動で読み込みます（ただし OS 環境変数が優先される）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットします。

---

## 停止・フラグ関係

- data/stop_requested.flag: run_execution / run_monitoring が監視している停止フラグ。作成するとループが終了します。
- data/kill.flag: KillSwitch が書き込み、ExecutionEngine に停止を促します（kill.flag は ExecutionEngine 起動時に消去する設定があります）。

PID ファイル:
- Execution 起動時に pid を data/execution.pid に残します（Settings.pid_file_path により変更可能）。SystemMonitor はこの PID ファイルの有無・有効性をチェックします。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / 設定読み込み（.env 自動ロード、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・丸め・キャップ
    - risk_adjustment.py — セクター制限・レジーム乗数
  - execution/
    - order_manager.py — 発注ワークフロー
    - reconciler.py — 再起動時リコンシリエーション
    - （その他 broker_factory, order_repository 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化レイヤ
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種モニタ
    - monitoring_engine.py — 複数 Monitor を束ねる
    - kill_switch.py — 停止フラグの発行
    - alert_manager.py — LINE への通知
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - research/
    - factor_research.py — momentum / volatility / value 等
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - data/ (実行時に使用するディレクトリ、デフォルト)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)
    - kabusys.duckdb (DuckDB)

（上記は主要ファイルの抜粋です。詳細はソースコードを参照してください）

---

## 開発メモ / 注意点

- Monitoring は Settings.env にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用します。監視ログは本番 DB に記録される想定です。
- Paper Trading は本番 DB と明確に分離されます（settings.is_paper が True の場合、paper_sqlite_path を使用）。
- OpenAI を使う機能は API キーが必須。API エラーはリトライやフォールバック（ゼロスコア）でフェイルセーフ化されています。
- .env のパーサは bash 風の export 文やクォート、インラインコメントを考慮しているため既存の .env をそのまま使えます。
- process priority / CPU affinity の設定はプラットフォーム依存（psutil を利用）。権限不足時は警告を出してスキップします。

---

## 参考コマンドまとめ

- Execution 起動:
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring 起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード:
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

README に書かれている動作はソースコード（src/kabusys 以下）のコメント・実装に基づいています。実行前に .env や必要な外部サービス（kabu API / OpenAI API 等）の設定を行ってください。追加の質問や、README の補足（例: 開発用 Dockerfile、CI 設定、具体的なテーブルスキーマの説明など）が必要であればお知らせください。