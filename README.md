# KabuSys — README (日本語)

小規模な日本株自動売買フレームワークの一部実装です。  
このリポジトリは戦略・ポートフォリオ構築、実行（ExecutionEngine）、監視（Monitoring）、
リサーチ（ファクター計算・特徴量探索）、AI を使ったニュース NLP / レジーム判定などのモジュール群を含みます。

---
目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動例）
- 主要環境変数（抜粋）
- 停止・キルスイッチについて
- ディレクトリ構成（概観）

---

## プロジェクト概要

KabuSys は日本株自動売買に必要なコンポーネントをモジュール化した実装です。  
主要な機能は以下の層で構成されています。

- execution: 注文管理、ブローカークライアントの抽象化、リコンシリエーション
- monitoring: システム監視・注文監視・リスク監視・アラート（LINE）・ダッシュボード
- portfolio: 候補選定、重み計算、ポジションサイズ算出、セクター制約・レジーム補正
- research: DuckDB を用いたファクター計算・特徴量探索（ファクター評価）
- ai: OpenAI を利用したニュースセンチメント（news_nlp）・レジーム判定（regime_detector）
- tools: 検証用レポート生成などのユーティリティスクリプト

設計方針の一部:
- DuckDB/SQLite をローカル DB として使用。production/paper_trading は分離可能。
- 自動で .env / .env.local をロード（必要なら無効化可能）。
- 外部 API（kabuステーション、J-Quants、OpenAI 等）との接続を想定した設計。

---

## 主な機能一覧

- SystemMonitor: CPU/メモリ/ディスク、Execution プロセスの生存チェック、データ鮮度チェック
- TradeMonitor: 滞留注文（stale orders）/約定異常価格検出
- RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、リスクログ記録
- KillSwitch / AlertManager: 条件に応じて停止フラグ作成と LINE プッシュ通知
- MonitoringEngine: 上記モニタ群を束ねたポーリングループ
- ExecutionEngine（起動スクリプトあり）: Broker クライアントを用いた注文発行・リスク管理・リコンシリエーション
- Portfolio utilities: 候補選定・スコア重み・ポジションサイズ計算（lot 単位丸め、aggregate cap）
- Research: Momentum / Volatility / Value 等のファクター計算、将来リターン、IC 計算、統計サマリ
- AI: ニュースを LLM でスコアリングして ai_scores に書き込み、マクロニュースと価格でレジーム判定
- Tools: Paper Trading の検証レポート生成スクリプト（paper_verification_report）、Streamlit ダッシュボード

---

## セットアップ手順

1. リポジトリを取得
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - このコードベースで使用される主なパッケージ:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があればそれを使ってください:
    pip install -r requirements.txt）

4. 環境変数 (.env) の準備
   - プロジェクトルートの `.env` / `.env.local` が自動的に読み込まります（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 代表的な必須変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を利用する場合:
     - OPENAI_API_KEY（ai.score_news / regime_detector で使用）

5. データディレクトリ
   - デフォルトでは data/ 配下にファイルが作成されます:
     - data/monitoring.db (SQLite)
     - data/kabusys.duckdb (DuckDB)
     - data/execution.pid など
   - 必要に応じて .env の SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH で上書きできます。

---

## 使い方（起動例）

以下は代表的な起動方法です。src ディレクトリにあるモジュールがパッケージとして import される想定なので、プロジェクトルートから実行してください。

1) 監視ループ（Monitoring）
- デフォルト: MONITOR_POLL_INTERVAL=60 秒
- 起動:
  - python -m kabusys.run_monitoring
- 環境変数でポーリング間隔変更:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 動作:
  - Settings から sqlite_path（デフォルト data/monitoring.db）へ接続し、SystemMonitor.check_once を定期実行します。
  - 停止は data/stop_requested.flag の作成で検知してグレースフルに終了します。

2) 実行エンジン（Execution）
- paper_trading モード（ブローカーのモックを利用）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - この場合 paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。
- 本番想定:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 起動時は execution.pid を生成し、data/stop_requested.flag を監視して終了します。

3) Streamlit ダッシュボード（監視 UI）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only URI を使って DB を開くため、監視プロセスが稼働中でも安全に参照できます。

4) Paper Trading 検証レポート
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - 日付フィルタ:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベースを指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5) AI 関連（ニュース NLP / レジーム判定）
- OpenAI API キーが必要:
  - 環境変数 OPENAI_API_KEY を設定するか、関数引数で渡してください。
- 例（プログラムから呼ぶ）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(duckdb_conn, target_date, api_key="sk-...")

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: 起動環境。valid = development / paper_trading / live（デフォルト: development）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant/partial/never/reject、デフォルト "instant"）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（未設定なら通知は行われない）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

注意: Settings クラスによって無効な値は ValueError が投げられます。PAPER_FILL_MODE や KABUSYS_ENV 等は有限集合に制限されています。

---

## 停止・キルスイッチについて

- 停止要求（やさしい停止）:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループはフラグを検知して終了します（冪等）。
- Kill Switch（自動停止トリガ）:
  - RiskMonitor の判定結果に基づき KillSwitch が data/kill.flag を書き込むと ExecutionEngine 側で停止シグナルとして扱えます。
  - KillSwitch は冪等にファイルを書き、理由テキストを格納します。
- kill.flag は Settings.kill_flag_clear_on_start (環境変数 KILL_FLAG_CLEAR_ON_START=1) により起動時に自動でクリアできます。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートを想定。ソースは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                — 設定 / .env 自動ロード / Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュースセンチメント（OpenAI）
    - regime_detector.py      — レジーム判定（価格 + マクロセンチメント）
  - monitoring/
    - monitoring_db.py        — SQLite テーブル初期化 + MonitoringDB クラス
    - system_monitor.py       — CPU/プロセス/データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常の監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 操作ユーティリティ
    - alert_manager.py        — LINE 通知ラッパ
    - monitoring_engine.py    — 監視コンポーネント束ね
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - execution_engine.py     — （エンジン本体はこのパッケージに含まれる想定）
    - broker_factory.py
    - broker_api.py
    - ...（ブローカー抽象・実装）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py     — psutil を使ったプロセス優先度 / CPU affinity 設定
  - data/                    — デフォルトの DB / flag / pid ファイルを置くディレクトリ（実行時に生成される）

---

補足・運用ノート
- monitoring モジュールは監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を SQLite に永続化します。init_monitoring_db() は冪等性を持ち、既存 DB への簡単なマイグレーション（カラム追加）も行います。
- Execution と Monitoring は DB を分離できます（paper_trading モードでは paper_trading.db を使用）。
- OpenAI 呼び出しはリトライ・バックオフ・レスポンスバリデーション等の堅牢化ロジックを含みますが、API キーや料金に注意して運用してください。
- process_priority.set_process_priority() により起動直後に優先度を上げます（管理者権限がない環境では警告が出てスキップされます）。

---

この README はコードベースの主要点を簡潔にまとめたものです。詳細は各モジュールの docstring / ソースを参照してください。必要であれば導入手順や運用手順をさらに具体化したドキュメントを作成します。