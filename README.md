# KabuSys

日本株向け自動売買システム（KabuSys）のコードベース。  
機能は「実行エンジン（ExecutionEngine）」「監視（MonitoringEngine）」「ポートフォリオ構築」「調査用ファクター計算」「AI（ニュースのセンチメント評価／レジーム判定）」などで構成されています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を提供します。

- 注文発行・管理・リスク制御を行う実行エンジン（本番 / Paper Trading 切替対応）
- システム稼働・注文状況・リスク閾値を監視する監視コンポーネント（ログ永続化・LINE 通知対応）
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター制限等）
- DuckDB を用いたファクター計算・特徴量探索（研究用途）
- OpenAI（gpt-4o-mini）を用いたニュース NLP による銘柄センチメント評価および市場レジーム判定
- Streamlit ベースの監視ダッシュボード、検証レポート生成ツール等

設計上のポイント：
- 設定は環境変数（および .env / .env.local 自動読み込み）で管理
- Paper Trading は本番 DB と分離（専用 SQLite を使用）
- OpenAI 呼び出しはリトライ・バックオフや応答検証を備えた安全な実装

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注、OrderManager、RiskManager、Reconciler）
  - BrokerFactory による実運用 / モック（paper_trading）切替
  - 起動時の PID 管理・停止フラグ監視
- Monitoring
  - SystemMonitor（CPU / メモリ / ディスク / プロセス / データ鮮度）
  - TradeMonitor（滞留注文 / 約定価格異常検出）
  - RiskMonitor（ドローダウン、ポジション数上限検知）
  - KillSwitch（閾値到達で `data/kill.flag` を書き込み ExecutionEngine を停止）
  - AlertManager（LINE push による通知。クールダウン管理あり）
  - MonitoringDB（SQLite ベースの永続化層。マイグレーション処理あり）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio
  - 候補選定（score / rank ベース）
  - 重み計算（等金額 / スコア加重）
  - 単元丸め・ポジションサイズ計算（リスクベース、上限・集約キャップ対応）
  - セクターキャップ適用、レジーム乗数
- Research
  - ファクター計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、基本統計サマリ
- AI
  - news_nlp.score_news: raw_news -> OpenAI で銘柄毎スコア算出 → ai_scores に書込
  - regime_detector.score_regime: ETF(1321)のMA + マクロニュースセンチメントを合成してレジーム判定
  - API 呼び出しはリトライ/バックオフ・レスポンス検証を実装

---

## セットアップ手順

1. Python 仮想環境（推奨）
   - python3.9+ を推奨
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - 要件ファイルがある場合はそれを利用してください。無ければ主要依存をインストール:
     - pip install duckdb psutil openai requests streamlit
   - （プロジェクトによっては追加の依存が必要です）

3. ディレクトリ作成
   - データ格納先を作成:
     - mkdir -p data

4. 環境変数設定（.env / .env.local）
   - 自動ロード機能があるためプロジェクトルートに `.env` や `.env.local` を置けます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  (監視スクリプトのポーリング間隔秒。run_monitoring 起動時に参照)

5. 初期 DB
   - Monitoring 用 SQLite は起動スクリプトが自動で初期化（init_monitoring_db）します。
   - Paper Trading 用 DB（paper_trading.db）は実行環境で必要に応じ作成／準備してください。

---

## 使い方（実行コマンド）

- 監視ループを起動（monitoring）
  - デフォルトで MONITOR_POLL_INTERVAL=60 秒。環境変数で上書き可能。
  - コマンド:
    - python -m kabusys.run_monitoring
  - 動作:
    - プロセス優先度を "high" に設定（可能な OS の場合）
    - Settings から sqlite_path を参照して monitoring DB を初期化
    - SystemMonitor の check_once を定期実行（監視記録を SQLite に保存）
    - 停止はプロジェクトルートの data/stop_requested.flag ファイル設置で検知して終了

- 実行エンジンを起動（ExecutionEngine）
  - 本番 or Paper Trading 切替:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH にデータを保存（本番 DB と完全分離）
  - コマンド:
    - python -m kabusys.run_execution
  - 動作:
    - Process 優先度を上げる
    - Broker クライアント作成、OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動
    - data/stop_requested.flag により停止検知。実行中はデータディレクトリに execution.pid を書きます

- Streamlit ダッシュボード
  - コマンド:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取りモードで SQLite を開き、Overview / Positions / Orders / System タブを表示します

- Paper Trading 検証レポート生成ツール
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - 期間指定例:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db /path/to/paper_trading.db
  - 出力:
    - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して PASS/FAIL 判定を標準出力に印字します

- AI（ニューススコア / レジーム判定）をプログラムから呼び出す
  - news_nlp.score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要（api_key 引数でも指定可能）
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - OPENAI_API_KEY が必要
  - いずれも OpenAI API キーが未設定だと ValueError を送出します
  - 実行中の API 呼び出しはリトライ・バックオフ・レスポンス検証を行います

---

## 主要ファイル・ディレクトリ構成

（src/kabusys をルートにした主な構成）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env ロード / Settings クラス
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI 呼び出し）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / MonitoringDB クラス
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - alert_manager.py
    - kill_switch.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - （その他実行関連モジュール: broker_factory, execution_engine, order_repository 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - data/ (ランタイムで使用する。DB・PIDファイル等を配置)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用デフォルト)
    - kabusys.duckdb (DuckDB データ)
    - execution.pid, kill.flag, stop_requested.flag

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（必須ではないが動作モードに影響）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに必須（AI モジュールを使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — run_monitoring は必ずここを使います
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）

設定はプロジェクトルートの `.env` / `.env.local` に置くと自動ロードされます（既存 OS 環境変数は保護されます）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 運用上の注意

- run_monitoring はモニタリング用 DB（sqlite_path）を環境に関係なく使用します。Paper Trading 時でも監視は本番 sqlite_path を参照する点に注意してください。
- run_execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path を使用して本番 DB と分離します。
- 停止の仕組み:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution が検知して安全停止します。
  - KillSwitch は条件到達時に data/kill.flag を書き込み、ExecutionEngine 側がそれを検出して停止する運用設計です。
- OpenAI を使う機能は API 利用料・レート制限に注意して運用してください（リトライや 429 ハンドリングは実装済みですが、コスト／レートの影響は考慮してください）。
- MonitoringDB は起動時に必要なカラムがなければ ALTER TABLE によるマイグレーションを行います。

---

## 開発 / 貢献

- モジュールは単体テストを想定した設計（外部依存の注入、API 呼び出し部分の差替えが可能）になっています。  
- 実行前に環境変数、データディレクトリ、DB の接続権限を確認してください。

---

README は簡潔に主要な使い方と構成をまとめたものです。さらに詳しい設計仕様（StrategyModel.md, PortfolioConstruction.md 等）がある想定のため、戦略やブローカーインターフェースの詳細は該当ドキュメントを参照してください。