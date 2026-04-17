# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買 / 研究 / 監視用のミニマルなフレームワークです。本リポジトリには以下の主要機能を持つモジュール群が含まれています。

- 注文実行エンジン（ExecutionEngine）と OrderManager / Reconciler による再同期処理
- 監視サブシステム（System / Trade / Risk Monitor）と通知（LINE）
- Paper Trading 用の分離された SQLite DB と検証レポート生成ツール
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- 研究モジュール（ファクター計算、特徴量探索、IC 計算）
- AI 関連ユーティリティ（ニュースの NLP スコアリング、レジーム判定）
- Streamlit ベースの監視ダッシュボード

主要機能
---
- 実行環境（本番 / paper_trading / development）の切替
- Paper Trading と Live のデータ分離（PAPER_TRADING_SQLITE_PATH）
- 監視ループ（SystemMonitor）による CPU/メモリ/ディスク/プロセス状態・データ鮮度監視および永続化（SQLite）
- TradeMonitor による滞留注文・約定異常検出
- RiskMonitor によるドローダウン・ポジション上限監視と Kill Switch で ExecutionEngine 停止
- LINE 通知（AlertManager）によるクールダウン管理付きプッシュ通知
- OpenAI を使ったニュースセンチメント（ai.news_nlp）とマクロ判定（ai.regime_detector）
- DuckDB を用いた価格・財務データ集計とファクター計算（research パッケージ）
- Streamlit ダッシュボードでの可視化

前提条件（主な依存）
---
- Python 3.9+
- 必要ライブラリ（例）:
  - duckdb
  - psutil
  - requests
  - streamlit
  - openai
  - sqlite3（標準）
- OS: Linux / macOS / Windows（プロセス優先度設定はプラットフォーム依存で制限あり）

インストール
---
1. リポジトリをクローンして作業ディレクトリに移動
2. 仮想環境を作成して依存をインストール（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -r requirements.txt
     （requirements.txt がない場合は上記の主要依存を個別に pip install）

環境変数（.env）
---
プロジェクトは自動でプロジェクトルートの .env および .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。最低限設定が必要な変数例:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (ai 機能を使う場合必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用（任意）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

データ・PID・フラグファイル
---
- data/execution.pid — 実行エンジンの PID（ExecutionEngine が書き込む）
- data/stop_requested.flag — 外部からの停止要求検知用フラグ（run_monitoring / run_execution が参照）
- data/kill.flag — KillSwitch が書き込む停止理由（ExecutionEngine に停止シグナルを通知する）
- DB ファイル: data/monitoring.db（監視ログ）、data/paper_trading.db（paper_trading 用）、data/kabusys.duckdb

セットアップ手順（簡易）
---
1. 必要なフォルダを作成:
   - mkdir -p data
2. .env をプロジェクトルートに作成（.env.example を参考に）
3. DuckDB・SQLite のパスは Settings によりデフォルトで data 以下を使用するため、通常は上記だけで OK
4. 監視 DB 初期化は run_monitoring / run_execution が自動で行う

使い方（コマンド例）
---
- 監視ループを起動（プロジェクトルートで）:
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可（秒）
  - 監視は Settings.sqlite_path を使用（環境に依らず本番 sqlite を使用）

- 実行エンジンを起動:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると Mock ブローカーを使用し、PAPER_TRADING_SQLITE_PATH に書き込む:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI 機能（ニューススコアリング / レジーム判定）をプログラムから呼び出す:
  - kabusys.ai.score_news(conn, target_date, api_key=...)  # ai/news_nlp.py
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)  # ai/regime_detector.py

停止・フラグ制御
---
- 外部からプロセス（run_monitoring / run_execution）を安全に停止したい場合:
  - touch data/stop_requested.flag
  - これらのスクリプトはループ中にファイル存在をチェックして正常終了します
- 実行エンジンを強制停止させたい（Kill Switch）:
  - KillSwitch が条件を満たした場合 data/kill.flag を書き込み、run_execution 側で検知して停止します
- kill.flag を手動でクリアするにはファイルを削除:
  - rm data/kill.flag
  - または Python で KillSwitch.clear() を使用

開発者向け情報（主なモジュール）
---
- kabusys/config.py
  - Settings クラス: 環境変数のラッピング。KABUSYS_ENV、DB パス、各種閾値などを提供
  - 自動で .env/.env.local をプロジェクトルートから読み込む
- kabusys/run_monitoring.py
  - SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL で間隔を変更可
- kabusys/run_execution.py
  - ExecutionEngine を組み立てて実行。paper_trading 環境では paper DB を使用
- kabusys/monitoring/*
  - MonitoringDB（SQLite テーブル定義/マイグレーション）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / AlertManager / KillSwitch
  - streamlit_dashboard.py（ダッシュボード）
- kabusys/execution/*
  - OrderManager、Reconciler、OrderRepository など、発注・リコンシリエーション周り
- kabusys/portfolio/*
  - 銘柄選定、重み算出、セクター制限、ポジションサイズ計算
- kabusys/research/*
  - ファクター計算（momentum/value/volatility）、将来リターン、IC、統計サマリー
- kabusys/ai/*
  - news_nlp.py（ニュースセンチメント、OpenAI 呼び出し）
  - regime_detector.py（マクロ判定と MA200 を組み合わせたレジーム判定）

ディレクトリ構成（抜粋）
---
src/kabusys/
- __init__.py
- config.py                    — 環境変数 / Settings
- run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
- run_execution.py             — ExecutionEngine 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- ai/
  - news_nlp.py                 — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py          — 市場レジーム判定
- monitoring/
  - monitoring_db.py            — SQLite テーブル初期化 / MonitoringDB
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - alert_manager.py
  - kill_switch.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - ...                         — broker_factory 等（発注ロジック）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - process_priority.py         — psutil を用いた優先度/affinity ユーティリティ

よくある質問 / 注意点
---
- DB の初期化は run_monitoring / run_execution が自動で行います（init_monitoring_db）。
- KABUSYS_ENV によって paper_trading 用の DB を分離しているため、実稼働 DB を誤って書き換えないよう注意してください。
- OpenAI を利用する機能は API キーが必要です。API コールはネットワークエラー・429・5xx に対してリトライロジックを持っていますが、コストとレート制限に注意してください。
- process priority や cpu affinity の設定は権限によって失敗する可能性があります（警告ログでスキップされます）。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くことを推奨します（起動時に ?mode=ro を付与）。

ライセンス・貢献
---
（ライセンス情報や貢献方法が別途ある場合はここに追記してください）

以上がこのコードベースの概観と基本的な操作手順です。必要であれば各モジュールの API 使用例や .env.example の具体的サンプル、起動スクリプトの systemd / supervisor 設定例なども追加できます。どの情報を優先して追加しましょうか？