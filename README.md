README — KabuSys（日本株自動売買システム）概要ドキュメント（日本語）
==================================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。本コードベースは
- 実行エンジン（ExecutionEngine）による発注・リスク管理
- 監視（MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- 研究用ファクター計算（momentum / volatility / value 等）
- AI を使ったニュースセンチメント推定（OpenAI）
- Paper Trading 用ツール／レポート生成
を含みます。

主な特徴（機能一覧）
-----------------
- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番／Paper Trading を切り替え（paper_trading 時は MockBroker を使用し DB を分離）
  - ブローカークライアント生成、OrderManager / RiskManager / Reconciler を組み立ててセッション実行
- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor を定期ポーリングし system_status / risk_logs / trade_logs / dashboard を記録
  - MONITOR_POLL_INTERVAL 環境変数で間隔を制御（デフォルト 60 秒）
  - 監視は常に本番 sqlite_path を使用（環境に依らず）
- 監視コンポーネント
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度をチェック
  - TradeMonitor：滞留注文 / 約定価格の異常を検出
  - RiskMonitor：ドローダウン監視、ポジション上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて kill.flag を書き込み ExecutionEngine 停止シグナルを送信
  - AlertManager：LINE Messaging API でアラート送信（クールダウン付き）
  - Streamlit ダッシュボード（監視結果の可視化）
- Portfolio モジュール（純粋関数）
  - 候補選定（select_candidates）
  - 重み付け（等分/スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）
- Research（DuckDB を利用）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC / 統計サマリ等の探索用ユーティリティ
- AI モジュール（OpenAI）
  - news_nlp.score_news：raw_news を集約して LLM で銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector.score_regime：ETF MA とマクロニュースの LLM 評価を合成して market_regime に書き込み
  - 冗長なエラーはフェイルセーフで扱い、リトライ／クリップ等の安全策あり
- Paper Trading ツール
  - tools/paper_verification_report.py：Paper Trading DB を読み取り検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨（typing の union 型表記などを使用）
- SQLite は標準の sqlite3（Python 組込）
- DuckDB, psutil, requests, openai, streamlit 等が必要

推奨手順（最小）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

   （必要に応じて他の依存を追加してください。プロジェクトに requirements.txt があればそれを使用）

4. 環境変数設定
   - プロジェクトルートに .env / .env.local を配置すると自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主要な環境変数（例）
     - KABUSYS_ENV = development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN
     - LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/MEM/DISK 閾値等

5. データディレクトリの作成
   - mkdir -p data

使い方（実行コマンド例）
---------------------
- ExecutionEngine を起動（本番 or paper_trading に依存）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - python -m kabusys.run_execution  （KABUSYS_ENV は .env で指定）

  説明：
  - paper_trading 環境では MockBrokerClient を使用し DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みます。
  - 起動時にプロセス優先度を "high" にセットします。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （ポーリング間隔を秒で上書き）
  - 注意: Monitoring は KABUSYS_ENV に関わらず sqlite_path（本番用）を使用します。

- Streamlit ダッシュボード（監視データ可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で DB を指定（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

- AI モジュール（プログラムから利用）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)

  - regime_detector:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

注意点・運用メモ
---------------
- Settings の自動 .env ロード
  - .env / .env.local はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）から読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
- KABUSYS_ENV 値
  - 有効値: development / paper_trading / live
  - Paper trading は実運用 DB と分離される設計
- MONITOR_POLL_INTERVAL
  - 環境変数でポーリング間隔を秒単位で設定できます（デフォルト 60）。1 未満や負の値は無視されデフォルトにフォールバックします。
- Kill flag
  - KillSwitch はデータディレクトリに kill.flag（デフォルト data/kill.flag）を作成して ExecutionEngine 停止を促します。
  - ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定しておくと起動時に既存の kill.flag を削除できます。
- プロセス優先度設定
  - 起動スクリプトは set_process_priority("high") を呼びます。権限不足等で設定できない場合は警告が出ますが継続します。
- DB スキーマ
  - monitoring_db.init_monitoring_db(conn) は冪等でテーブル・インデックスを作成します。既存 DB に対する軽微なマイグレーション（カラム追加）処理も含みます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
  - パッケージ定義（__version__ など）
- config.py
  - 環境変数読み込みロジックと Settings クラス（アプリ設定）
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じて動作）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト
- execution/
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, execution_engine.py, broker_factory.py, broker_api.py ...
  - 発注ロジック、Order State Machine、リコンシリエーション等
- monitoring/
  - monitoring_db.py
    - system_status / trade_logs / positions / risk_logs / dashboard を管理する永続化層
  - system_monitor.py
    - CPU/Mem/Disk/プロセス/データ鮮度チェック
  - trade_monitor.py
    - 滞留注文・約定異常チェック
  - risk_monitor.py
    - ドローダウン・ポジション上限監視
  - kill_switch.py
    - kill.flag の書き込み/消去ロジック
  - alert_manager.py
    - LINE Push 通知（クールダウン付）
  - monitoring_engine.py
    - 複数モニタを束ねるポーリングエンジン
  - streamlit_dashboard.py
    - Streamlit による監視ダッシュボード
- portfolio/
  - portfolio_builder.py
    - 候補選定・スコアソート
  - position_sizing.py
    - 単元丸め・リスクベース・等分配等の発注株数計算
  - risk_adjustment.py
    - セクターキャップ、レジーム乗数
- research/
  - factor_research.py
    - momentum / volatility / value ファクター計算（DuckDB）
  - feature_exploration.py
    - 将来リターン・IC・統計サマリー等
- ai/
  - news_nlp.py
    - raw_news を OpenAI に送って銘柄別センチメントを計算し ai_scores に書き込む
  - regime_detector.py
    - ETF の MA200 とマクロニュース LLM を合成して market_regime を作成
- tools/
  - paper_verification_report.py
    - Paper Trading DB の検証レポート生成用 CLI

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスや貢献方法を追記してください）

問い合わせ・運用時のヒント
-----------------------
- ログレベルは Settings.log_level で制御（LOG_LEVEL 環境変数）
- DuckDB や SQLite のパスは Settings.duckdb_path / sqlite_path / paper_sqlite_path で指定可能
- OpenAI を使用する機能は API キーが必須（api_key 引数または環境変数 OPENAI_API_KEY）
- LINE 通知を有効にするには LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を設定

以上がコードベースの概要と導入・運用に必要な基本情報です。必要であれば、各モジュールの API 仕様（関数引数・戻り値）や実行フローの図、サンプル .env を追記します。どの情報を優先して追加しますか？