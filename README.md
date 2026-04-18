README
======

概要
----
KabuSys は日本株向けの自動売買・調査プラットフォームの一部です。本リポジトリは以下の主要機能を備えたライブラリ／実行スクリプト群を提供します。

- 発注エンジン（ExecutionEngine）起動スクリプト
- 監視（Monitoring）ループ（システム／注文／リスク監視）
- ペーパートレードの検証レポート生成ツール
- ポートフォリオ構築、ポジションサイジング、リスク調整の純粋関数群
- ファクター計算・リサーチユーティリティ
- ニュースの NLP（OpenAI）によるセンチメントスコアリング
- 環境変数ウィザードおよび設定検証ツール

設計上の方針のポイント
- 本番・ペーパートレードは DB を分離（paper_trading モード用 DB を用意）
- ルックアヘッドバイアス排除（日時参照の扱いに注意）
- 外部 API 呼び出し（OpenAI 等）は明示的にキーを渡す or 環境変数を使用
- フェイルセーフ：API 失敗時は極端な例外をあげずフォールバックする実装が多い

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動（本番 / ペーパー）: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI: ニュースセンチメント（kabusys.ai.score_news）、レジーム判定（kabusys.ai.regime_detector）
- Research: ファクター計算（calc_momentum / calc_volatility / calc_value）、将来リターン・IC 等
- Portfolio: 候補選定、重み算出、ポジションサイズ算出、セクター制約、レジーム乗数
- Monitoring internals: system / trade / risk monitor、kill switch、アラート連携（AlertManager 経由）

セットアップ手順
----------------
前提: Python 3.9+（typing、psutil、duckdb、openai 等が使われています）

1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai
   - 任意: PyYAML（config 検証で YAML の内容チェックが有効になります）:
     pip install pyyaml

   （プロジェクトに requirements.txt がある場合はそれを使用してください）

3. .env を作成（ウィザード推奨）
   - python -m kabusys.config_setup
     → 対話形式で .env を生成します（.env は絶対コミットしないでください）

4. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば出力に従って修正します
   - --strict を付けると警告も失敗扱いになります

5. data ディレクトリやデフォルト DB の配置
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視用): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
   - 初回は空ファイルを作るだけでも起動できます。スクリプトが必要なテーブルを初期化します。

主要環境変数（抜粋）
-------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 実行環境:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DB パス:
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB）
- OpenAI:
  - OPENAI_API_KEY（ai モジュール使用時）
- Monitoring:
  - MONITOR_POLL_INTERVAL（秒。run_monitoring のポーリング間隔、デフォルト 60）
- Paper:
  - PAPER_FILL_MODE（instant|partial|never|reject、デフォルト: instant）
- その他:
  - LOG_LEVEL（DEBUG/INFO/...）
  - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか。デフォルト 0）

使い方
------

CLI（プロセス起動 / ツール）
- 環境ウィザード
  - python -m kabusys.config_setup
    ・.env の作成・更新を対話形式で行う

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine を起動（本番/ペーパーいずれも）
  - python -m kabusys.run_execution
    ・KABUSYS_ENV が paper_trading の場合は MockBroker を使用し、paper_trading DB（PAPER_TRADING_SQLITE_PATH）に記録します
    ・実行中は data/execution.pid に PID を書きます
    ・停止フラグ: data/stop_requested.flag を作ると安全に停止します
    ・Kill switch 用フラグ: data/kill.flag（KillSwitch が書き込む）

- Monitoring を起動
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    ・監視ループのポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可（秒、デフォルト 60）
    ・監視は monitoring DB（settings.sqlite_path）へ記録します（本番 DB のパスを参照）
    ・停止フラグ: data/stop_requested.flag を置くとループが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 簡易チェック（稼働率・注文成功率・送信率・P95 レイテンシ等）を出力します

プログラム API（ライブラリの一部使用例）
- ポートフォリオ関連関数（純粋関数なのでテストしやすい）
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
  - candidates = select_candidates(buy_signals, max_positions=10)
  - weights = calc_score_weights(candidates)
  - sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)

- リサーチ（DuckDB 接続を渡して使用）
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - records = calc_momentum(conn, date(2026,4,1))

- AI（ニューススコアリング）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="sk-...")  # api_key を渡すか OPENAI_API_KEY を環境変数でセット

注意点
- .env は機密情報を含むため絶対に Git にコミットしないでください
- openai ライブラリのバージョンが変わると呼び出し方法や例外クラスが変わる可能性があります。テスト／モックを用意してください（実装内で API 呼び出し関数を差し替えやすく設計されています）
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します（誤って Kill Switch を自動クリアすると危険）

停止・Kill Switch
- ExecutionEngine 停止は data/stop_requested.flag を作成するか、KillSwitch が必要条件を満たすと data/kill.flag を書き込みます
- KillSwitch はリスク閾値（ドローダウン、ポジション上限など）に従ってフラグを書きます
- 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（開発用／本番では推奨しない）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み・Settings
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py                — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py         — 市場レジーム判定（AI + ma200）
  - monitoring/
    - monitoring_db.py          — SQLite テーブル初期化・CRUD ラッパ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py          — （アラート配信は AlertManager 経由）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度設定ユーティリティ
  - (その他) execution/, data/ 等のサブパッケージ（発注ロジックやデータパイプライン）

各ファイルの簡単な役割
- config.py: 自動的にプロジェクトルートの .env / .env.local をロードし Settings を提供
- config_setup.py: .env を対話的に作成・更新
- validate_config.py: 環境変数と config/*.yaml の基本チェックを実行
- run_execution.py: ExecutionEngine を組み立てて起動（paper_trading モードでは MockBroker を使用）
- run_monitoring.py: SystemMonitor をポーリングして monitoring DB に記録
- monitoring/*: 監視ロジック（システム・注文・リスク監視）と KillSwitch / AlertManager
- portfolio/*: 候補選定・重み付け・ポジションサイズ計算、セクター制限やレジーム乗数
- research/*: DuckDB を使ったファクター計算・統計分析
- ai/*: OpenAI を用いたニューススコアリング・レジーム検出
- tools/paper_verification_report.py: ペーパートレード DB を解析してパフォーマンス判定を行う CLI

トラブルシューティング
---------------------
- .env が正しくロードされない:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していると自動ロードはスキップされます
  - config_setup で .env を作成し、validate_config で検証してください

- Execution/Monitoring がすぐ終了する:
  - data/stop_requested.flag が存在していないか確認してください
  - PID ファイル（data/execution.pid）が stale でないか確認してください

- OpenAI まわりのエラー:
  - OPENAI_API_KEY を設定するか、score_news / score_regime に api_key を明示的に渡してください
  - Rate limit・ネットワーク断は内部でリトライしますが、限度を超えると処理がスキップされます

開発者向けメモ
--------------
- 多くのモジュールは副作用を避ける純粋関数（portfolio, research 等）と、DB / IO を扱うクラスに分離されています。単体テストや差し替え（モック）を行いやすく設計されています。
- OpenAI 呼び出し部はテストのために差し替え可能にしてある（internal helper を patch するとよい）。

ライセンス / バージョン
----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）

以上がこのコードベースの概要と主要な使い方です。必要であれば、README に含める具体的なコマンド例、環境変数テンプレート（.env.example）の生成方法、あるいは追加のディレクトリツリー（より詳細）を出力します。どの情報を拡張しましょうか？