README
=====

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした Python 製のコードベースです。本リポジトリは以下の主要機能を含みます。

- 発注実行エンジン（ExecutionEngine、OrderManager、Reconciler 等）
- 監視サブシステム（SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、統計サマリ）
- AI 支援機能（ニュースの NLP スコアリング、レジーム判定。OpenAI を利用）
- 運用ツール（Paper Trading 検証レポート生成、Streamlit ダッシュボード）

設計方針の一部：
- DB は SQLite（監視用）および DuckDB（時系列・研究用）を使用
- 環境依存値は .env / 環境変数から読み込み（自動ロードあり）
- 本番/ペーパー環境は KABUSYS_ENV により切替（paper_trading は本番 DB と分離）

機能一覧
--------
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、Execution の PID 存在、データ鮮度を監視しログ化
  - TradeMonitor: 滞留注文や約定価格の異常を検出してリスクログ登録
  - RiskMonitor: ドローダウンやポジション上限をチェックしてダッシュボード/リスクログを書き込み
  - MonitoringEngine: 上記の監視をまとめてポーリング、アラート管理・KillSwitch 評価を実行
  - AlertManager: LINE Push による一方向通知（トークン未設定時はログのみ）
  - Streamlit ダッシュボード: 監視 DB を可視化

- 発注 / 実行
  - OrderManager: Signal → DB 登録 → Broker 呼び出しの状態遷移を管理
  - Reconciler: 起動時の自動復旧（OrderSent の照合、ポジション差分検出）
  - ExecutionEngine 起動スクリプト（run_execution.py）: BrokerFactory により実際の/モックのブローカーを生成

- ポートフォリオ構築
  - 銘柄選定（score/ランク順）、等金額/スコア加重配分、リスクベースのポジションサイジング
  - セクター上限適用、レジーム乗数

- 研究
  - ファクター計算（Momentum / Volatility / Value）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリ）
  - DuckDB を用いた高速集計

- AI（OpenAI）
  - news_nlp.score_news: raw_news を LLM（gpt-4o-mini 等）でセンチメント評価し ai_scores に保存
  - regime_detector.score_regime: MA200 乖離とマクロニュースセンチメントを合成して market_regime を判定

- ツール
  - paper_verification_report: paper_trading DB から検証レポートを生成
  - streamlit_dashboard: 監視 DB を使ったダッシュボード表示

セットアップ手順
----------------
前提:
- Python 3.10+（typing の新構文を使用）
- SQLite（標準ライブラリで利用可）
- DuckDB, psutil, requests, openai, streamlit などの外部パッケージ

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を推奨）

3. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

主要な環境変数（一部、デフォルト値を併記）
- KABUSYS_ENV: 起動環境。valid: development | paper_trading | live （デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: ブローカー API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（未設定でも動作）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill switch のフラグファイル（デフォルト: data/kill.flag）
- PAPER_FILL_MODE: paper_trading 時のモック約定動作（instant/partial/never/reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- LOG_LEVEL 等の閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT 等

例: .env の最小例
- KABUSYS_ENV=development
- OPENAI_API_KEY=sk-...
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

使い方
------
主要な実行コマンド例:

- 監視ループ（Monitoring の単体起動）
  - 環境変数 MONITOR_POLL_INTERVAL で間隔を秒で設定可能（デフォルト 60）。
  - python -m kabusys.run_monitoring
  - 仕様: 起動時にプロセス優先度を "high" に設定し、SQLite（settings.sqlite_path） と DuckDB に接続して SystemMonitor のループを実行します。

- 実行エンジン起動（注文実行）
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient が使用され、data/paper_trading.db に記録され本番 DB と分離されます。
  - python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB ファイル指定: --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）

- Streamlit ダッシュボード（監視 DB の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは read-only モードで SQLite に接続します（URI モード）。

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要。モジュールから直接呼び出して score_news / score_regime を使用します。
  - 例: from kabusys.ai.news_nlp import score_news
         score_news(duckdb_conn, date(2026,4,1), api_key="sk-...")

注意点 / 実運用のヒント
- init_monitoring_db() は冪等であり、起動時に不足カラムのマイグレーションも行います。
- run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番パス）を使用します（監視は本番 DB を参照する設計）。
- run_execution は KABUSYS_ENV==paper_trading の場合 paper_sqlite_path を使用して本番 DB と分離します。
- process_priority の設定はプラットフォーム依存で失敗することがあります（警告ログのみ）。
- OpenAI 呼び出しはレート制限・ネットワーク障害を考慮したリトライ実装が含まれていますが、API キーと使用料に注意してください。
- kill.flag により ExecutionEngine を安全に停止させる仕組みがあります。KillSwitch は kill.flag の存在や理由をファイルに記録します。

ディレクトリ構成
----------------
主要ファイル・モジュールの概観（src/kabusys 以下）

- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py               — ExecutionEngine 起動スクリプト（paper_trading モード対応）
- config.py                      — 環境変数 / 設定読み込みロジック（.env 自動ロード含む）
- __init__.py                    — パッケージ定義

- monitoring/
  - monitoring_db.py             — SQLite 用の永続化層（テーブル作成、ログ API）
  - system_monitor.py            — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py             — 注文滞留・約定異常監視
  - risk_monitor.py              — ドローダウン / ポジション上限監視
  - monitoring_engine.py         — 各 Monitor を束ねるポーリングエンジン
  - kill_switch.py               — kill.flag 管理
  - alert_manager.py             — LINE 通知（push）
  - streamlit_dashboard.py       — Streamlit ダッシュボード

- execution/
  - order_manager.py             — オーダー状態遷移とブローカー呼び出しの高レベル管理
  - reconciler.py                — 起動時のリコンシリエーション（復旧）
  - （その他ブローカー / order_repository 等は同階層に存在）

- portfolio/
  - portfolio_builder.py         — 候補選定、重み計算
  - risk_adjustment.py           — セクターキャップ、レジーム乗数
  - position_sizing.py           — 発注株数計算（単元丸め、aggregate cap）

- research/
  - factor_research.py           — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py       — 将来リターン、IC、サマリ統計

- ai/
  - news_nlp.py                  — raw_news を LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py           — MA200 + マクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成ツール

補足・問い合わせ
----------------
- コード内の docstring / ログメッセージは日本語で意図や制約が明記されています。初期導入や運用時は各モジュール内のコメントを参照してください。
- セットアップや実行で問題が発生した場合は、ログレベルを DEBUG に上げて（LOG_LEVEL 環境変数）詳細ログを確認してください。

以上。必要があれば、インストール用の requirements.txt 作成や、よくあるエラーと対処集（トラブルシューティング）を追加で作成します。どの情報が欲しいか教えてください。