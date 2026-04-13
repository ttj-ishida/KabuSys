README.md

KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤を想定した Python コードベースです。本リポジトリは以下の主要機能を含みます。

- 注文作成・送信・状態管理を行う Execution Engine
- システム稼働状況・注文異常・リスク監視の Monitoring（SQLite にログ永続化）
- ポートフォリオ構築・ポジションサイズ計算などの Portfolio 関連ユーティリティ
- DuckDB を用いたファクター計算・リサーチ機能
- OpenAI を用いたニュース NLP（センチメント集計）およびレジーム判定
- Paper Trading 向けの検証用ツール（レポート生成等）
- Streamlit ベースの監視ダッシュボード

主な特徴
--------
- 環境変数／.env ファイルからの設定読み込み（Settings クラス）
- 本番 DB と paper_trading DB の分離（KABUSYS_ENV による動作切替）
- 監視ループ／Execution の起動スクリプトと監視テーブルの自動初期化
- OpenAI API 呼び出しのリトライや応答バリデーションなどフェイルセーフ設計
- psutil によるプロセス優先度・CPU affinity 設定ユーティリティ
- DuckDB を用いたファクター計算（モメンタム・ボラティリティ・バリュー等）
- Streamlit による簡易ダッシュボード表示

セットアップ手順
----------------
1. Python 環境（3.9+ など）を準備します。仮想環境を使うことを推奨します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストールします。requirements.txt がない場合は主要依存を手動で入れてください。
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. プロジェクトルートに .env（および必要なら .env.local）を作成します。自動読み込みはデフォルトで有効です（Settings モジュール参照）。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリを作成します（デフォルト DB 保存先： data/）。
   - mkdir -p data

主要な環境変数（代表例）
------------------------
- KABUSYS_ENV: 動作モード（development / paper_trading / live） — デフォルト: development
  - paper_trading の場合、paper 用 SQLite （PAPER_TRADING_SQLITE_PATH）に記録されブローカーはモックを使用
- SQLITE_PATH: 監視ログ用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant / partial / never / reject） — デフォルト: instant
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用のリフレッシュトークン（設定必須のプロパティあり）
- KABU_API_PASSWORD: kabuステーション API のパスワード（設定必須のプロパティあり）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知機能を使う場合に設定
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID ファイル・kill.flag のパス（デフォルト: data/execution.pid / data/kill.flag）

簡単な .env 例
----------------
（実際の値は安全に管理してください）
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...

使い方
------
以下は主要スクリプト／コマンドの起動方法例です。

- Monitoring ポーリングループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings で決められた sqlite_path（環境にかかわらず本番 sqlite_path）を使用してログを残します。

- Execution Engine 起動（実際の発注処理）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
  - 起動時にプロセス優先度が "high" に設定され、pid_file（Settings.pid_file_path）を書きます。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - モニタリング用 SQLite を read-only モードで開いて表示します。

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 範囲指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先されます）

監視・停止シグナル
------------------
- ExecutionEngine の強制停止は monitoring の KillSwitch が data/kill.flag を書き込むことで通知されます（KillSwitch クラス）。Execution 側は起動時に kill.flag をクリアする設定（Settings.kill_flag_clear_on_start）等を持ちます。
- 実行中の PID は pid_file（Settings.pid_file_path）に保存され、SystemMonitor は stale PID ファイルを検出して削除・アラートを行います。

DB スキーマ（監視用）
--------------------
monitoring_db.init_monitoring_db により以下のテーブルを作成します（冪等）:

- system_status: cpu/memory/disk/process 状態の時系列ログ
- trade_logs: 発注イベントログ（logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms）
- positions: 現在保有（code を主キー）
- risk_logs: リスクイベント（DRAWDOWN_ALERT, STALE_ORDER など）
- dashboard: 集計（id=1 固定で最新を保持）

主要ディレクトリ構成（src/kabusys）
-----------------------------------
- __init__.py
- config.py
  - Settings クラス: 環境変数 / .env 読み取りロジック
- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading モード対応）
- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込み
  - regime_detector.py: マクロ＋MA を用いた市場レジーム判定と保存
- monitoring/
  - monitoring_db.py: SQLite 永続化層（init / MonitoringDB クラス）
  - system_monitor.py: システム稼働・データ鮮度チェック
  - trade_monitor.py: 注文滞留・約定異常チェック
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag 管理
  - alert_manager.py: LINE 通知ラッパー
  - monitoring_engine.py: 各モニタを束ねるエンジン
  - streamlit_dashboard.py: Streamlit ダッシュボード
- execution/
  - order_manager.py, reconciler.py, ...（注文管理・同期・再実行ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py（銘柄選定・ウェイト・サイズ計算）
- research/
  - factor_research.py, feature_exploration.py（DuckDB を使ったファクター計算・IC 解析）
- tools/
  - paper_verification_report.py（Paper Trading 検証レポート）
- utils/
  - process_priority.py（プロセス優先度 / CPU affinity ユーティリティ）

設計上の注意点 / 運用上のポイント
--------------------------------
- Settings は自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数は優先）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- paper_trading モードでは本番 DB と完全に分離された paper DB を使用することを意図しています（安全対策）。
- OpenAI 関連機能は API キーの設定が必須です。API 呼び出しの失敗時はフェイルセーフ（スコアを 0.0 とする等）で継続する実装です。
- DuckDB はローカル分析向けの高速な列指向 DB です。prices_daily / raw_financials / raw_news 等のテーブル準備が必要です（データ投入は別途実装）。

ライセンス／貢献
----------------
本ドキュメントはコードベースから自動生成した概要です。実際の利用時は各モジュール実装・依存関係を確認し、適切なテスト・セキュリティ対策を行ってください。

補足
----
- ここに記載のコマンドや環境変数、デフォルトパスはコード中の設定（config.py 等）に基づいています。運用前に Settings のプロパティや各スクリプトの挙動を確認してください。
- 実行に必要な依存パッケージ（openai, duckdb, psutil, requests, streamlit など）は環境に応じてインストールしてください。