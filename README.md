KabuSys — 日本株自動売買システム
================================

以下は与えられたコードベースに基づく README です。運用・開発の導入ガイド、主要機能、使い方、ディレクトリ構成などを日本語でまとめています。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買システムのコアモジュール群です。本リポジトリには実行エンジン（発注・リスク管理・再同期）、監視（システム状態・注文監視・リスク監視）、
ポートフォリオ構築・ポジションサイズ計算、ファクター計算・リサーチユーティリティ、AI を使ったニュースセンチメントやレジーム判定用モジュールなどが含まれます。

- 実行エンジンは本番／ペーパートレーディング（分離された SQLite DB）をサポートします。
- 監視機能は定期ポーリングでシステム状態や滞留注文、ドローダウンなどを検出し、LINE による通知や kill flag による ExecutionEngine 停止を行えます。
- DuckDB を用いた市場データ処理・ファクター計算や、OpenAI を用いたニュース NLP（センチメント評価）機能を備えています。

主な機能一覧
--------------
- Execution
  - 発注フロー管理（OrderManager）、発注履歴リポジトリ、起動時のリコンシリエーション（Reconciler）
  - Paper trading モード（MockBrokerClient を利用して data/paper_trading.db に記録）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - MonitoringEngine: 上記を束ねてポーリング、AlertManager（LINE通知）、KillSwitch（flag ファイル）
  - SQLite ベースの監視 DB 初期化・読み書き層（monitoring_db）
  - Streamlit 監視ダッシュボード
- Portfolio construction
  - 候補選定、等金額/スコア重み計算、セクター制約の適用、ポジションサイズ計算（lot 単位丸め等）
- Research
  - ファクター計算（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - news_nlp: raw_news から銘柄別センチメントを OpenAI でスコア化して ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定
- ユーティリティ
  - Settings（環境変数管理・自動 .env ロード）
  - process_priority（プロセス優先度 / CPU affinity 設定）
- ツール
  - paper_verification_report: Paper Trading DB を集計して検証レポートを生成

前提・依存
-----------
- Python >= 3.10（型注釈で | を使用しているため）
- SQLite（Python 組み込みモジュール）
- 必要な外部ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード使用時)
- インストール例:
  pip install duckdb psutil openai requests streamlit

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウト
2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   pip install duckdb psutil openai requests streamlit
4. データディレクトリを作成
   mkdir -p data
   （デフォルトの SQLite / DuckDB ファイルは data/ 以下に置かれます）
5. 環境変数設定
   - プロジェクトルートに .env を置けば自動読み込み（.env.local があれば上書き）
   - 主な環境変数:
     - KABUSYS_ENV : development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN : J-Quants API トークン（必須）
     - KABU_API_PASSWORD : kabuステーション API パスワード（必須）
     - OPENAI_API_KEY : OpenAI API キー（AI 機能を使う場合）
     - PAPER_TRADING_SQLITE_PATH : paper_trading 用 DB（paper_trading モード時）
     - SQLTITE_PATH : 監視 DB パス（デフォルト data/monitoring.db）
     - DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID : LINE 通知に必要
     - PAPER_FILL_MODE : instant | partial | never | reject（paper trading の約定挙動）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, MONITOR_POLL_INTERVAL（秒）など

例 (.env)
----------
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=your_openai_key_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

使い方（起動・ツール）
----------------------

- 監視ポーリング起動（SystemMonitor 単体スクリプト）
  - 簡易起動:
    python -m kabusys.run_monitoring
  - ポーリング間隔の上書き:
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
  - 補足: run_monitoring は常に本番用の sqlite_path を使用（設定に従い data/monitoring.db 等へアクセス）

- 実行エンジン起動（ExecutionEngine）
  - ペーパートレードモード:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
  - 本番モード:
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
  - 補足: paper_trading のときは MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。

- Streamlit 監視ダッシュボード
  - 起動コマンド（プロジェクトルートから）:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を read-only で開き、Positions / Orders / System / Overview を表示します。

- Paper Trading 検証レポート（コマンドライン）
  - 使い方:
    python -m kabusys.tools.paper_verification_report
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで --db を指定して別パスの DB を参照可能。

- AI（ニューススコア／レジーム判定）の呼び出し（ライブラリ API）
  - OpenAI API キーが必要（OPENAI_API_KEY または引数で指定）
  - 例（Python スクリプト／REPL）:
    from kabusys.ai.news_nlp import score_news
    import duckdb, datetime
    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, datetime.date(2026,4,10), api_key="YOUR_KEY")
  - regime_detector も同様に score_regime() を呼ぶことで market_regime テーブルに書き込みます。

設定（Settings）と挙動注意点
--------------------------
- Settings クラスは .env/.env.local/OS 環境変数を読み込みます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。
- KABUSYS_ENV により振る舞いが変わります:
  - development: 開発用（デフォルト）
  - paper_trading: MockBroker を使い DB を分離（PAPER_TRADING_SQLITE_PATH）
  - live: 本番
- PAPER_FILL_MODE（paper_trading 時）:
  - instant | partial | never | reject のいずれか。無効値はエラー。
- kill.flag 機構:
  - KillSwitch が条件を満たすと KILL_FLAG_PATH（デフォルト data/kill.flag）へ理由を書き込み、ExecutionEngine 側で停止検出できます。起動時にフラグをクリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定してください。

監視 DB（スキーマ）
------------------
- init_monitoring_db() により以下のテーブルが作られます（冪等）:
  - system_status (cpu/memory/disk/process_ok, recorded_at)
  - trade_logs (trade イベント履歴, latency_ms カラムを含む)
  - positions (現在ポジション)
  - risk_logs (リスクイベント)
  - dashboard (1行保持の集計: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value)
- MonitoringDB クラスは読み書き用ラッパーを提供し、log_system_status / log_trade_event / upsert_dashboard / log_risk_event などのメソッドを持ちます。

ディレクトリ構成（主要ファイル）
--------------------------------
（src/kabusys をルートとした抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — Settings（環境変数処理）
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite スキーマ / DB ラッパー
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
    - (その他: broker_factory 等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - (その他: data.* モジュールや execution 内の broker 周りなど)

運用上の注意・ヒント
--------------------
- Paper trading は本番 DB と完全に分離する設計になっています。運用時は KABUSYS_ENV の設定に注意してください。
- OpenAI を使う機能はネットワーク障害やレート制限に対してリトライ・フォールバックの実装がありますが、API キーの保護と使用量には注意してください。
- process_priority や CPU affinity の設定はプラットフォーム依存で失敗する可能性があります（権限不足等）。その場合は WARNING を出してスキップします。
- 監視ループは MONITOR_POLL_INTERVAL で間隔を指定できます。0 以下や不正値はデフォルト（60 秒）へフォールバックします。

貢献・拡張案
------------
- 銘柄ごとの lot_size をマスタ化して position_sizing を拡張
- AI モデルやプロンプトのパラメタ化
- Streamlit ダッシュボードの追加ビュー（チャート、時系列）
- DuckDB のデータ更新パイプライン（data.pipeline）との統合強化

以上がリポジトリの概要・セットアップ・使用方法です。README に追加したい実行例や環境固有の手順（systemd サービス化、Docker 化、CI 設定など）があれば教えてください。必要に応じてサンプル .env.example や requirements.txt のテンプレートも作成できます。