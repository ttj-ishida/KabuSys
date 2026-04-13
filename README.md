# KabuSys

日本株自動売買プラットフォームのコアライブラリ群（プロトタイプ）。  
このリポジトリは発注・リスク管理・ポートフォリオ構築、監視、研究、ニュースNLP を含むモジュール群を提供します。

> 注意: README はこのコードベースに含まれる主要モジュールの使い方・構成をまとめたものであり、実運用には追加の設定・データ準備・テストが必要です（特に DuckDB のテーブルやブローカークライアント等）。

---

## 概要

KabuSys は日本株向けのアルゴリズム取引基盤を構成するモジュールセットです。主な責務は以下です。

- 注文生成・送信・状態管理（Execution）
- リコンシリエーション（起動時の自動復旧）
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- リスク制御（ドローダウン監視・ポジション上限など）
- 監視（プロセス生存確認・データ鮮度・注文の滞留や約定異常検出）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュースの NLP によるセンチメントスコア化（OpenAI を利用）
- 各種ユーティリティ（環境設定読み込み・プロセス優先度設定 等）
- 開発向けツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

---

## 主な機能一覧

- Execution
  - Engine 起動スクリプト（run_execution.py）
  - BrokerFactory による本番 / Paper Trading 切替
  - OrderManager / OrderRepository / Reconciler（発注フローと自動復旧）
  - RiskManager（シンプルな制約ロジック）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor（定期チェック）
  - MonitoringEngine（各 Monitor を束ねてポーリング）
  - AlertManager（LINE Push）
  - KillSwitch（フラグファイルによる Execution 停止）
  - SQLite ベースの監視 DB 管理（init_monitoring_db）
  - Streamlit ダッシュボード（簡易可視化）
- Portfolio（純粋関数）
  - 候補選定、等重／スコア重み、セクター制限、ポジションサイズ計算
- Research
  - DuckDB を使ったファクター計算（momentum/value/volatility）
  - 将来リターン、IC 計算、統計サマリなど
- AI
  - news_nlp: raw_news から銘柄ごとのセンチメントを OpenAI で評価して ai_scores に書き込む
  - regime_detector: ma200 とマクロニュースを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポート生成ツール

---

## 動作要件（推奨）

- Python 3.10+
  - 型ヒント（|）や from __future__ のアノテーションを使用しているため Python 3.10 以上を推奨します。
- 必要な Python パッケージ（主要なもの）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを利用する場合)
- SQLite は標準ライブラリで提供されます。

（プロジェクトに requirements.txt がない場合は上記パッケージを手動でインストールしてください）

例:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. 環境変数の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主に使用される環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - KABU_API_BASE_URL (省略時は http://localhost:18080/kabusapi)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - PAPER_TRADING_SQLITE_PATH (paper_trading モードの SQLite DB)
     - DUCKDB_PATH (DuckDB ファイルのパス; デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 SQLite のパス; デフォルト: data/monitoring.db)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート送信用)
     - MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔秒; デフォルト 60)
     - PAPER_FILL_MODE (paper_trading の fill モード: instant | partial | never | reject)
5. DB 初期化
   - run_execution.py / run_monitoring.py の起動時に monitoring DB のテーブル作成（init_monitoring_db）が自動実行されます。
   - DuckDB 側は prices_daily / raw_financials / raw_news 等のテーブルが必要です。これらはデータパイプライン／インポート処理で準備してください（本リポジトリにデータ導入スクリプトは含まれていない想定）。

---

## 使い方

基本的な起動例・コマンドラインの使い方。

- ExecutionEngine を起動（本番または paper_trading は KABUSYS_ENV に依存）
  - KABUSYS_ENV=paper_trading を使うと Paper Trading 用の MockBrokerClient が使用され、デフォルトで data/paper_trading.db に記録されます。
  - 起動:
    - python -m kabusys.run_execution
  - 実行開始時にプロセス優先度を High に設定します（set_process_priority）。

- SystemMonitor（単体スクリプト）を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書きできます（デフォルト 60 秒）。
  - 監視は常に production の sqlite_path を参照します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite DB を開きます（存在しない場合は起動に失敗します）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db
    - 環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- プログラムからの API 呼び出し例（ニューススコアリング）
  - 簡単なサンプル（Python REPL 等）:
    - import duckdb
    - from kabusys.ai import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date=date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - 注意: score_news / score_regime は OpenAI API キーが必要。キー未設定だと ValueError を送出します。

- 環境設定自動読み込み
  - プロジェクトルート（.git または pyproject.toml を検出）から `.env` / `.env.local` を自動ロードします。OS 環境変数が優先され、`.env.local` は上書きで読み込まれます。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 注意点 / 実運用上のメモ

- Paper Trading は production DB と分離しており、デフォルトで data/paper_trading.db に記録されます。KABUSYS_ENV=paper_trading を利用してください。
- OpenAI API を利用する機能（news_nlp / regime_detector）は API 呼び出しのため API キーとネットワークを要します。失敗時のフォールバックやリトライロジックは組み込まれていますが、呼び出しコストに注意してください。
- Monitoring の kill switch はファイルベース（data/kill.flag）です。ExecutionEngine はこのフラグを検出して安全に停止する設計になっています。
- DuckDB 側のテーブル（prices_daily, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）は外部データパイプラインで準備する必要があります。 research / ai モジュールはこれらの存在を前提としています。
- run_execution/run_monitoring の起動時にプロセス優先度を設定しようとします（psutil を使用）。権限不足で失敗しても警告でスキップします。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なモジュールと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（アプリ設定）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 切替）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news を OpenAI でスコアリングして ai_scores に書込むロジック
    - regime_detector.py
      - ma200 とマクロニュースを用いた市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py
      - SQLite テーブル作成 & MonitoringDB（読み書きユーティリティ）
    - system_monitor.py
      - CPU/Memory/Disk/プロセス生存/データ鮮度監視
    - trade_monitor.py
      - 注文滞留・約定異常検出
    - risk_monitor.py
      - ドローダウン・ポジション上限監視、dashboard 更新
    - kill_switch.py
      - フラグファイルによる停止シグナル
    - alert_manager.py
      - LINE Push を用いた通知
    - monitoring_engine.py
      - 各 Monitor を束ねるポーリング制御
    - streamlit_dashboard.py
      - Streamlit による簡易ダッシュボード
  - portfolio/
    - portfolio_builder.py
      - 候補選定・重み付け
    - position_sizing.py
      - 株数算出・集約 cap（単元考慮）
    - risk_adjustment.py
      - セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - __init__.py
    - factor_research.py
      - momentum/volatility/value ファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン、IC、統計サマリ等
  - execution/
    - reconciler.py
      - 起動時の注文/ポジション突合（自動復旧）
    - order_manager.py
      - 発注フローの上位 API（OrderState 管理）
    - （その他 execution 関連のモジュールは本抜粋に一部のみ含む）
  - tools/
    - __init__.py
    - paper_verification_report.py
      - Paper Trading の検証レポート生成スクリプト
  - utils/
    - __init__.py
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ

その他、data ディレクトリ（DBファイル等）や外部のデータパイプラインは別途用意してください。

---

この README はコードベースの主要な使い方・構成をまとめたものです。実行時に生じる詳細な設定やデータ準備（DuckDB のスキーマ・外部ブローカー実装・認証情報など）は、運用環境に応じて適切に構成してください。必要であれば、各モジュールに関するより詳細なドキュメントを追記します。