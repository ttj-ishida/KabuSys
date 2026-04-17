# KabuSys

日本株向け自動売買システムのコードベース。  
このリポジトリはシグナル→ポートフォリオ構築→発注→監視・リコンシリエーション、ならびに研究用ユーティリティ（ファクター計算・特徴量探索・AI ニューススコアリング）を含みます。

---

## プロジェクト概要

KabuSys は以下の主要機能を備えた自動売買プラットフォームのコアライブラリです。

- 発注エンジン（ExecutionEngine）および OrderManager による注文生成・状態管理
- 再起動時の自動リコンシリエーション（Reconciler）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）によるシステム健全性の定期チェック
- LINE によるアラート送信（AlertManager）と KillSwitch による安全停止
- Paper Trading 用の分離された DB と Mock ブローカー運用
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数）
- 研究用モジュール（ファクター計算、将来リターン、IC、統計サマリー）
- AI ベースのニュースセンチメント評価（OpenAI を利用した ai_scores 書き込み）
- Streamlit ベースの監視ダッシュボード
- 各種ツール（Paper Trading 検証レポート生成など）

主要な設計方針として、外部 API 呼び出しや現在日時の参照に注意を払い、ルックアヘッドバイアスを避けること、及び Paper Trading と本番の DB を明確に分離することを重視しています。

---

## 機能一覧

- Execution
  - Order 作成 / 送信 / 同期（OrderManager）
  - リコンシリエーション（Reconciler）
  - RiskManager（発注時のリスク判定）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス PID / データ鮮度
  - TradeMonitor: 滞留注文 / 約定価格の異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイルで ExecutionEngine を安全停止
  - AlertManager: LINE Push によるアラート（クールダウン制御）
  - Streamlit ダッシュボード（リアルタイムではなく DB を読む）
- Portfolio
  - 候補選定、等重配分・スコア重み配分
  - セクターキャップ適用、レジーム乗数計算
  - ポジションサイズ算出（単元株丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）算出、ファクター統計サマリ
- AI
  - ニュースセンチメントスコア（OpenAI を用いた批判的検証 / バッチ処理 / リトライ）
  - レジーム判定（ETF MA200 + マクロ記事センチメントの合成）
- Tools
  - Paper Trading 検証レポート生成（過去期間の稼働率、成功率、レイテンシ等）

---

## セットアップ手順

前提
- Python 3.10 以上（typing などの利用を想定）
- sqlite3 は標準ライブラリに含まれます
- system によっては psutil の権限や一部機能の制限があります（優先度設定や cpu_affinity）

1. リポジトリをクローン／展開
   - ソースは `src/kabusys` に配置されています。

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 以下は主な依存ライブラリ（requirements.txt が無い場合は手動で）
     - duckdb
     - openai
     - psutil
     - requests
     - streamlit (ダッシュボードを使う場合)
   - 例:
     - pip install duckdb openai psutil requests streamlit

4. 環境変数 / .env の設定
   - プロジェクトルートに `.env`（または `.env.local`）を配置できます。config モジュールは自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化）。
   - 必須（使用機能に依存）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（Research で使用）
     - KABU_API_PASSWORD — kabuステーション API 用パスワード（Execution）
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - LINE アラート（任意）:
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
   - 主要な設定とデフォルト:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - PID_FILE_PATH: data/execution.pid
     - KILL_FLAG_PATH: data/kill.flag
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
     - LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

5. データディレクトリ
   - 既存の DB が無ければ自動でテーブルを初期化する箇所がありますが、最初に `data/` を作成しておくと良いです。
   - PID / flag ファイルは `data/` 以下に生成されます（例: data/execution.pid, data/kill.flag, data/stop_requested.flag）。

---

## 使い方（代表的なコマンド）

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL を設定するとポーリング間隔を変更できます（秒）
  - 備考:
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（monitoring データは本番 DB を想定）

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - Paper Trading 実行例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper Trading の場合は MockBrokerClient が使用され、DB は `data/paper_trading.db`（既定）へ記録されます
  - 起動前に `data/kill.flag` が存在したら起動をスキップします（KillSwitch の挙動）
  - 停止は `data/stop_requested.flag`（プロジェクトルート）や `data/kill.flag` を書き込むことで指示できます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（省略時は環境変数 PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

- AI ニューススコアリング（コード API）
  - from kabusys.ai.news_nlp import score_news
  - DuckDB 接続を渡して score_news(conn, target_date, api_key=...)
  - OpenAI API キーが必要

- 市場レジーム判定（コード API）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=...)

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは DB を読み取り専用で参照します（MonitoringEngine が書き込むデータを表示）

---

## 環境変数（主なもの）

- 必須（機能による）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI / LINE
  - OPENAI_API_KEY
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- 運用／DB
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
  - PID_FILE_PATH — デフォルト: data/execution.pid
  - KILL_FLAG_PATH — デフォルト: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START — "1" で起動時に kill.flag をクリア
  - PAPER_FILL_MODE — instant|partial|never|reject（paper_trading の挙動）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring で使用）
  - LOG_LEVEL — INFO など
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視の閾値

注意: config.Settings クラスが未設定の必須変数を参照すると ValueError が発生します（起動時にエラーとなるため .env を正しく設定してください）。

---

## ディレクトリ構成

主要ファイルと簡単な説明（src/kabusys 以下）:

- __init__.py
  - パッケージ定義、バージョン
- config.py
  - .env 読み込み、Settings クラス（環境変数管理）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading は MockBroker に分離）
- ai/
  - news_nlp.py — ニュースの LLM スコアリング、ai_scores への書き込み
  - regime_detector.py — MA200 とマクロセンチメントの合成による市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite のテーブル初期化と永続化 API（MonitoringDB クラス）
  - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度チェック
  - trade_monitor.py — 滞留注文・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限の監視
  - kill_switch.py — kill.flag の読み書き（Execution 停止シグナル）
  - alert_manager.py — LINE への通知送信
  - monitoring_engine.py — 監視コンポーネントの orchestration
  - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py — 注文ライフサイクルの外向け API
  - reconciler.py — 再起動時の同期処理（Order / Position）
  - その他（broker_factory, order_repository, order_record, execution_engine 等が存在する想定）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - position_sizing.py — 発注株数算出（単元丸め、aggregate cap）
- research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- tools/
  - paper_verification_report.py — paper_trading DB に対する検証レポート生成ツール
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity の設定ユーティリティ

補足:
- data/ 以下に DB や PID / flag ファイルが置かれます（未コミット）。デフォルトパスは Settings により決定されます。

---

## 運用上の注意

- 監視コンポーネントは本番 DB を参照するため、監視の実行環境や権限に注意してください。
- OpenAI を呼ぶ処理は API レート制限や課金が発生します。API キーや利用量に注意して運用してください。
- psutil の一部機能（nice, cpu_affinity）は OS と実行権限に依存します。権限不足時は警告を出して処理を継続する設計です。
- kill.flag / stop_requested.flag / execution.pid 等のファイルでプロセス管理を行います。手動で操作する場合は慎重に扱ってください。
- Paper Trading は本番とデータを完全分離するよう設計されています（別 SQLite ファイルを使用）。

---

もし README に追加したい利用例（具体的な環境変数テンプレート、docker-compose の例、CI テスト手順 など）があれば教えてください。必要に応じてサンプル .env.example を作成します。