KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買フレームワークです。本リポジトリは以下の主要機能を提供します。

- 注文管理・発注エンジン（ExecutionEngine と OrderManager）
- モニタリング（System / Trade / Risk の監視、アラート、kill switch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI連携（ニュースセンチメント評価・市場レジーム判定 via OpenAI）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

本 README はコードベース（src/kabusys 配下）をもとに、セットアップ・起動方法・主要コンポーネントの説明を日本語でまとめたものです。

主な機能一覧
-------------
- 実行（Execution）
  - Broker クライアント抽象化（本番 / Paper Trading の分離）
  - OrderManager による注文状態管理、送信、同期
  - Reconciler による再起動時の自動復旧（Order / Position の突合）
- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存性、データ鮮度チェック
  - TradeMonitor: 滞留注文（stale orders）・約定価格異常の検出
  - RiskMonitor: ドローダウン、ポジション上限の監視とリスクログ
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）書き込み
  - AlertManager: LINE による通知（オプション）
  - Streamlit ダッシュボード（監視データ可視化）
- ポートフォリオ
  - 候補選定（スコア順）、等配分・スコア加重、リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap 対応）
- リサーチ
  - momentum / volatility / value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
- AI
  - ニュース記事のセンチメント評価（OpenAI）
  - マクロニュース + ETF MA200 による市場レジーム判定（LLM + 時系列指標合成）
- 運用支援
  - paper_trading 用検証レポート生成スクリプト（tools.paper_verification_report）
  - monitoring DB 初期化ユーティリティ（init_monitoring_db）

必要条件（主要依存）
-------------------
（実行環境や用途により必要なパッケージは変わります。最低限の一覧）

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit（ダッシュボード利用時）
- sqlite3（標準ライブラリ）

pip インストール例:
    pip install duckdb psutil requests openai streamlit

設定（環境変数 / .env）
----------------------
アプリ設定は .env ファイルまたは OS 環境変数から読み込まれます（自動ロード機能あり）。
自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

主な環境変数（名前とデフォルト・説明）
- KABUSYS_ENV (development | paper_trading | live) — 実行環境。デフォルト: development
  - paper_trading の場合、MockBrokerClient を用い data/paper_trading.db を使用します。
  - monitoring は KABUSYS_ENV に関わらず production sqlite_path を使用します（設計上の注意）。
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定モード（instant | partial | never | reject、デフォルト: instant）
- PID_FILE_PATH — PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH — kill.flag ファイルパス（default: data/kill.flag）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

セットアップ手順
----------------
1. リポジトリをクローン / コピー
2. Python 仮想環境を作成して有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate
3. 必要パッケージをインストール
   pip install -r requirements.txt
   （requirements.txt がない場合は上記の必要条件パッケージを個別にインストール）
4. data ディレクトリ作成
   mkdir -p data
5. .env を作成して必要な環境変数を設定（.env.example を参考に）
   例:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=yyyyy
     OPENAI_API_KEY=zzzzz
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
6. 初回は monitoring DB の初期化が自動で行われます（run_monitoring / run_execution が init_monitoring_db を呼びます）。

使い方（起動・コマンド）
-----------------------

1) 監視ループ（Monitoring）
- 監視（SystemMonitor のポーリング）を起動します。MONITOR_POLL_INTERVAL で間隔を指定可能（秒、デフォルト 60）。
- Process 優先度を "high" に設定して起動します（内部で psutil を使用）。
- 実行:
    python -m kabusys.run_monitoring
- 例（間隔 30 秒）:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

注意: Monitoring は Settings の sqlite_path を使用して監視ログを永続化します（環境に関わらず本番 sqlite_path を使用する設計である点に注意）。

2) 実行エンジン（Execution）
- 実際の注文発行を行う ExecutionEngine を起動します。
- KABUSYS_ENV が paper_trading の場合は MockBrokerClient が使われ、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全に分離されます。
- 実行:
    python -m kabusys.run_execution

3) Paper Trading 検証レポート
- Paper Trading の SQLite を解析して検証レポートを標準出力に出力します。
- 実行:
    python -m kabusys.tools.paper_verification_report
- 期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定例:
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

4) Streamlit ダッシュボード（監視 UI）
- 起動:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- read-only URI で SQLite を開いて表示します。MonitoringEngine を先に起動してデータを書き込んでください。

5) AI 機能（ニューススコア・レジーム判定）
- モジュール API を通して呼ぶことを想定しています（DuckDB 接続を渡す）。
- 例（Python スクリプト内）:
    from openai import OpenAI
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")
- レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,4,10), api_key="YOUR_OPENAI_KEY")

設計上の注意点
-------------
- Monitoring は production sqlite_path を使用する（paper_trading でも同じ監視 DB を参照する設計）。
- ExecutionEngine を paper_trading モードで動かすと、発注履歴/トレードログは data/paper_trading.db に記録されるため本番 DB と分離されます。
- OpenAI 連携は API キー必須。API エラー時はフェイルセーフ（スコア 0 やスキップ）で継続する実装が各所にあります。
- process priority（優先度設定）や CPU affinity の設定は psutil を利用し、アクセス権限がない環境では警告を出してスキップします。
- kill.flag（Settings.kill_flag_path）を書き込むことで ExecutionEngine に停止シグナルを送る仕組みがあります。KillSwitch はリスク条件（ドローダウン等）でフラグを作成します。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 内の主要ファイル・モジュール一覧と簡単な説明です。

- src/kabusys/__init__.py
  - パッケージメタ情報（__version__ 等）
- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（.env 自動ロード、必須チェック）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- src/kabusys/monitoring/
  - monitoring_db.py — SQLite 監視 DB スキーマ / MonitoringDB クラス
  - system_monitor.py — システム状態・データ鮮度チェック
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — LINE 通知機能
  - kill_switch.py — kill.flag の作成/判定
  - streamlit_dashboard.py — Streamlit ダッシュボード
- src/kabusys/execution/
  - order_manager.py, order_repository.py, reconciler.py, execution_engine.py, broker_factory.py, broker_api.py など
  - 注文管理、ブローカー抽象化、再同期ロジックを提供
- src/kabusys/portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数算出（単元丸め・aggregate cap）
  - risk_adjustment.py — セクター制限・レジーム乗数
- src/kabusys/research/
  - factor_research.py — momentum/volatility/value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン、IC、統計サマリ
- src/kabusys/ai/
  - news_nlp.py — ニュース記事の LLM ベースのセンチメント評価（ai_scores 書き込み）
  - regime_detector.py — ETF MA200 + マクロセンチメントに基づくレジーム判定
- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

開発・運用上のヒント
--------------------
- ログレベルは LOG_LEVEL 環境変数で制御可能（デフォルト INFO）。
- Monitoring / Execution 起動時にプロセス優先度が High に設定されるため、実行環境の権限によっては警告が出ることがあります。
- DuckDB のテーブル（prices_daily / raw_financials / raw_news など）を用いてファクター計算や AI 処理が行われます。研究用途でデータを用意する際は DuckDB に適切にロードしてください。
- Paper Trading の検証は tools.paper_verification_report による自動レポーティングが便利です。
- OpenAI 呼び出しはレートリミットや一時的な障害を考慮してリトライロジックを備えていますが、API 利用料は発生します。テスト時はモック化（unittest.mock.patch）することを推奨します。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンス情報や貢献方法を記載してください。該当ファイルがない場合はプロジェクト方針に合わせて追記してください。）

補足
----
この README はリポジトリ内のコードコメントと実装に基づいてまとめています。実際の運用にあたっては .env.example（存在する場合）やコード内のドキュメントコメントを参照し、必要に応じて設定・初期データの準備を行ってください。質問や手順の不明点があれば具体的に教えてください。必要に応じて起動スクリプト例や .env のテンプレートを作成します。