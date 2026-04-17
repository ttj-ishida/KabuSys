# KabuSys

日本株自動売買システムのサブセット実装。戦略・ポートフォリオ構築、発注/実行、監視、AI ニューススコアリング、研究ユーティリティを含みます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 実行エンジン起動
  - 監視ループ起動
  - モニタリングダッシュボード（Streamlit）
  - Paper Trading 検証レポート
  - AI 系ユーティリティ（ニューススコア / レジーム判定）
  - 停止・キルスイッチ
- 環境変数（主要）
- ディレクトリ構成

プロジェクト概要
- KabuSys は日本株の自動売買に必要なコンポーネント群（シグナル→ポートフォリオ構築→発注→監視→アラート）を収めたコードベースです。
- DuckDB を用いた時系列データ/ファクター計算、SQLite を用いた監視ログ・注文ログ永続化、OpenAI を使ったニュース NLP などの機能を持ちます。
- 実行環境は本番（live）、ペーパー取引（paper_trading）、開発（development）を切り替え可能です。

機能一覧
- execution
  - OrderManager / ExecutionEngine（発注・状態管理、リコンシリエーション）
  - Broker クライアントファクトリ（実ブローカー / モック切替）
  - Reconciler（起動時の同期処理）
- monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス・データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じた停止フラグ生成）
  - AlertManager（LINE へプッシュ通知）
  - MonitoringEngine（上記を束ねてポーリング）
  - Streamlit ベースの監視ダッシュボード
- portfolio
  - 候補選定・重み付け、ポジションサイズ決定、セクターキャップ／レジーム乗数
- research
  - ファクター計算（Momentum / Volatility / Value）、IC・フォワードリターン計算、統計サマリ
- ai
  - news_nlp（OpenAI を使ったニュースセンチメント → ai_scores 書込）
  - regime_detector（MA200 とマクロニュースで市場レジーム判定）
- tools
  - paper_verification_report（Paper Trading DB から検証レポートを生成）

セットアップ手順
1. リポジトリをクローンし、ソースルートへ移動
   - ルートに `pyproject.toml` 等がある想定
2. Python（3.10 以上を推奨）の仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 必要な主要パッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit
   - （実リポジトリでは requirements.txt / pyproject にまとめる想定）
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数の準備
   - ルートに `.env` を置くか、環境変数を直接設定
   - 自動ロードはデフォルトで有効（`.env` / `.env.local` をプロジェクトルートから読み込み）
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方

実行エンジン起動（ExecutionEngine）
- モジュール: src/kabusys/run_execution.py
- 動作:
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い専用 DB（デフォルト: data/paper_trading.db）に記録します。本番 DB と分離されます。
  - プロセス優先度を "high" に設定し、ExecutionEngine をバックグラウンドスレッドで実行します。stop フラグ（data/stop_requested.flag）が存在すると停止します。
- 起動コマンド:
  - python -m kabusys.run_execution
- 注意:
  - 起動前に kill.flag を削除したい場合は Settings.kill_flag_clear_on_start が有効か確認してください。
  - PID ファイル: data/execution.pid（デフォルト）

監視ループ起動（Monitoring）
- モジュール: src/kabusys/run_monitoring.py
- 動作:
  - SystemMonitor をポーリングして監視データを monitoring DB（デフォルト: data/monitoring.db）へ書き込みます。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 注意: Monitoring は環境にかかわらず本番 sqlite_path（data/monitoring.db）を使用します。
- 起動コマンド:
  - python -m kabusys.run_monitoring
- 停止:
  - 終了は KeyboardInterrupt（Ctrl+C）またはプロジェクト root の data/stop_requested.flag を作成することで行えます。

モニタリングダッシュボード（Streamlit）
- ファイル: src/kabusys/monitoring/streamlit_dashboard.py
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能:
  - ダッシュボード（Overview / Positions / Orders / System）を表示。DB は読み取り専用で開きます。

Paper Trading 検証レポート
- スクリプト: src/kabusys/tools/paper_verification_report.py
- 目的: Paper Trading DB（data/paper_trading.db）から稼働率、注文成功率、レイテンシ等を集計して PASS/FAIL 判定する
- 実行例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で DB パスを指定可能

AI 系ユーティリティ（ニューススコア / レジーム判定）
- news_nlp.score_news(conn, target_date, api_key=None)
  - DuckDB 接続を受け、raw_news を集約して OpenAI Chat API（gpt-4o-mini）でセンチメントを算出し ai_scores テーブルへ書き込みます。
  - OPENAI_API_KEY 環境変数または引数で API キーを渡してください。
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime テーブルへ書き込みます。

停止・キルスイッチ（KillSwitch）
- KillSwitch はリスク条件（ドローダウンやポジション上限）に達した場合に data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- kill.flag の既存確認・クリアは KillSwitch API で行えます。手動クリア:
  - rm data/kill.flag
- run_execution / run_monitoring で用いられている停止フラグ:
  - data/stop_requested.flag — ループ停止用（run scripts が参照）
  - data/kill.flag — KillSwitch が書き込む停止要因（ExecutionEngine 停止トリガ）

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring で使用）
- PID_FILE_PATH: 実行エンジン PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

簡易 .env 例
（ルートに .env を置くことで自動で読み込まれます）
- KABUSYS_ENV=development
- JQUANTS_REFRESH_TOKEN=your_token
- KABU_API_PASSWORD=your_kabu_password
- OPENAI_API_KEY=sk-...
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / 設定管理
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py            — SQLite テーブル初期化 & DB ラッパ
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
      - ... （ExecutionEngine, broker_factory 等）
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
    - utils/
      - process_priority.py
      - __init__.py
- data/                                — (runtime) DB / flag / pid 等を置く場所（存在しない場合は作成）
  - monitoring.db
  - paper_trading.db
  - kabusys.duckdb
  - execution.pid
  - kill.flag
  - stop_requested.flag

補足・運用メモ
- DB の分離:
  - 監視ログ（monitoring.db）は常に指定の sqlite_path を使用します（監視用は環境に依らず本番パスを参照）。
  - Paper Trading（KABUSYS_ENV=paper_trading）は paper_trading 用の SQLite を使用し、本番データと分離されます。
- プロセス優先度:
  - run_* スクリプトは起動時にプロセス優先度を "high" に設定しようとします（psutil による。権限不足時は警告）。
- テスト / CI:
  - Settings の自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ログ:
  - 多くのモジュールは logging.getLogger を使ってログ出力します。実運用では適切なハンドラ/レベルを設定してください。

ライセンス・貢献
- 本 README はコードベースの説明を目的としたドキュメントです。実際の運用ではセキュリティ（APIキー管理等）と資金リスクに十分注意してください。

以上。必要であれば、インストール用の requirements.txt、より詳しい運用手順（systemd サービス定義、Docker 化、CI テスト例）や API モックの使い方についての追記を作成します。どの部分を詳しくしますか？