README
=====

概要
----
KabuSys は日本株の自動売買・調査・監視を目的としたモジュール群です。本リポジトリは以下の主要機能を提供します。

- 注文発行・リスク管理・再同期を行う ExecutionEngine
- システム稼働状態・注文の監視・アラート送信を行う Monitoring コンポーネント
- ポートフォリオ構築（候補選定・重み付け・株数決定）ユーティリティ
- ファクター算出・リサーチユーティリティ（DuckDB 経由で時系列データを処理）
- ニュース NLP / 市場レジーム判定（OpenAI を利用したセンチメント評価）
- Paper Trading 向けの検証レポート生成や Streamlit ダッシュボード

設計上のポイント
- 環境設定は .env ファイルまたは環境変数で指定（自動読み込み機構あり）
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離（デフォルト: data/paper_trading.db）
- DB: SQLite（監視ログ等）および DuckDB（時系列・リサーチ用）
- OpenAI API 呼び出しは冪等・リトライ・検証ロジックを組み込んで安全に実行

機能一覧
--------
主要機能のサマリ：

- execution
  - 注文作成、送信、ブローカーとの同期、再起動時のリコンシリエーション
  - RiskManager / OrderManager / Reconciler など
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス存在・データ鮮度監視
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン / ポジション上限検出（kill.flag 書き込み）
  - AlertManager: LINE へのプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用で監視 DB を可視化）
- portfolio
  - 候補選定（スコア降順）、等重/スコア重み付け、ポジションサイズ計算、セクター制約等
- research
  - モメンタム / ボラティリティ / バリュー等のファクター算出
  - 将来リターン計算、IC（情報係数）計算、統計サマリ
- ai
  - news_nlp: raw_news を集約し OpenAI に投げて銘柄ごとのセンチメントを ai_scores に格納
  - regime_detector: ETF MA200 とマクロニュースセンチメントを合成して市場レジーム判定
- tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: 監視 DB を可視化する Streamlit アプリ

セットアップ手順
----------------
前提
- Python 3.9+（pathlib の型や型注釈を利用）
- 必要ライブラリ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボードを使う場合）
これらは requirements.txt がある場合はそれに従ってください（本コードベースに同梱されていない場合は手動でインストールしてください）。

例:
  pip install duckdb psutil requests openai streamlit

環境変数 / .env
- プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
- 自動ロードを無効化する場合:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（抜粋）
- KABUSYS_ENV: 起動環境 ("development" / "paper_trading" / "live") — デフォルト "development"
- SQLITE_PATH: 監視 DB (default: data/monitoring.db)
- DUCKDB_PATH: DuckDB ファイルパス (default: data/kabusys.duckdb)
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（paper_trading 時に使用）
- PAPER_FILL_MODE: paper_trading 時の執行モード ("instant" | "partial" | "never" | "reject")
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で使用）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必要時）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（Execution 時）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

データディレクトリの作成例
  mkdir -p data
  chmod 700 data

初期 DB 作成
- 実行スクリプト（run_monitoring/run_execution）は起動時に init_monitoring_db() を呼び出し、
  必要なテーブルを冪等に作成します。明示的な初期化は不要です。

使い方
------
起動スクリプト

- 監視ループ（SystemMonitor 単体起動）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番用の sqlite_path を使用します（KABUSYS_ENV にかかわらず）。

- ExecutionEngine（売買エンジン）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient（Paper Trading 実装）を使用し、
    PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へログを分離します。

ツール

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  環境変数 PAPER_TRADING_SQLITE_PATH を優先的に参照しますが、--db で直接指定できます。

- Streamlit ダッシュボード（監視 DB を可視化）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

Python API（ライブラリとして）
- ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と target_date を渡して銘柄ごとの ai_scores を書き込みます。
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB 接続を渡して market_regime テーブルへ判定結果を書き込みます。
- portfolio.*, research.* の関数は純粋関数として import して利用できます。
  例:
    from kabusys.portfolio import select_candidates, calc_equal_weights
    from kabusys.research import calc_momentum

監視・制御関連
- KillSwitch（data/kill.flag）: RiskMonitor により条件を満たすと kill.flag が書き込まれ、ExecutionEngine 側で停止トリガーとして利用されます。
- PID ファイル: ExecutionEngine は起動時に PID を pid_file_path に書くことを想定しています。SystemMonitor はこの PID ファイルの存在とプロセス存続をチェックします。

ディレクトリ構成
----------------
（src/kabusys 以下を想定した主要ファイル／モジュール）

- src/kabusys/
  - __init__.py                  — パッケージ定義（__version__ 等）
  - config.py                    — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - run_monitoring.py            — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py             — SQLite ベースの永続化レイヤ（テーブル初期化・読み書き）
  - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常監視
  - risk_monitor.py              — ドローダウン・ポジション上限監視
  - kill_switch.py               — kill.flag 書き込みユーティリティ
  - alert_manager.py             — LINE Push 通知ラッパー
  - monitoring_engine.py         — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py       — Streamlit ダッシュボード

- src/kabusys/execution/
  - order_manager.py             — 注文状態管理
  - reconciler.py                — 起動時の注文/ポジションリコンシリエーション
  - ...（broker_factory / execution_engine / order_repository 等が存在）

- src/kabusys/portfolio/
  - portfolio_builder.py         — 候補選定・スコアソート
  - position_sizing.py           — 株数計算・ユニット丸め・資金配分
  - risk_adjustment.py           — セクター上限・レジーム乗数

- src/kabusys/research/
  - factor_research.py           — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py       — 将来リターン・IC・統計ツール

- src/kabusys/ai/
  - news_nlp.py                  — ニュースセンチメント（OpenAI 呼び出し）
  - regime_detector.py           — 市場レジーム判定（MA200 + マクロセンチメント）

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI

- src/kabusys/utils/
  - process_priority.py          — プロセス優先度 / CPU affinity 設定ユーティリティ

補足（運用上の注意）
-------------------
- OpenAI を利用する機能は API キーが必須です。API 呼び出しの失敗時は「フェイルセーフ」挙動（スコア 0.0 など）を取る設計ですが、API キーの保護とレート制限に注意してください。
- Paper Trading と本番 DB は完全に分離することを推奨します（環境変数でパスを指定）。
- run_monitoring は監視専用 DB（monitoring.db）を使います。誤って production DB を書き換えないようパスを確認してください。
- Process Priority や CPU Affinity の設定は psutil を利用します。権限不足で設定に失敗することがありますが、その場合は警告ログを出してスキップします。

よく使うコマンドまとめ
---------------------
- 監視を起動:
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

- Execution を起動（Paper Trading の例）:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution

- Paper 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンスや貢献方法についてはプロジェクトのルートにある関連ファイル（LICENSE / CONTRIBUTING）を参照してください（本 README には含まれていません）。

以上。質問や README の追記希望（例: サンプル .env、依存関係一覧の追記など）があればお知らせください。