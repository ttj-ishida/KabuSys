KabuSys — README
=================

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量なPythonパッケージです。本リポジトリには以下の主要コンポーネントが実装されています。

- 注文発行・リスク管理を行う Execution エンジン（ExecutionEngine、OrderManager 等）
- 監視・アラート基盤（SystemMonitor、TradeMonitor、RiskMonitor、AlertManager、KillSwitch）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB を用いたファクター計算）
- ニュース NLP / 市場レジーム判定（OpenAI API を利用した LLM スコアリング）
- Paper Trading の検証レポート生成スクリプト
- Streamlit ベースの監視ダッシュボード

主な設計方針
- DuckDB / SQLite をローカルに利用してデータを管理（外部APIは最小限）
- 本番・Paper Trading を環境変数で切替可能
- LLM 呼び出しはフェイルセーフ（API失敗時は安全側にフォールバック）
- 自動的に .env/.env.local をロード（プロジェクトルート検出あり）※無効化可能

機能一覧
--------
- 注文の作成・送信・同期（OrderManager / Reconciler）
- リスク監視（ドローダウン・ポジション上限・滞留注文・約定異常）
- システム監視（CPU/メモリ/ディスク/プロセス生存確認・データ鮮度）
- LINE 通知（AlertManager によるプッシュ通知、クールダウンあり）
- Paper Trading 環境（API 呼び出しをモック化し DB を分離）
- Paper Trading 検証レポート出力（tools/paper_verification_report.py）
- ニュースセンチメント（OpenAI を使った銘柄別スコアリング）
- 市場レジーム判定（ETF ma200 とマクロ記事の LLM 評価を合成）
- Streamlit ダッシュボード（監視データの可視化）

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈で PEP 604 の | 表記等を使用）
- SQLite は標準ライブラリで利用可能
- DuckDB, psutil, requests, openai, streamlit などを利用

仮想環境と依存パッケージ（例）
1. 仮想環境作成・有効化
   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール（適宜 requirements.txt があればそちらを利用）
   pip install duckdb psutil requests openai streamlit

（プロジェクトによっては追加パッケージがある可能性があります）

環境変数 / .env
- KabuSys は起動時にプロジェクトルート（.git または pyproject.toml がある場所）から .env を自動読み込みします。
- 自動ロードを無効化する場合:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（重要）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース/レジーム判定で使用）
- KABUSYS_ENV: 動作モード ("development" / "paper_trading" / "live")（デフォルト: development）
- PAPER_FILL_MODE: Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite ファイル（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite ファイル（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE通知用
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒、デフォルト 60）

使い方
------

1) 実行エンジンを起動（本番 / Paper 切替）
- デフォルト: KABUSYS_ENV により挙動が変わります。
- Paper Trading を使う例:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  （run_execution.py が ExecutionEngine を初期化して run_session を実行します）
- Live 環境:
  export KABUSYS_ENV=live
  python -m kabusys.run_execution

注意: run_execution はプロセス優先度を高く設定し、DB に接続します。Paper 環境では paper_sqlite_path を使用して本番DBから分離します。

2) 監視ループを起動（SystemMonitor ポーリング）
- デフォルトでは MONITOR_POLL_INTERVAL=60 秒でループしますが、環境変数で上書き可能:
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
- run_monitoring は system monitor をポーリングし、monitoring DB（sqlite）へ状態を永続化します。

3) Streamlit ダッシュボード
- 監視 DB を読み取り専用で可視化します:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
- 指定期間のレポートを標準出力に出力します:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- または DB を明示する:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

5) ニュース NLP / レジーム判定（プログラム呼び出し例）
- OpenAI のキーを設定した上で、モジュール関数をスクリプトや REPL から呼び出せます。

  例: ニューススコア付け
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")

  例: レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, date(2026, 4, 10), api_key="sk-...")

6) テスト用: MonitoringEngine の単回実行
- MonitoringEngine は各モニタを組み合わせた run_once/run があります。単発実行して挙動を確認できます（ユニットテスト向け）。

設定の自動ロード挙動
- 起動時にプロジェクトルートが見つかれば .env を自動でロードします（ただし既存の OS 環境変数は上書きされません）。.env.local があれば上書きされます。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

ディレクトリ構成
----------------

（src 以下を基点に主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py              — パッケージ初期化（バージョン等）
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_execution.py         — ExecutionEngine 起動スクリプト（プロセス優先度設定・DB接続・エンジン起動）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト（CLI）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント取得（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロ記事 LLM）
  - monitoring/
    - __init__.py
    - monitoring_db.py       — SQLite テーブル初期化・読み書きラッパー（MonitoringDB）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — 注文滞留・価格異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック（Execution 停止トリガ）
    - alert_manager.py       — LINE 通知クライアント
    - monitoring_engine.py   — 各 Monitor を束ねるランナー
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py   — 候補選定 / 重み付け
    - risk_adjustment.py     — セクターキャップ / レジーム乗数
    - position_sizing.py     — 株数計算（リスクベース / ウェイトベース）
    - __init__.py
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility ファクター計算
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー
  - execution/
    - order_manager.py       — 注文のステートマシン外向き API
    - reconciler.py          — 再起動時リコンシリエーション
    - （他、broker_factory, execution_engine, order_repository 等が想定）
  - utils/
    - __init__.py
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

データベース / スキーマ関連
- monitoring_db.init_monitoring_db(conn) を呼ぶことで必要なテーブル（system_status, trade_logs, positions, risk_logs, dashboard）とインデックスが冪等的に作成されます。
- モジュール側でマイグレーション（ALTER TABLE でのカラム追加）も実装されています（例: latency_ms, peak_value の追加）。

運用上の注意
------------
- 実際の売買を行う場合は KABUSYS_ENV や API キー、PID / kill flag の取り扱いに細心の注意を払ってください。
- Paper Trading では本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用するため、本番資金に影響させずに検証できます。
- LLM（OpenAI）呼び出しはコストがかかるため、頻繁な自動呼び出しは避けてください。failure時はフェイルセーフ処理が働きますが、APIキーは適切に管理してください。
- process priority / cpu affinity の設定は権限によって失敗する場合があります（警告ログのみ）。

貢献・拡張
----------
- DuckDB のテーブル・スキーマ（prices_daily / raw_financials / raw_news 等）を充実させることで、リサーチや AI モジュールの精度向上が期待できます。
- Broker クライアントは抽象化されているため、新しいブローカー実装を追加して ExecutionEngine に組み込めます。
- Streamlit ダッシュボードや AlertManager の通知チャネルを拡張することが可能です。

ライセンス・その他
------------------
- この README はコードベースの説明を目的としたもので、実際の運用時にはライセンス表示やセキュリティガイドラインを追記してください。

最後に
------
不明点や追加してほしいドキュメント（例えば各モジュールの API 仕様、DB スキーマ定義の詳細、開発用テスト手順など）があれば教えてください。必要に応じて README を拡張します。