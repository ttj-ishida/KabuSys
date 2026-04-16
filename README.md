# KabuSys

日本株自動売買システムのリファレンス README。  
このリポジトリは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント / レジーム判定）などの主要コンポーネントを含みます。

※ ドキュメントはコードベース（src/kabusys 以下）から要点を抜粋してまとめています。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主な責務は次のとおりです。

- 取引実行（Broker API 経由の注文発行・状態管理・リコンシリエーション）
- 実行監視（プロセス・リスク・注文状況・データ鮮度の監視とログ永続化）
- ポートフォリオ構築（候補選定・重み付け・単位株丸め・リスク調整）
- リサーチ（ファクター計算、将来リターン・IC 計算、統計集計）
- AI 支援（ニュース記事からのセンチメント算出、マクロニュース + MA による市場レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

設計方針の一部：
- DuckDB / SQLite を用いたローカル DB 中心の処理
- 本番／Paper Trading を明確に分離（KABUSYS_ENV による振る舞い切替）
- OpenAI 呼び出しはフェイルセーフ（失敗時はフォールバック）かつ逐次リトライ実装

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントファクトリ（Paper モードでは Mock を使用）
  - OrderManager / OrderRepository / Reconciler（自動復旧）
  - リスク管理（RiskManager）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（定期チェック、ログ保管）
  - MonitoringEngine（モニタを束ねたポーリング）
  - AlertManager（LINE push によるアラート送信）
  - KillSwitch（条件を満たすと data/kill.flag を書き込み Execution を停止）
  - Streamlit ベースの監視ダッシュボード

- Portfolio
  - 候補選定、等重・スコア重み付け
  - ポジションサイズ計算（リスクベース / 等配分 / スコア配分）
  - セクター上限制御、レジーム乗数

- Research
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（forward returns, IC, summary）

- AI
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）でセンチメント付与 → ai_scores へ書込
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM 評価を合成し market_regime に書込

- Tools
  - Paper Trading 検証レポート出力（src/kabusys/tools/paper_verification_report.py）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）

---

## セットアップ手順

前提
- Python 3.10+（PEP 604 の union 型 `X | Y` を使用しているため）
- Git クローン済みのプロジェクトルートに移動

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - 追加で必要なパッケージがあれば適宜インストールしてください。

   （requirements.txt が無い場合は上記が最低限。環境に応じて pytest 等を追加）

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効）。
   - 主要な環境変数（例）:
     - KABUSYS_ENV = development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN = <J-Quants トークン>
     - KABU_API_PASSWORD = <kabu API パスワード>
     - OPENAI_API_KEY = <OpenAI API Key> (AI 機能利用時)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (LINE 通知)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - PAPER_FILL_MODE = instant | partial | never | reject
     - LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

4. データディレクトリ
   - data/ に DB（monitoring.db, paper_trading.db）やフラグファイル（stop_requested.flag, kill.flag, execution.pid 等）を配置／生成します。
   - 初回は実行時に自動生成されるテーブル（init_monitoring_db）があります。

---

## 使い方（主要スクリプト）

- 監視ループ（常駐プロセス）
  - python -m kabusys.run_monitoring
  - 説明:
    - SystemMonitor を定期実行して system_status 等を SQLite に記録します。
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能。デフォルト 60 秒。
    - 監視は KABUSYS_ENV にかかわらず設定された本番 sqlite_path を使用します。
    - 終了方法: data/stop_requested.flag を作成するか Ctrl+C。

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と分離。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - execution.pid（data/execution.pid）に PID を書きます。stale PID の検出・削除ロジックあり。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD --db path/to/paper_trading.db
  - 引数:
    - --from / --to: 集計期間（任意）
    - --db: SQLite ファイル（指定がなければ PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）
  - 出力: 標準出力に稼働率、注文成功率、送信率、レイテンシ等のサマリと PASS/FAIL 判定

- Streamlit ダッシュボード（監視）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: Read-only 接続で監視 DB を可視化します（MonitoringEngine を先に動かしてデータを書き込んでおくこと）。

- AI 関連（コード経由利用）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
    - OPENAI_API_KEY または api_key 引数が必要
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=None)

---

## 実行時の重要な挙動・注意点

- KABUSYS_ENV
  - development / paper_trading / live のいずれか。Settings クラスでバリデートします。
  - paper_trading: Execution は paper_sqlite_path を使い MockBrokerClient を利用（本番 DB と分離）。
  - monitoring は監視用 sqlite_path（デフォルトの monitoring.db）を使用し、環境にかかわらず本番 DB パスを参照する仕様の箇所があります（コード内コメント参照）。

- 停止フラグ
  - run_monitoring / run_execution は data/stop_requested.flag の有無を監視して優雅に停止します。
  - KillSwitch は条件達成時に data/kill.flag を書き込み Execution の停止を促します（Execution 側で kill.flag の存在を監視する実装が必要）。

- MONITOR_POLL_INTERVAL
  - 秒数を表す環境変数。1 未満や不正値はデフォルト（60 秒）にフォールバックします。

- OpenAI の呼び出し
  - レート制限・タイムアウト・5xx は指数バックオフでリトライします。パースや API 失敗時はフェイルセーフでスコア 0.0（またはスキップ）にフォールバックする設計です。
  - 必ず OPENAI_API_KEY を設定してください（ない場合は例外を投げる関数もあります）。

- DB マイグレーション
  - init_monitoring_db は冪等でテーブルを作成し、既存スキーマへのカラム追加（peak_value, latency_ms）を試みます。

---

## ディレクトリ構成 (主要ファイル)

src/kabusys/
- __init__.py
- config.py                     — 環境変数 / Settings 管理（.env 自動ロード機能）
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト
- tools/
  - __init__.py
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- ai/
  - __init__.py
  - news_nlp.py                  — ニュース NLP（OpenAI）によるスコア付与
  - regime_detector.py           — 市場レジーム判定（MA200 + LLM 合成）
- monitoring/
  - __init__.py
  - monitoring_db.py             — MonitoringDB（SQLite）永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - (その他 Broker / Engine 関連モジュールは同パッケージ内に存在)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity 設定ユーティリティ
  - __init__.py
- data/ (実行時に使う想定のディレクトリ、リポジトリ内に存在しない場合は作成)
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - stop_requested.flag
  - kill.flag
  - execution.pid

---

## 参考：よく使うコマンドまとめ

- 仮想環境・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai requests streamlit

- 監視ループ起動
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README は以上です。特定のモジュール（例: ExecutionEngine の設定、Broker 接続実装、RiskManager のパラメータ等）について詳しい利用法や追加の設定例が必要であれば教えてください。