KabuSys — 日本株自動売買プラットフォーム
=====================================

概要
----
KabuSys は日本株向けの自動売買システムの一部実装です。本リポジトリには以下の主要コンポーネントが含まれます：

- ExecutionEngine: 注文作成・送信・状態管理、リコンシリエーション機能
- Monitoring: システム状態・注文状態・リスクの定期監視、アラート送信（LINE）
- Research / Factors: DuckDB 上の株価・財務データからファクターや将来リターンを計算
- Portfolio construction: 候補選定、重み計算、ポジションサイジング、セクター制約など
- AI 補助: ニュースのセンチメント評価（OpenAI）、市場レジーム判定
- ユーティリティ: プロセス優先度設定、Streamlit ダッシュボード、検証レポート等

主な特徴
--------
- DuckDB / SQLite ベースのローカルデータ分析と監視ログ保存
- Paper trading 環境の完全分離（専用 SQLite DB）
- LLM を使ったニュースセンチメント（OpenAI）・レジーム判定をサポート
- 常時監視ループ（polling）＋ kill/stop フラグによる安全停止
- Streamlit での監視ダッシュボード、検証レポート生成ツール

準備・セットアップ
------------------

前提
- Python 3.9+（typing の表記等に依存）
- OS: Linux / macOS / Windows（ただし process priority / CPU affinity の一部機能はプラットフォーム依存）

推奨手順（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   代表的な依存:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   - pip install duckdb psutil requests openai streamlit

   （本リポジトリに requirements.txt がない場合は上記を手動でインストールしてください）

3. データディレクトリの作成
   - mkdir -p data

4. 環境変数の設定
   本プロジェクトは .env / .env.local / OS 環境変数を読み込みます（自動読み込みはデフォルトで有効）。
   必須（実行する機能に応じて）:
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（research 関連）
   - KABU_API_PASSWORD — kabuステーション API 用（本番/実行）
   Optional:
   - OPENAI_API_KEY — OpenAI API キー（AI 機能）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE アラート送信用
   設定サンプル (.env):
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   OPENAI_API_KEY=...
   PAPER_FILL_MODE=instant
   LOG_LEVEL=INFO
   ```

重要な環境変数とデフォルト
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、run_execution は paper_trading 用 DB を使い MockBroker を利用
- SQLITE_PATH: 監視データ用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading のフィル（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行監視・停止フラグ関連（デフォルトは data/*.flag / data/execution.pid）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

使い方（主要スクリプト）
-----------------------

1) 監視ループを起動（Monitoring）
- python -m kabusys.run_monitoring
  - 動作:
    - Settings を読み込み（.env 等）
    - process priority を "high" に設定（可能な範囲で）
    - SQLite / DuckDB に接続して監視 DB を初期化（init_monitoring_db）
    - SystemMonitor.check_once() を定期的に実行
  - 環境変数:
    - MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（正の整数、デフォルト60）
  - 停止:
    - プロジェクトルートの data/stop_requested.flag を作成するとループが安全に終了します

2) 実行エンジンを起動（Execution）
- python -m kabusys.run_execution
  - 動作:
    - Settings を読み込み
    - Paper trading かどうかで SQLite パスを切替（paper_trading の場合は PAPER_TRADING_SQLITE_PATH）
    - BrokerClientFactory によりブローカークライアントを生成（KABUSYS_ENV=paper_trading なら Mock）
    - OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立て ExecutionEngine を開始
  - 停止:
    - data/stop_requested.flag を作ると実行エンジンに停止命令が伝搬され停止処理を行います
  - PID:
    - 実行時に data/execution.pid を書く仕様（設定で変更可能）

3) Streamlit ダッシュボード（監視可視化）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いてダッシュボード表示

4) Paper Trading 検証レポート生成ツール
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）
  - 出力: 標準出力に検証結果（稼働率・成功率・レイテンシなど）を表示

5) AI 機能（ニュースセンチメント / レジーム判定）
- kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼び出して使用
  - これらは OpenAI API キー（OPENAI_API_KEY）を要求します
  - LLM 呼び出しはリトライやフォールバックが組み込まれており、API 失敗時は安全側の動作（スコア 0 など）にフォールバックします

停止・強制停止（Kill / Stop）
- Stop (運用停止の指示): data/stop_requested.flag — run_monitoring.py / run_execution.py が検知して終了
- Kill Switch（リスク閾値で自動停止）:
  - RiskMonitor が閾値を越えた場合、KillSwitch が Settings.kill_flag_path（デフォルト data/kill.flag）に理由を書き込む
  - Execution 起動時に kill.flag が既にあれば起動を中止（設定で起動時にクリアするオプションあり）

ディレクトリ構成（主要ファイル）
-------------------------------

src/
  kabusys/
    __init__.py                 # パッケージ情報
    config.py                   # 環境設定読み込み / Settings クラス
    run_monitoring.py           # Monitoring ポーリングループ起動スクリプト
    run_execution.py            # ExecutionEngine 起動スクリプト

    ai/
      news_nlp.py               # ニュースを OpenAI に投げてスコア化
      regime_detector.py        # マクロ＋ETF ma200 で市場レジーム判定
      __init__.py

    monitoring/
      monitoring_db.py          # SQLite テーブル定義・監視ログ保存 API
      system_monitor.py         # CPU/メモリ/ディスク/process/data freshness 監視
      trade_monitor.py          # 注文滞留・約定異常検出
      risk_monitor.py           # ドローダウン・ポジション上限監視
      kill_switch.py            # kill.flag の管理
      alert_manager.py          # LINE 通知
      monitoring_engine.py      # 各 Monitor をまとめる
      streamlit_dashboard.py    # Streamlit ダッシュボード
      __init__.py

    execution/
      order_repository.py       # 注文 DB 操作（SQLite）
      order_manager.py          # 注文作成 / 同期 / キャンセル等
      reconciler.py             # 再起動時の同期処理
      execution_engine.py       # 実行セッションの制御
      broker_factory.py         # Broker クライアント生成（Mock / 実ブローカー）
      broker_api.py             # Broker API 抽象プロトコル
      order_record.py           # OrderRecord / OrderState
      risk_manager.py           # 発注リスク評価
      ...                       # （省略の追加実装ファイルが存在する想定）

    portfolio/
      portfolio_builder.py      # 候補選定 / 重み計算
      position_sizing.py        # 株数決定・スケール調整
      risk_adjustment.py        # セクターキャップ / レジーム乗数
      __init__.py

    research/
      factor_research.py        # Momentum / Volatility / Value ファクター計算
      feature_exploration.py    # 将来リターン, IC, 統計サマリー
      __init__.py

    tools/
      paper_verification_report.py  # Paper trading 検証レポート生成（CLI）
      __init__.py

    utils/
      process_priority.py       # プロセス優先度 / CPU affinity ユーティリティ
      __init__.py

data/
  monitoring.db                # 監視ログ（SQLite、実行で生成）
  paper_trading.db             # Paper trading 用 DB（paper_trading 時）
  kabusys.duckdb               # DuckDB ファイル
  execution.pid                # 実行プロセス PID（runtime）
  kill.flag / stop_requested.flag  # 停止・kill フラグ

開発・運用時の注意
------------------
- process priority の設定（高優先度）は OS 権限に依存します。Linux で負の nice 値を設定する場合は root 権限が必要なことがあります。失敗時はログに警告が出てスキップされます。
- .env の自動ロード:
  - リポジトリルート（.git または pyproject.toml を基準）を探索して .env を読み込みます。
  - OS 環境変数は .env の上書きを保護（.env.local は強制上書き可能）。
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper trading:
  - KABUSYS_ENV=paper_trading の場合、実際のブローカー API へは接続せず MockBroker を使い、記録は PAPER_TRADING_SQLITE_PATH に保存されます。本番 DB と完全分離されます。
  - PAPER_FILL_MODE を設定して約定振る舞いを制御できます（instant, partial, never, reject）。
- データ鮮度:
  - SystemMonitor は DuckDB の get_last_price_date を参照してデータ鮮度を判定（デフォルト 3 日以内許容）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等にテーブル作成を行い、既存スキーマに欠けるカラムを追加する簡易マイグレーション処理を含みます。

トラブルシューティング
---------------------
- SQLite/DuckDB ファイルが開けない:
  - パスや権限を確認してください。Streamlit からは読み取り専用で URI を指定しています（as_uri + ?mode=ro）。
- OpenAI 呼び出し失敗:
  - OPENAI_API_KEY を設定、またはネットワーク接続・API 利用制限（レート）を確認してください。LLM 呼び出しはリトライロジックと安全なフォールバックを備えています。
- LINE 通知が来ない:
  - LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID を正しく設定しているか、LINE API の利用制限を確認してください。API レスポンスの非 2xx はログに記録されます。

拡張・開発方向
----------------
- 銘柄ごとの lot_size（単元株数）を銘柄マスタに持たせる等、position_sizing の拡張
- Order 状態遷移・Closed 状態のより厳密な実装（Reconciler と ExecutionEngine の連携強化）
- more robust migration system（現在は簡易マイグレーションのみ）
- CI / テストの整備（ユニットテスト、モックでの API 呼び出し差し替え）

ライセンス / 貢献
-----------------
本 README はコードベースの説明を目的としています。実運用する場合は必ず充分なテストとリスク評価を行ってください。外部 API（kabuステーション / OpenAI / J-Quants 等）利用時の契約・利用規約を遵守してください。

---

不明点や README の追記希望（導入手順の詳細化、サンプル .env、依存関係の requirements.txt 生成など）があれば教えてください。必要に応じて実行例や運用手順をさらに詳しく追記します。