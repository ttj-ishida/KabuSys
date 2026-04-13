README.md

概要
---
KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。
主な目的は以下です。
- ファクター計算・特徴量探索を行うリサーチ機能（DuckDBベース）
- 注文管理・ブローカ連携を行う Execution 層（本番 / ペーパートレード切替）
- システム稼働・注文状況の監視およびアラート（SQLite を永続化層とする）
- ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI API）
- Paper Trading 検証レポート、Streamlit ダッシュボード等の運用ツール

主な特徴
---
- モジュール分割により「リサーチ」「ポートフォリオ構築」「実行」「監視」「AI」機能が独立
- DuckDB を用いた高性能な時系列/ファクタ処理（prices_daily / raw_financials 等）
- SQLite による監視ログ / 発注ログ保存（monitoring.db / paper_trading.db）
- Paper Trading モードで本番データと完全分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価・レジーム判定（冪等処理・リトライ実装）
- LINE へ通知を送る AlertManager、kill.flag による ExecutionEngine 停止信号機構

必要条件（概略）
---
- Python 3.10+
- pip install 依存パッケージ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボード利用時)
- 標準ライブラリ: sqlite3, logging, argparse 等

（実際の requirements.txt を用意している場合はそちらを使用してください。）

環境変数（主なもの）
---
（プロジェクトは .env / .env.local を自動ロードします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API（リサーチ等で必要）
- KABU_API_PASSWORD — kabuステーション API パスワード

任意（機能に応じて）:
- OPENAI_API_KEY — OpenAI API（AI 機能を使う場合に必須）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知用
- LINE_USER_ID — LINE 通知先ユーザID
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
  - paper_trading: MockBroker を使い data/paper_trading.db に書き込む
  - live: 本番運用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")（デフォルト: instant）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — モニタリング / 制御関連
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト: 60）。無効値はデフォルトにフォールバック
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

セットアップ手順（ローカル）
---
1. リポジトリをクローン
2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
4. .env を作成（.env.example を参考に必要な環境変数を設定）
5. 必要ディレクトリ作成
   - mkdir -p data
6. DuckDB / SQLite の初期化は各スクリプト起動時に自動で行われます（init_monitoring_db を実行）

使い方（主要スクリプト）
---
- 監視ループ起動（Production 監視プロセス）
  - python -m kabusys.run_monitoring
  - 動作: Settings で指定された sqlite_path（監視用）と duckdb_path に接続、SystemMonitor のポーリングを実行
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: MONITOR_POLL_INTERVAL=30）

- ExecutionEngine 起動（注文実行エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します
  - 実行前に .env でブローカ設定等を揃えてください

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH の代わりに指定可）
  - 出力: 稼働率、注文成功率、送信率、レイテンシなどのサマリと PASS/FAIL 判定

- Streamlit ダッシュボード（監視UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データは監視用 SQLite（読み取り専用）から取得します

ライブラリ利用（一部例）
---
- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
- ファクター計算 / リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic
  - これらは duckdb 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照します
- AI 機能
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None) — OpenAI API キーが必要（引数 or OPENAI_API_KEY 環境変数）
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime(conn, date, api_key)

運用上の注意
---
- 設定管理: config.Settings は .env を自動ロードしますが、テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます
- Paper Trading は本番 DB と完全に分離されます。paper_trading モード時は data/paper_trading.db へ書き込みます
- OpenAI 使用時は API レート制限やエラーに対して内部でリトライを行いますが、API キーや料金に注意してください
- set_process_priority を実行します（psutil に依存）。OS により管理者権限が必要な場合があります
- kill.flag（Settings.kill_flag_path）を使って外部から実行エンジン停止をトリガできます。kill.flag は KillSwitch により冪等に書き込まれます

ディレクトリ構成（主要ファイルの説明）
---
src/kabusys/
- __init__.py — パッケージ定義、__version__
- config.py — 環境変数・設定の読み込みロジック（.env 自動ロード、Settings クラス）
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ（psutilベース）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
  - position_sizing.py — 株数算出・リスク/上限処理（calc_position_sizes）
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value などのファクター計算（DuckDB 接続利用）
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ
- ai/
  - news_nlp.py — raw_news を LLM に送り銘柄別センチメントを ai_scores へ書き込む
  - regime_detector.py — ETF MA とマクロニュースを合成して market_regime を書き込む
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 & 永続化 API（MonitoringDB）
  - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、PID 検査
  - trade_monitor.py — 注文滞留・約定価格異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の読み書き
  - alert_manager.py — LINE 通知（クールダウン管理）
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py — Streamlit での監視 UI
- execution/
  - order_repository.py, order_manager.py, reconciler.py, execution_engine.py, broker_factory.py, ...（発注管理・リコンシリエーション・リスク管理等）
- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト
- run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト

開発・テストのヒント
---
- DuckDB / SQLite のテーブル構成やサンプルデータを用意して、研究関数や AI 部分を単体で検証すると良いです
- OpenAI への呼び出し部分はモックしやすく設計されています（テスト時は _call_openai_api をパッチ）
- MonitoringDB は冪等にスキーマ作成 / マイグレーションを行います。初回起動時に自動でテーブルが作成されます

最後に
---
この README はコードベースの主要点をまとめたものです。実運用では個別の設定（API キー管理、権限、監視ポリシー、バックアップ等）を十分に検討してください。必要であれば .env.example のテンプレートや requirements.txt、デプロイ手順を追加で作成できます。