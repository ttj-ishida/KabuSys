# KabuSys

日本株向け自動売買システムのモジュール群。戦略、ポートフォリオ構築、発注実行、監視、AI（ニュースセンチメント／レジーム判定）などを含むライブラリ／実行スクリプト群です。

## 概要
このリポジトリは、次の主要機能を持つコンポーネント群から構成されています。

- 発注エンジン（ExecutionEngine）と OrderManager / Reconciler によるブローカー連携・自動復旧
- 監視（MonitoringEngine）: システムリソース、データ鮮度、注文滞留、リスク（ドローダウン等）を定期チェックしログ/アラート出力
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制限等）の純粋関数群
- リサーチ（ファクター計算・特徴量探索）
- AI モジュール: ニュースを OpenAI に送りセンチメントを算出（ai.news_nlp）、マクロ＋ETF MA による市場レジーム判定（ai.regime_detector）
- ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード

設計方針の一部:
- データベースは DuckDB（時系列・リサーチ）と SQLite（監視ログ・発注ログ／Paper Trading）を併用
- Paper Trading は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- .env / 環境変数により挙動を切り替え（Settings クラス）

## 主な機能一覧
- SystemMonitor: CPU/メモリ/ディスク、実行プロセスの監視、データ鮮度チェック
- TradeMonitor: 注文滞留（stale）・約定異常価格の検出
- RiskMonitor: ドローダウン・ポジション上限の監視とリスクログ格納
- KillSwitch: 指定条件で data/kill.flag を生成して ExecutionEngine を停止させる仕組み
- AlertManager: LINE Messaging API を使った通知（クールダウン機能付き）
- Portfolio モジュール: 候補選定、等配分／スコア配分、リスクベースの株数計算、セクターキャップ適用、レジーム乗数
- AI モジュール: OpenAI を用いたニュースセンチメント（ai_scores テーブルへ書込み）／マクロセンチメント + ETF MA によるレジーム判定
- Streamlit ダッシュボード: 監視 DB を可視化
- Tools: paper_verification_report（Paper Trading の稼働性／成功率／レイテンシ等の検証レポート出力）

## 動作要件（依存）
少なくとも以下パッケージを想定しています（requirements.txt がある場合はそちらを使用してください）:

- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード起動時)
- openai（OpenAI クライアント。ai モジュール使用時）
- その他: 標準ライブラリ（sqlite3 等）

例:
pip install duckdb psutil requests streamlit openai

※OS によっては streamlit や psutil の追加設定が必要です。

## 環境変数（主なもの）
Settings クラスで参照される主な環境変数とデフォルト：

- KABUSYS_ENV: 起動環境。development / paper_trading / live （デフォルト: development）
  - paper_trading の場合、MockBroker を使用し paper_sqlite_path に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager 用（省略可）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動。instant|partial|never|reject（デフォルト instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など（詳細は Settings クラス参照）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読込を無効化

Settings ではプロジェクトルートの .env/.env.local を自動読み込みします（OS環境変数優先）。自動読み込みを無効にするには上記フラグを使います。

## セットアップ手順（開発マシン）
1. リポジトリをクローン
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存インストール
   - pip install -r requirements.txt  （もし用意されていなければ手動で必要パッケージを pip install）
4. 環境変数の準備
   - プロジェクトルートに .env（もしくは .env.local）を作成して上記必須値を設定
   - 例:
     KABUSYS_ENV=development
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
5. データディレクトリ作成
   - mkdir -p data

※ paper_trading モードで検証する場合は PAPER_TRADING_SQLITE_PATH を設定するかデフォルト data/paper_trading.db が使用されます。

## 使い方（主要スクリプト）
以下はパッケージモードで実行する例です（プロジェクトルートで実行）。

- 監視ループの起動
  - 簡易:
    python -m kabusys.run_monitoring
  - ポーリング間隔を変更:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path（本番 DB）を使用する点に注意

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBroker を使い PAPER_TRADING_SQLITE_PATH に記録（本番 DB と分離）
  - エンジンは data/stop_requested.flag を検知すると停止します。起動時に data/kill.flag をクリアする設定もあります（Settings.kill_flag_clear_on_start）

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB（読み取り専用）を参照して Overview / Positions / Orders / System を表示

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（プログラム API）
  - ニューススコア付与:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

  どちらも OPENAI_API_KEY の設定が必要です（引数で渡すことも可能）。

## 停止・フラグについて
- data/stop_requested.flag: run_monitoring / run_execution が外部からの停止要求を検知するために使う。存在すると loop を抜けます。
- data/kill.flag: KillSwitch が生成するファイル。ExecutionEngine を即座に停止させるための信号として利用（存在チェックと書き込み・削除 API が用意されています）。
- data/execution.pid: 実行中の ExecutionEngine の PID を格納するファイル。SystemMonitor は PID 存在チェックでプロセス健全性を判断します。

## 監視・リスク閾値（デフォルト）
Settings で設定可能（環境変数経由）:

- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT（監視アラート閾値）
- RiskMonitor のドローダウン閾値既定は 10%（内部デフォルト dd_threshold=0.10）
- Position 上限デフォルトは max_positions=10（RiskMonitor）

## ディレクトリ構成（主要ファイル）
以下は src/kabusys の主要ファイル構成（抜粋）です：

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 監視ログ層
    - monitoring_engine.py         — 監視エンジン
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他 broker / engine / order_repository 等)
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
  - data/ (実行時生成されるディレクトリ: monitoring/pid/flags/db など)

（実際のファイルツリーはリポジトリ内を参照してください）

## 開発メモ / 注意点
- Settings はプロジェクトルートの .env/.env.local を自動読み込みします。テストや CI で自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading モードは本番 DB とデータ分離されています。誤って本番 DB に書き込まないように注意してください。
- OpenAI API 呼び出しは外部ネットワーク依存・レートリミットがあるため、エラー時はフェイルセーフ（スコア 0.0 フォールバックや部分スキップ）が組み込まれていますが、API キー管理には注意してください。
- monitoring_db.init_monitoring_db は冪等でテーブル・カラムの簡単なマイグレーションを行います。運用時はバックアップを推奨します。
- process_priority.set_process_priority はプラットフォーム差分を吸収しますが、権限不足で設定できない場合は警告を出して続行します。

---

README に書かれている以外の実行方法や設定、運用ポリシーについては各モジュールのドキュメント文字列（docstring）を参照してください。必要であればサンプル .env.example や requirements.txt、運用ガイドのテンプレートを追加で作成できます。どの情報を追記したいか教えてください。