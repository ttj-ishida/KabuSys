# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 実行スクリプト群）。  
このリポジトリは注文実行、監視、ポートフォリオ構築、リサーチ、AI を用いたニュース評価などの機能を提供します。

## プロジェクト概要
KabuSys は以下の機能を持つモジュール化された自動売買基盤です。

- 注文発行・状態管理（ExecutionEngine、OrderManager、OrderRepository 等）
- 実行後のリコンシリエーション（Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）およびアラート（LINE）
- Paper Trading（モックブローカー）と本番の明確な分離
- DuckDB を使った市場データ処理・ファクター計算（research）
- OpenAI を用いたニュースの NLP スコアリング / 市場レジーム判定（ai）
- Streamlit ベースの監視ダッシュボード
- 検証レポート生成ツール（paper_verification_report）

## 主な機能一覧
- Execution
  - 実際のブローカーまたはモック（paper_trading）での注文処理
  - リスク管理（position 上限、drawdown 等）
  - 再起動時の自動リコンシリエーション
- Monitoring
  - CPU/メモリ/ディスク、Execution プロセスの監視
  - 注文滞留・約定異常の検出
  - KillSwitch によるフラグファイル経由のエンジン停止指令
  - LINE 通知（AlertManager）
  - Streamlit ダッシュボード表示
- Portfolio
  - 候補選定（スコア順）、等配分・スコア加重配分
  - セクターキャップ、レジーム乗数
  - 株数計算（lot 単位丸め、aggregate cap）
- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）計算
- AI
  - ニュースを OpenAI でセンチメント化して ai_scores に保存
  - マクロニュース + 指標で market_regime を判定
- Tools
  - Paper Trading の検証レポート生成スクリプト

## セットアップ手順

1. 前提
   - Python 3.9+
   - system パッケージ: libpq 等は不要だが、DuckDB / psutil / requests / streamlit / openai 等の Python パッケージが必要

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 例: pip install -r requirements.txt  
     （本リポジトリに requirements.txt が無い場合、少なくとも以下を入れてください）
     - duckdb
     - psutil
     - requests
     - streamlit
     - openai
     - (必要に応じて) sqlite3 は標準ライブラリ

4. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB パス、デフォルト: data/paper_trading.db）
     - SQLITE_PATH（監視 DB パス、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（市場データ DB、デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT

5. データディレクトリ
   - data/ 配下に DB やフラグファイルが作成されます:
     - data/monitoring.db — SQLite（監視ログ）
     - data/paper_trading.db — Paper Trading 用 SQLite（KABUSYS_ENV=paper_trading）
     - data/kabusys.duckdb — DuckDB（市場データ）
     - data/execution.pid, data/stop_requested.flag, data/kill.flag などの制御ファイル

## 使い方（代表的なコマンド）

- ExecutionEngine（注文実行エンジン）起動
  - production / development:
    - python -m kabusys.run_execution
  - Paper Trading モード（モックブローカー、DB 分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 注意: 実行時に data/execution.pid が作成され、stop_requested.flag や data/kill.flag を検知すると停止します。

- Monitoring（ポーリング監視）起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）を使用して永続化します。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）。

- AI 機能（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも api_key が None の場合は環境変数 OPENAI_API_KEY を参照します。

- ライブラリとしての利用例（Python コード内）
  - ポートフォリオ計算:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

## 注意事項 / 実装上のポイント
- Settings は .env / .env.local をプロジェクトルートから自動読み込みします（CWD に依存しない検出ロジック）。
- Monitoring は monitoring DB に対して常に「本番設定の sqlite_path」を使います（監視の DB は環境に依存せず基本的に固定）。
- Paper Trading モードでは実ブローカーを使わず MockBrokerClient を使用し、DB は PAPER_TRADING_SQLITE_PATH に分離されます（本番 DB を汚さない）。
- run_execution/run_monitoring は起動時にプロセス優先度を high に設定しようとします（psutil を使用）。権限やプラットフォームによっては警告が出ますが継続します。
- KillSwitch / stop_requested.flag:
  - KillSwitch はリスク条件（例: drawdown、ポジション上限）により data/kill.flag を書き込み、ExecutionEngine 側はそれを検出して安全停止します。
  - run_* スクリプトは data/stop_requested.flag の存在も検出してループを終了します（外部からの停止機構）。

## ディレクトリ構成

概略（src/kabusys 以下）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     — 環境変数 / Settings
    - run_execution.py              — ExecutionEngine 起動スクリプト
    - run_monitoring.py             — SystemMonitor 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py (省略されている実装ファイルがある想定)
      - broker_factory.py
      - broker_api.py
      - order_record.py
      - order_repository.py
      - ...（ブローカー関連）
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
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
    - data/ (実行時に生成されることが多い)
      - monitoring.db
      - paper_trading.db
      - kabusys.duckdb
      - execution.pid
      - kill.flag
      - stop_requested.flag
    - utils/
      - process_priority.py
      - __init__.py

（上記は主なファイルを抜粋したものです。実装ファイルはさらに細分化されています。）

## よくある運用フロー
1. 市場データ（DuckDB）を整備する（prices_daily / raw_financials / raw_news 等）。
2. ExecutionEngine を起動（KABUSYS_ENV による切替）。
3. MonitoringEngine を起動してシステム稼働状態を監視・ログ収集。
4. 必要に応じて Streamlit ダッシュボードで状況確認。
5. Paper Trading の検証結果は tools/paper_verification_report で集計。

## トラブルシューティング
- MONITOR_POLL_INTERVAL に 0 や負の数を設定すると無効値としてログ警告が出てデフォルト 60 秒にフォールバックします。
- OpenAI 周りはネットワーク・429 等でリトライ実装がありますが、API キー未設定時は明示的なエラーを投げます。環境変数 OPENAI_API_KEY を設定してください。
- DuckDB / SQLite ファイルにアクセスできない場合、Streamlit ダッシュボードは読み取り専用 URI を使って接続するため DB の存在とアクセス権を確認してください。

---

必要であれば README に以下を追加できます：
- requirements.txt の推奨内容
- より詳細な .env.example（サンプル環境変数）
- デプロイ手順（systemd / docker-compose）
- テストの実行方法

ご希望があれば上記を追記します。