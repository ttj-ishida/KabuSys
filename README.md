KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。  
主に次の用途を持ちます:

- 発注エンジン（ExecutionEngine）による注文管理・リスク管理・ブローカー連携
- 監視（Monitoring）: システム状態・注文状況・リスク指標のポーリングとアラート／Kill Switch
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制約）
- リサーチ（ファクター計算、特徴量探索、IC計算 等）※DuckDB を利用
- AI 関連（ニュースセンチメントの LLM スコアリング、市場レジーム判定）
- ツール（ペーパートレード検証レポート生成 等）
- 設定ウィザード・設定検証 CLI

主な設計方針:
- 設定は .env または環境変数で管理（config_setup.py で対話式生成、validate_config.py で検証）
- DuckDB / SQLite をデータ格納に使用（分析用 DuckDB、監視/発注ログは SQLite）
- Paper Trading 環境は本番 DB と分離（data/paper_trading.db を利用）
- OpenAI API を用いた NLP 処理はフェイルセーフ設計（API 失敗時はスキップやフォールバック）

機能一覧
--------
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）
  - 対話式 .env 作成: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
- 実行（Execution）
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
  - Paper Trading モード: KABUSYS_ENV=paper_trading（MockBroker を使用、専用 SQLite を使用）
  - リスク管理（RiskManager、Reconciler、OrderManager 等）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine
  - run_monitoring.py により定期ポーリング（MONITOR_POLL_INTERVAL で間隔調整）
  - Kill Switch（data/kill.flag）生成による安全停止
  - 監視結果の永続化（SQLite の monitoring DB）
- ポートフォリオ構築
  - 候補選定、等金額/スコア加重、リスクベース配分、セクターキャップ、レジーム乗数
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC、統計サマリ等
- AI（OpenAI）
  - ニュース記事を LLM でスコアリングし ai_scores へ格納
  - 市場レジーム判定（ETF MA + マクロニュースセンチメント）
- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

前提 / 必要環境
----------------
- Python 3.9+
- 必須パッケージ（主要なもの）
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で YAML をパースする場合）
- SQLite（標準ライブラリに含まれます）
- ネットワーク接続（OpenAI / 外部 API 利用時）

セットアップ手順
----------------
1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - python -m venv venv
   - source venv/bin/activate（Windows は venv\Scripts\activate）

2. 依存パッケージをインストールします（requirements.txt がない場合は手動で）。
   - pip install duckdb psutil openai PyYAML

3. .env を作成します（対話式推奨）。
   - python -m kabusys.config_setup
   ウィザードが .env を生成します。必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   その他オプション: KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, LINE_* など。

4. 設定を検証します。
   - python -m kabusys.validate_config
   - 問題があれば修正し、必要なら --strict モードで警告を失敗扱いに。

5. データ / ログ ディレクトリを確認（自動で作成される場合があります）。
   - デフォルト SQLite/DuckDB パス: data/monitoring.db, data/kabusys.duckdb
   - ログは logs/<app>.log に出力（日次ローテーション、30日保持）
   - PID / フラグファイル： data/execution.pid, data/kill.flag, data/stop_requested.flag など

使い方（起動・コマンド）
-----------------------
- ExecutionEngine 起動（本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - Paper Trading の場合: export KABUSYS_ENV=paper_trading（Unix 系）
    - Paper Trading では MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  - 監視は常に本番の sqlite_path を使用（環境に依らず）

- 設定ウィザード / 検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連関数（プログラム内から呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーは OPENAI_API_KEY 環境変数または api_key 引数で指定

運用上のポイント
-----------------
- Kill Switch:
  - RiskMonitor やその他条件で KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨（自動クリアは危険）。

- Paper Trading:
  - 完全に分離された DB（data/paper_trading.db）を使います。実際の発注は発生しません。

- ログ:
  - setup_logging 関数で stdout と日次ローテーションファイルに出力されます。ログディレクトリが作れない場合はコンソールのみで継続します。

- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げようとします。権限により失敗しても警告で済みます。

ディレクトリ構成（主要ファイル）
-------------------------------
src/
  kabusys/
    __init__.py
    config.py                 # 環境変数 / Settings 管理（自動 .env ロード含む）
    config_setup.py           # .env 対話式ウィザード
    validate_config.py        # 設定検証 CLI
    run_execution.py          # ExecutionEngine 起動スクリプト
    run_monitoring.py         # SystemMonitor ポーリング起動スクリプト

    utils/
      logging_setup.py        # 統一的ログ設定ユーティリティ
      process_priority.py     # プロセス優先度 / CPU affinity ユーティリティ
      __init__.py

    execution/                # 発注エンジン関連（OrderManager, RiskManager, Engine等）
      ... (実装ファイル群)

    monitoring/
      monitoring_db.py        # 監視用 SQLite のスキーマ + 永続化 API
      system_monitor.py       # システム・データ鮮度チェック
      trade_monitor.py        # 注文関連の監視（滞留/約定異常等）
      risk_monitor.py         # ドローダウン・ポジション上限監視
      kill_switch.py          # kill.flag の管理
      monitoring_engine.py    # 各 Monitor を束ねるエンジン
      alert_manager.py        # アラート送信（LINE 等。実装に依存）

    portfolio/
      portfolio_builder.py    # 候補選定・重み付け
      position_sizing.py      # 株数算出・スケーリング
      risk_adjustment.py      # セクター制約・レジーム乗数
      __init__.py

    research/
      factor_research.py      # モメンタム・ボラティリティ・バリューの計算
      feature_exploration.py  # 将来リターン・IC・統計サマリ
      __init__.py

    ai/
      news_nlp.py             # ニュース記事の LLM スコアリング（ai_scores へ書き込み）
      regime_detector.py      # 市場レジーム判定（MA + マクロセンチメント）
      __init__.py

    data/                     # 実行時に作成される既定の DB / flag / pid / ログ等（git 管理しない）
      (例) monitoring.db, paper_trading.db, kabusys.duckdb, kill.flag, execution.pid

    tools/
      paper_verification_report.py  # Paper Trading 検証レポート生成
      __init__.py

補足（開発者向け）
------------------
- DuckDB 接続を渡して純粋関数的にリサーチ処理を呼ぶ設計です（副作用が少ない）。
- OpenAI 呼び出し周りはネットワーク障害やレート制限を考慮したリトライ設計・フォールバック実装になっています。
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml）を起点に行われ、自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリに含まれる LICENSE ファイル等を参照してください（本説明では明示していません）。

以上が本リポジトリの概要と基本的な使い方です。README に含めてほしい追加の内容（例: 実行例、環境変数の完全一覧、CI 設定、開発フロー等）があれば指示してください。