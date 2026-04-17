# KabuSys — README

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群と運用ツール群を収めています。戦略構築（ファクター計算）、ポートフォリオ構成、発注エンジン、監視・アラート、Paper Trading 検証、LLM を使ったニュース NLP 等の機能を含みます。

以下は導入・運用に必要な情報の要約です。

プロジェクト概要
- 日本株自動売買システムのコアモジュール群。
- 戦略（リサーチ）用のファクター計算、ポートフォリオ構築（銘柄選定・重み付け・株数算出）を純粋関数で提供。
- 発注周り（OrderManager、ExecutionEngine 等）・リコンシリエーション機能を備えたエンジン。
- 監視サブシステム（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）と通知（LINE）・ダッシュボード（Streamlit）を備える。
- Paper Trading 用の分離された DB と検証レポート生成ツールを提供。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価や市場レジーム判定モジュールを含む（API キー必要）。

主な機能一覧
- 戦略リサーチ
  - モメンタム / ボラティリティ / バリュー系ファクター計算（duckdb 経由）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー
- ポートフォリオ構築
  - 候補選定、等比重／スコア加重、セクター制約の適用、レジーム乗数
  - 株数（ロット）決定、リスク/アグリゲートキャップ処理
- 発注・実行
  - OrderManager / Reconciler / ExecutionEngine（起動スクリプトあり）
  - Paper Trading モード（完全分離された SQLite DB）
- 監視・アラート
  - SystemMonitor（CPU/Memory/Disk、プロセス監視、データ鮮度）
  - TradeMonitor（滞留注文、約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（閾値到達時の停止フラグ書き込み）
  - AlertManager（LINE push 通知）
  - Streamlit ベースの監視ダッシュボード
- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- AI 支援
  - ニュース NLP による銘柄毎センチメント評価（ai.news_nlp.score_news）
  - マクロ + ma200 を合成した市場レジーム判定（ai.regime_detector.score_regime）

セットアップ手順（開発 / ローカル実行向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python と仮想環境
   - 推奨: Python 3.10+
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 主な依存: duckdb, psutil, requests, streamlit, openai
   - 例:
     - pip install duckdb psutil requests streamlit openai

   （requirements.txt がある場合は pip install -r requirements.txt を使用）

4. データディレクトリを作成
   - mkdir -p data
   - 実行時に必要なファイル（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/stop_requested.flag）や PID/flag は起動処理で自動作成されることがあるが、事前に data/ を作っておくと安全です。

5. 環境変数設定
   - プロジェクトルートの .env / .env.local を用意すると自動的に読み込まれます（既存 OS 環境変数が優先）。自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 主な環境変数（最低限必要なもの）
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
     - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
     - KABU_API_BASE_URL — kabusapi の base URL（デフォルト: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時必須）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - KABUSYS_ENV — environment: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject（デフォルト: instant）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/...）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視挙動関連
   - 監視ループ専用環境変数:
     - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）。1未満・不正値は無視されデフォルトにフォールバック。

使い方（代表的なコマンド）
- Execution Engine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込む。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - 起動中は data/execution.pid に PID を書きます。停止は data/stop_requested.flag を書くことで行えます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - Settings の sqlite_path（監視用 DB）に接続して監視データを記録します。MONITOR_POLL_INTERVAL でポーリング間隔を変更可能。
    - Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番想定）を使用します。
    - 停止はプロジェクトルート/data/stop_requested.flag を作成するとループが検知して終了します。

- Streamlit ダッシュボード起動（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ローカルの monitoring.db を読み取り専用で開きます（起動中の MonitoringEngine による書き込みと共存可）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で PAPER_TRADING_SQLITE_PATH を上書きできます。

- AI モジュール（プログラムから呼ぶ）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 呼び出しには OpenAI API キー（OPENAI_API_KEY 環境変数または引数）が必要。一部関数は DB 接続（duckdb）を受け取ります。

運用に関する注意点
- Kill / Stop フラグ
  - data/stop_requested.flag — 実行スクリプト（run_execution, run_monitoring）が監視する停止フラグ（存在で停止）。
  - data/kill.flag — KillSwitch による自動停止指示（ExecutionEngine の停止シグナルとして使用）。
- DB 分離
  - 本番と Paper Trading は SQLite ファイルを分離（Settings で制御）。paper_trading 環境は paper_sqlite_path を使用します。
- ログレベル等は Settings.log_level で制御可能。Settings は起動時に .env を自動読み込みします（プロジェクトルートが検出可能な場合）。
- Process priority と CPU affinity: 起動スクリプトは可能な範囲でプロセス優先度を high に設定します（psutil を使用）。権限がない場合は警告が出てスキップします。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - run_execution.py — ExecutionEngine 起動スクリプト（デーモン的実行）
  - run_monitoring.py — SystemMonitor 起動スクリプト（ポーリングループ）
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクター上限・レジーム乗数
    - position_sizing.py — 株数決定・アグリゲートキャップ等
    - __init__.py
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI 呼び出し・バッチ処理）
    - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース）
    - __init__.py
  - monitoring/
    - monitoring_db.py — SQLite テーブル作成・読み書きラッパー
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるループ / run_once
    - alert_manager.py — LINE push 通知ユーティリティ
    - kill_switch.py — フラグ書き込みによる停止命令
    - streamlit_dashboard.py — Streamlit 監視ダッシュボード
    - __init__.py
  - execution/
    - order_manager.py — OrderManager（State Machine の外向き API）
    - reconciler.py — 起動時のリコンシリエーション処理
    - （その他：broker_factory, execution_engine, order_repository 等 — 発注/リポジトリ周り）
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ヘルパー
    - __init__.py
  - data/ （起動時に生成されることが多い）
    - monitoring.db（デフォルト）
    - paper_trading.db（paper_trading 用）
    - execution.pid
    - stop_requested.flag
    - kill.flag

開発者向けメモ
- Settings はプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を自動ロードします。自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続はリサーチ・AI モジュールで利用します。prices_daily / raw_financials / raw_news 等のテーブルを前提としています。
- MonitoringDB の init_monitoring_db() は冪等で実行できます（マイグレーション処理を内包）。
- AI 関連は OpenAI の API 仕様（レスポンス形式やエラー挙動）に依存します。API キーがない場合、score_* 系は ValueError を投げます（呼出し側で捕捉してください）。
- テスト時は外部 API 呼び出しをモック可能な設計（_call_openai_api のラッパー等）になっています。

よく使うコマンドまとめ
- 実行エンジン起動:
  - KABUSYS_ENV=live python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 責務
- 本 README にはライセンス情報を含めていません。リポジトリに LICENSE ファイルがある場合はそちらを参照してください。
- 自動売買システムは資金・規制上のリスクを伴います。実運用前に十分な検証・レビューを行ってください。

フィードバック / 変更
- ドキュメントやコードに不明点があれば、リポジトリの issue / PR を通して提案してください。

以上。README の補足やフォーマット変更（Markdown の細分化、サンプル .env.example の追記等）が必要であれば教えてください。