# KabuSys

KabuSys は日本株の自動売買・研究・監視を目的とした小規模なシステム群です。バックテスト / リサーチ用の DuckDB ベースのファクター計算、Execution 用の発注エンジン、Monitoring／Alert／Kill Switch 機能、AI を使ったニューススコアリングなどのコンポーネントを含みます。

以下はこのリポジトリ（src/kabusys）に含まれる主要機能と使い方の概要です。

---

## プロジェクト概要

- 自動売買エンジン（ExecutionEngine）とその補助コンポーネント（OrderManager, RiskManager, Reconciler 等）。
- 監視（Monitoring）機能：システム状態、注文滞留、リスク監視（ドローダウン・ポジション上限）を定期的に記録・アラート。
- リサーチ：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量解析ユーティリティ。
- AI モジュール：OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）や市場レジーム判定。
- Tools：Paper Trading の検証レポート生成、Streamlit ダッシュボードなど。
- 設定は環境変数（.env / .env.local の自動ロードあり）で管理。

---

## 機能一覧

- Execution
  - Broker クライアントの抽象化（本番/Mock 区別）
  - OrderManager による注文の作成・送信・同期
  - Reconciler による起動時リコンシリエーション（再同期）
  - RiskManager（発注制限等）

- Monitoring
  - SystemMonitor：CPU/Mem/Disk・プロセス生存・データ鮮度検査・ログ永続化
  - TradeMonitor：滞留注文／約定価格異常の検出
  - RiskMonitor：ドローダウン／ポジション上限の検査とリスクログ出力
  - KillSwitch：フラグファイル (data/kill.flag) による ExecutionEngine 停止シグナル
  - AlertManager：LINE Push による通知（トークン未設定時はログ出力のみ）
  - Streamlit ダッシュボード（data/monitoring.db を参照）

- Research / Data
  - factor_research：モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC（Spearman）などの統計ユーティリティ

- AI
  - news_nlp.score_news：銘柄単位のニュース要約→センチメントスコア生成→ai_scores へ格納
  - regime_detector.score_regime：MA200 とマクロニュースの LLM スコアを合成して regime を判定

- Tools
  - paper_verification_report：Paper Trading DB（data/paper_trading.db）から検証レポートを生成
  - streamlit_dashboard：監視データ可視化（streamlit）

---

## セットアップ手順

1. Python バージョン
   - Python 3.10 以上を推奨（typing の union 型等を利用）。

2. 依存ライブラリのインストール（例）
   - requirements.txt が無ければ以下を手動インストールしてください：
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   - プロジェクト配布時に requirements.txt を用意している場合は：
     - pip install -r requirements.txt

3. 環境変数の設定
   - 必須（実運用で必要なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必要時）
     - KABU_API_PASSWORD — kabuステーション API 用（Execution 実行時）
   - AI 機能を使う場合
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
   - 任意（通知・挙動の調整）
     - LINE_CHANNEL_ACCESS_TOKEN — LINE Push 用トークン（AlertManager）
     - LINE_USER_ID — LINE Push 送信先ユーザー ID
     - KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
       - paper_trading: MockBroker を使い data/paper_trading.db を利用（本番 DB と分離）
       - live: 本番モード
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60 秒）
     - PID_FILE_PATH / KILL_FLAG_PATH 等は Settings で確認可能

   - .env 自動ロード
     - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし OS 環境が優先、.env.local は .env を上書き）。
     - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. データディレクトリ
   - デフォルトでは data/ 以下を使用します。必要に応じてディレクトリを作成してください。
     - mkdir -p data

---

## 使い方

以下は主要スクリプト／コマンド例です。ソースツリーを直接参照しているため、実行する際は PYTHONPATH を設定するか、パッケージをインストールしてください。

1. Monitoring（監視ループ）を起動
   - 簡単な起動例（ソースルートが ./src の場合）:
     - PYTHONPATH=src python src/kabusys/run_monitoring.py
   - モジュール実行（パッケージとしてインストール済みなら）
     - python -m kabusys.run_monitoring
   - 環境変数でポーリング間隔を変更:
     - MONITOR_POLL_INTERVAL=30 PYTHONPATH=src python src/kabusys/run_monitoring.py

   - 注意:
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（監視ログは一元化する想定）。
     - 起動時にプロセス優先度を "high" に設定しようとします（psutil の権限に依存）。

2. ExecutionEngine（発注セッション）を起動
   - 本番/ペーパーの切り替えは KABUSYS_ENV で制御:
     - KABUSYS_ENV=paper_trading PYTHONPATH=src python src/kabusys/run_execution.py
     - KABUSYS_ENV=live PYTHONPATH=src python src/kabusys/run_execution.py
   - paper_trading モードでは MockBrokerClient を使用し data/paper_trading.db に対して動作します（本番 DB と分離）。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション例:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - --db でデータベースパスを明示可能（PAPER_TRADING_SQLITE_PATH 環境変数も利用可）

4. Streamlit ダッシュボード（監視）
   - 起動コマンド（ファイル内ドキュメントと同じ）:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで接続するため、MonitoringEngine が data/monitoring.db を生成している必要があります。

5. AI 機能（ニューススコアリング / レジーム判定）
   - OPENAI_API_KEY を環境変数に設定してください。
   - ライブラリ関数を呼び出して使用します（DuckDB 接続を渡す設計）:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
   - これらの関数は DuckDB 接続（prices_daily / raw_news 等のテーブルが用意されている前提）を受け取り、結果を DB に書き込みます。
   - API はリトライ・バリデーション・スコアクリップ等を内蔵しています。

6. 監視データベース初期化
   - run_monitoring/run_execution は起動時に init_monitoring_db() を呼んで監視用 SQLite テーブルを作成（冪等）します。
   - 手動で初期化したい場合は Python REPL から呼び出してください：
     - from kabusys.monitoring.monitoring_db import init_monitoring_db
     - import sqlite3; conn = sqlite3.connect("data/monitoring.db"); init_monitoring_db(conn)

---

## 重要な環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API キー（必須: 使用する場合）
- KABU_API_PASSWORD — kabuステーション API パスワード（Execution 実行時に必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）。0 以下や不正値はデフォルトにフォールバック。
- SQLITE_PATH / DUCKDB_PATH / PAPER_TRADING_SQLITE_PATH — DB パス（デフォルトは data/ 以下）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — AlertManager による通知用（未設定時は通知をスキップ）

詳細は src/kabusys/config.py の Settings クラスを参照してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定の管理、.env 自動ロードロジック
  - run_monitoring.py  — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py   — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ & MonitoringDB ラッパー
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 制御
    - alert_manager.py       — LINE 通知ラッパー
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - reconciler.py
    - ...（BrokerFactory / ExecutionEngine 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

## 運用での注意点

- データ鮮度チェックは DuckDB の prices_daily テーブルを参照します。データの投入・更新が正しく行われていることを確認してください。
- paper_trading モードは本番 DB と完全分離するよう設計されています。必ず KABUSYS_ENV=paper_trading を設定してから起動してください。
- OpenAI 絡みの機能は API 料金・レート制限の影響を受けます。スコアリングはバッチ化・リトライを実装していますが、運用時はレート制限に注意してください。
- AlertManager（LINE）に関しては、トークンおよび user_id が設定されていないと送信をスキップします。クールダウン管理（同一カテゴリの頻度抑制）を備えています。
- run_monitoring/run_execution 起動時にプロセス優先度を "high" に設定しようとします。権限不足（非 root 等）やプラットフォーム依存で失敗することがありますが、警告ログを出して続行します。

---

この README はコードベースの主要機能と利用方法を簡潔にまとめたものです。より詳細な設計・アルゴリズムの説明はソース内の docstring（PortfolioConstruction.md や StrategyModel.md など参照箇所）や各モジュールのコメントを確認してください。必要であればセットアップスクリプトや example .env を追加する README の拡張も対応できます。