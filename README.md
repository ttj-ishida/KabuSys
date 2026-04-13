README
======

概要
----
KabuSys は日本株の自動売買フレームワーク（プロトタイプ）です。価格データの解析・ファクター計算・ポートフォリオ構築・発注制御・監視・検証ツールを含むモジュール群から構成されています。設計方針は次の通りです:

- 生データやブローカー API へ安全にアクセスする（paper_trading モードで本番と分離）
- DuckDB を用いたリサーチ / ファクター計算
- SQLite を用いた監視ログ・トレードログ永続化
- LLM（OpenAI）を用いたニュースセンチメント / レジーム判定の仕組みを試験的に実装
- モジュールは純粋関数と副作用を分離し、テストしやすい形で実装

主な機能
--------
- ポートフォリオ構築
  - 候補選定、等配分／スコア加重、リスク調整（セクター上限、レジーム乗数）、株数決定（lot 単位で丸め）
- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- 実行（Execution）
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler を通した発注・再同調ロジック
  - paper_trading モードでは MockBroker を用いて data/paper_trading.db に記録し本番 DB と分離
- 監視（Monitoring）
  - SystemMonitor, TradeMonitor, RiskMonitor による定期チェック
  - MonitoringDB（SQLite）へのログ保存
  - KillSwitch（条件で ExecutionEngine 停止フラグを file へ出力）
  - LINE プッシュ通知による AlertManager
  - Streamlit ベースの監視ダッシュボード
- ツール
  - Paper Trading の検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
- AI 支援
  - ニュースセンチメント（ai.news_nlp.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）

セットアップ
----------
前提:
- Python 3.10+（型ヒントで Union shorthand を使用しているため）
- Git リポジトリルートに配置していること（.env 自動読み込みが有効な場合）

1) 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2) 必要パッケージのインストール（プロジェクトに requirements.txt がなければ下記を個別に）
   - pip install duckdb psutil requests openai streamlit

   補足:
   - sqlite3 は標準ライブラリ
   - 他にプロジェクト固有の依存があれば requirements.txt を作成して管理してください

3) 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（OS 環境変数が優先）
   - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
  - paper_trading の場合は MockBroker を使用し PAPER_TRADING_SQLITE_PATH に記録
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な場合あり）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須な場合あり）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（ai モジュールを使用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject）
- PID_FILE_PATH, KILL_FLAG_PATH, その他しきい値系（CPU/MEM/DISK etc.）

使い方
------

基本的な実行例
- ExecutionEngine を起動（環境に応じて .env を整備）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB に書き込みます

- SystemMonitor のポーリングを起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60）
  - python -m kabusys.run_monitoring

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - または起動スクリプトから DB パスを CLI で指定

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

AI / LLM 関連
- ai.news_nlp.score_news / ai.regime_detector.score_regime は OpenAI API キー（OPENAI_API_KEY または引数）を必要とします。
- API 呼び出しはリトライ・バックオフ・結果検証等の安全処理を組み込んでいますが、利用時は API 使用量に注意してください。

モードの違い（本番 / paper_trading）
- KABUSYS_ENV=paper_trading の場合、発注はモック実装を使い paper_trading 用 SQLite に記録され、本番 DB とは完全に分離されます。
- 監視（monitoring）は KABUSYS_ENV にかかわらずデフォルトの monitoring.sqlite_path を使用する実装になっています（コード参照）。

監視・停止フロー
- SystemMonitor / TradeMonitor / RiskMonitor が定期的にチェックして MonitoringDB にログを書きます。
- KillSwitch は条件（ドローダウン超過など）で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。
- ExecutionEngine 側は起動時に kill.flag をクリアするオプション（Settings.kill_flag_clear_on_start）を持つことが想定されています。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                     # 環境変数 / .env 読み込みロジックと Settings
    run_execution.py              # ExecutionEngine 起動スクリプト
    run_monitoring.py             # SystemMonitor ポーリング起動スクリプト

    ai/
      __init__.py
      news_nlp.py                 # ニュースセンチメント（OpenAI）と ai_scores 書込み
      regime_detector.py         # マクロ + ETF MA によるレジーム判定

    monitoring/
      __init__.py
      monitoring_db.py            # SQLite スキーマ定義 / 永続層
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py

    execution/
      reconciler.py
      order_manager.py
      order_repository.py         # （コードベースで参照されるが抜粋にあり）
      execution_engine.py        # （抜粋内に存在する想定）
      broker_factory.py          # BrokerClientFactory（paper/live の切替）
      broker_api.py              # ブローカー API インターフェース定義

    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      __init__.py
      factor_research.py
      feature_exploration.py

    tools/
      __init__.py
      paper_verification_report.py

    utils/
      __init__.py
      process_priority.py         # プロセス優先度 / CPU affinity ユーティリティ

data/
  (接続先ファイル — デフォルト)
  kabusys.duckdb
  monitoring.db
  paper_trading.db

補足 / 実運用時の注意
--------------------
- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env/.env.local を自動で読み込みます。
  - OS 環境変数を保護しつつ .env.local が .env を上書きします。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成と簡単なマイグレーション（カラム追加）を行いますが、本格的なマイグレーション管理は別途必要です。

- OpenAI / 外部 API:
  - API キーや使用料、レート制限に注意してください。AI モジュールはエラー時にフェイルセーフにフォールバックする実装を意図していますが、実運用のポリシーは必須です。

- 権限:
  - process priority / CPU affinity の設定は OS と実行ユーザーの権限に依存します。必要に応じて適切な権限で起動してください。

開発
----
- テスト可能な純粋関数（portfolio や research モジュール等）が多く、ユニットテストの追加が容易です。
- OpenAI 呼び出しは内部でラップしているため、ユニットテストでは _call_openai_api のモック差し替えが可能です。
- run_monitoring / run_execution の main 関数は __main__ として直接起動可能（python -m kabusys.run_monitoring など）。

ライセンス / 著作権
------------------
（ここにプロジェクト固有のライセンス表記を記載してください）

最後に
------
この README はコードベースの主要なコンポーネントと基本的な使い方を説明するための要約です。詳細実装や追加設定は各モジュールの docstring やソースコードコメントを参照してください。質問や追加のドキュメントが必要であれば教えてください。