README
=====

概要
----
KabuSys は日本株の自動売買システム用ライブラリ／ツール群です。本リポジトリには以下の主要機能を持つモジュール群が含まれています。

- 注文管理・実行エンジンの起動スクリプト（ExecutionEngine 起動）
- 監視（System / Trade / Risk）およびアラート送信機能（LINE）
- Paper Trading 向けの検証ツール（レポート生成）
- Portfolio 構築・配分・ポジションサイズ計算ロジック（純粋関数）
- リサーチ用ファクター計算・特徴量探索（DuckDB を使用）
- ニュース文章を用いた LLM によるセンチメントスコア生成・レジーム判定（OpenAI）
- Streamlit ベースの監視ダッシュボード
- SQLite / DuckDB を利用したデータ永続化・集計層

設計方針のポイント
- DuckDB を使って履歴データ（prices_daily / raw_financials 等）を SQL ベースで処理する
- 主要ロジックは可能な限り純粋関数（副作用なし）に分離してユニットテストしやすくする
- 実行時の環境切替（development / paper_trading / live）は Settings による環境変数で制御
- Paper Trading は本番 DB と分離して data/paper_trading.db に記録（KABUSYS_ENV=paper_trading）

主な機能一覧
- run_monitoring.py: SystemMonitor をポーリングして system_status / risk_logs / trade_logs / dashboard を更新
- run_execution.py: ExecutionEngine を起動（paper_trading 時は MockBroker を使用）
- monitoring:
  - SystemMonitor: CPU / メモリ / ディスク・Execution プロセス PID・データ鮮度を監視
  - TradeMonitor: 滞留注文・約定価格異常を検出
  - RiskMonitor: ドローダウン・ポジション上限などを監視してリスクイベントを記録
  - KillSwitch: 指定ファイル (kill.flag) を書き込むことで ExecutionEngine 停止シグナルを送信
  - AlertManager: LINE Messaging API で一方向通知（クールダウン管理あり）
  - streamlit_dashboard: 監視 DB を可視化する簡易ダッシュボード
- portfolio: 候補選定 / 重み計算 / セクターキャップ / レジーム乗数 / 株数決定（単元丸め・集計キャップ）
- research: ファクター計算（Momentum / Volatility / Value）と特徴量解析（forward returns / IC / summary）
- ai:
  - news_nlp: raw_news を集約して OpenAI に送信、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector: MA200 乖離とマクロニュースセンチメントを合成して market_regime を記録
- tools:
  - paper_verification_report: Paper Trading の検証レポートを生成して標準出力に表示

セットアップ手順
----------------
前提
- Python 3.10 以上（型注釈で | を使用しているため）
- Git, SQLite（OS 標準で可）

手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil openai requests streamlit
   - （requirements.txt がある場合は pip install -r requirements.txt）
4. データディレクトリ作成（必要に応じて）
   - mkdir -p data
5. 環境変数設定
   - プロジェクトルートに .env を作成（.env.example を参照）
   - 自動ロード機能: config モジュールはプロジェクトルートから .env, .env.local を自動で読み込みます（OS 環境変数優先）。無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
6. 必須環境変数（主なもの）
   - JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI を利用する機能（ai.news_nlp / ai.regime_detector）を使う場合は必須
   - KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
   - その他（省略可 / デフォルトあり）:
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - PID_FILE_PATH (default: data/execution.pid)
     - KILL_FLAG_PATH (default: data/kill.flag)
     - PAPER_FILL_MODE (instant|partial|never|reject) — paper_trading の約定挙動（default: instant）
     - LOG_LEVEL, CPU/MEMORY/DISK 閾値 等（Settings 参照）
7. 初期 DB 作成は各起動スクリプトが自動で init_monitoring_db を呼びます（手動で実行する必要はありません）。

使い方（主要コマンド）
--------------------

1) 監視ループを起動（Production/Dev 共通）
- 実行:
  - python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
- 動作:
  - プロセス優先度を "high" に設定（権限不足時はスキップ）
  - monitoring DB（sqlite）と DuckDB に接続し SystemMonitor をポーリング
  - system_status / risk_logs / trade_logs / dashboard を更新

2) ExecutionEngine を起動（本番または Paper Trading）
- 実行:
  - python -m kabusys.run_execution
- 環境:
  - KABUSYS_ENV=paper_trading を設定すると Paper Trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH、default: data/paper_trading.db）に書き込み、MockBrokerClient を使用します。本番環境は settings.sqlite_path を使用します。
- 動作:
  - ブローカークライアント生成 → OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて engine.run_session() を呼びます
  - 起動時に Reconciler による自動復旧（OrderSent の照合等）が行われます

3) Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で PAPER_TRADING_SQLITE_PATH より優先して DB を指定可能
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を判定して PASS/FAIL を表示します

4) Streamlit ダッシュボード（監視）
- 実行:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視用 SQLite を読み取り専用で開き、概要 / 保有ポジション / 最近の注文 / システムステータス を表示します

5) AI 関連（ニュース NLP / レジーム判定）
- 必須:
  - OPENAI_API_KEY が必要（引数で渡す API キーを受け取る関数もあります）
- 注意:
  - 呼び出し先は OpenAI の gpt-4o-mini を想定しており、API 呼び出しはバッチ + リトライを行います
  - スコアは ±1 にクリップされ、失敗時はフェイルセーフ（スキップや 0.0 フォールバック）を行います

設定（Settings / 環境変数）
-------------------------
主要な設定項目（デフォルト値 / 備考）:
- KABUSYS_ENV: development | paper_trading | live（default: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabu API（必須）
- OPENAI_API_KEY: OpenAI API（ai を使うなら必須）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: instant | partial | never | reject（default: instant）
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: .env 自動ロードを無効化

ディレクトリ構成（抜粋）
----------------------
以下は本コードベースに含まれる主要ファイル／モジュールの構成（src/kabusys 以下）。実際のツリーは若干の追加ファイルがある場合があります。

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / .env ロード / Settings
    - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py
    - monitoring/
      - __init__.py
      - monitoring_db.py         — SQLite テーブル定義 / 永続化 API
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
      - (その他: broker_factory, execution_engine, order_repository などを参照するモジュール)
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - utils/
      - __init__.py
      - process_priority.py

補足 / 運用上の注意
------------------
- init_monitoring_db は冪等でテーブル作成と簡単なマイグレーション（カラム追加）を行います。起動スクリプトが自動的に呼び出します。
- run_execution/run_monitoring は起動時にプロセス優先度の変更を試みます（psutil を利用）。権限が無い場合は警告ログを出してスキップします。
- kill.flag を用いた KillSwitch はファイル存在により ExecutionEngine 停止を要求します。Execution 起動時に KILL_FLAG_CLEAR_ON_START 設定があると自動クリアできます。
- OpenAI を利用する処理は API 呼び出しに失敗した場合でもシステム全体が停止しないよう設計されていますが、API 使用料が発生する点に注意してください。
- Paper Trading を行う際は KABUSYS_ENV=paper_trading を設定して専用 DB に分離してください。

ライセンス / 貢献
-----------------
リポジトリに含まれる LICENSE ファイルを参照してください。バグ修正や機能追加は fork → PR をください。

以上。必要であれば README に実行例のスクリーンショットやより詳細な設定例（.env.example のサンプル）を追記します。どの情報を追加したいか教えてください。