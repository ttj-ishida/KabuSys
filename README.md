# KabuSys

日本株自動売買システムのモジュール群（ライブラリ / 実行スクリプト / 監視 / リサーチ / AI補助機能）。  
この README はリポジトリ内の主要コンポーネントと基本的な使い方、セットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株自動売買のための以下の機能群を提供します。

- 発注・注文管理（ExecutionEngine, OrderManager, Broker クライアント）
- リコンシリエーション（再起動後の同期）
- 監視（System / Trade / Risk のポーリング、監視ログの永続化）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ算出、セクター制限）
- リサーチ（ファクター計算、将来リターン・IC 計算、特徴量探索）
- AI を用いたニュースセンチメント（OpenAI によるニューススコアリング、レジーム判定）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

設計方針として、データベースは SQLite / DuckDB を使用し、外部 API 呼び出しやプロダクション資産への影響を最小にするように分離されています（例えば paper_trading 環境は本番 DB と完全分離）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動スクリプト（src/kabusys/run_execution.py）
  - 発注状態管理、リスク管理、リコンシリエーション
  - `KABUSYS_ENV=paper_trading` 時は MockBroker を使用し、paper 専用 DB に記録
- Monitoring
  - System / Trade / Risk 各種モニタ（src/kabusys/monitoring/*.py）
  - MonitoringEngine（間隔ポーリング、KillSwitch、LINE 通知）
  - SQLite に監視ログ保存（monitoring_db）
  - Streamlit ダッシュボード（src/kabusys/monitoring/streamlit_dashboard.py）
- Portfolio
  - 候補選定・重み計算（等金額 / スコア加重）
  - セクター制限、レジーム乗数、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - forward returns / IC 計算 / 統計サマリー
- AI
  - ニュース NLP（OpenAI を用いた銘柄別センチメントの算出）
  - レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- Tools
  - Paper Trading 検証レポート生成スクリプト
  - 監視ダッシュボード (Streamlit)

---

## 必要条件（概略）

- Python 3.9+
- SQLite（標準モジュール）
- 主要 Python パッケージ:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード使用時)
- ネットワークアクセス（LINE / OpenAI を使う場合）

（プロジェクトに requirements.txt がない場合は上記を pip でインストールしてください）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. data ディレクトリを作成（スクリプトが自動作成する場合もありますが事前準備推奨）
   ```
   mkdir -p data
   ```
5. 環境変数を設定（.env / .env.local を作成するか環境に直接設定）
   - 主要な環境変数（抜粋）:
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 使用時）
     - KABUSYS_ENV: environment (development | paper_trading | live). デフォルトは development
     - PAPER_FILL_MODE: paper_trading の fill モード（instant | partial | never | reject）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: Monitoring SQLite（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, LOG_LEVEL など

   config.py は .env と .env.local を自動ロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化できます）。

6. 必要に応じてデータベースを準備（初回はスクリプトがテーブルを作成します）
   - monitoring 用テーブルは run_monitoring や init_monitoring_db を通じて自動作成されます。

---

## 使い方（起動例）

- 監視ループを起動（ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60）
  - run_monitoring は常に本番用 sqlite_path（Settings.sqlite_path）を使用して monitoring テーブルを初期化します
  - 停止方法:
    - CTRL+C（KeyboardInterrupt）
    - プロジェクトルート/data/stop_requested.flag を作成すると次のポーリングでループが終了します

- ExecutionEngine を起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、paper DB（PAPER_TRADING_SQLITE_PATH）へ記録します。live を使う場合は実ブローカー設定が必要です。
  - 実行中に data/stop_requested.flag を作成するとエンジン停止シグナルを送り安全に終了します。
  - run_execution は起動時に monitoring DB の監視テーブルが存在することを保証（冪等的に作成）します。

- Streamlit ダッシュボード（監視 UI）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - データベースを読み取り専用で開くため、MonitoringEngine を先に起動してデータが存在することを確認してください。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で指定可能）
  - 成績指標（稼働率、注文成功率、レイテンシなど）をコンソール出力します。

- AI 機能（Python API）
  - ニューススコアリング:
    ```py
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - レジーム判定:
    ```py
    from datetime import date
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```
  - どちらも OPENAI_API_KEY を環境変数で設定しておくか api_key 引数で渡してください。

---

## 制御ファイル（フラグ・PID）

- data/stop_requested.flag
  - run_monitoring / run_execution が監視している停止フラグ。存在するとループを終了します。
- data/kill.flag
  - KillSwitch（RiskMonitor により評価） が書き込むファイル。ExecutionEngine に停止シグナルを送るために使用されます。KillSwitch は条件を満たすと kill.flag を作成します。
- data/execution.pid
  - ExecutionEngine の PID を保存するファイルとして参照されます。SystemMonitor はこの PID ファイルの存在・生存を確認してプロセス状態を判定します。

---

## 環境変数一覧（主要なもの）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能用）
- LINE_CHANNEL_ACCESS_TOKEN: LINE 通知用トークン
- LINE_USER_ID: LINE 通知先ユーザー
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: Monitoring SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文約定挙動）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, LOG_LEVEL
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視しきい値）

config.py に詳しい説明とデフォルト値が記載されています。

---

## 注意事項 / 運用上のメモ

- config.py は実行時にプロジェクトルートの .env / .env.local を自動ロードします（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。プロジェクトルートは .git または pyproject.toml を基準に探索します。
- Monitoring の DB（monitoring.db）は run_monitoring が使用する主な永続化領域です。init_monitoring_db によりテーブルは自動作成・マイグレーションされます。
- run_execution は paper_trading 環境時に paper DB を使用して本番 DB と分離します。実際のブローカーを使う場合は broker の設定と認証情報に注意してください。
- OpenAI を使用するモジュールは API 呼び出しのリトライ、JSON 検証、フェイルセーフ (失敗時は中立値で継続) を備えていますが、API 使用量には注意してください。
- process priority / cpu affinity の設定には psutil が必要です。権限や OS により設定できない場合は警告が出てスキップされます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (実装ファイルが存在する想定)
    - broker_factory.py, broker_api.py, ...（ブローカー関連）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/  (実行時に使用するファイル群)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb

（上記はリポジトリ内ファイルの抜粋。完全な一覧はリポジトリツリーを参照してください）

---

## 開発・テスト上のヒント

- モジュールは多くが外部システム（DB / Broker / OpenAI）に依存します。ユニットテストでは依存箇所をモックする設計になっています（例: news_nlp の _call_openai_api をパッチ）。
- .env.example を用意して必要な環境変数のテンプレートを管理してください（プロジェクトの秘密情報は .env.local に置き、.gitignore に追加することを推奨します）。
- monitoring の複数機能（LINE 通知、KillSwitch）は運用ルールに合わせてしきい値やクールダウン時間を調整してください。

---

以上がこのコードベースの概要と基本的な使い方です。  
必要に応じて README を拡張して、運用手順（systemd / Docker / supervisor のサービス定義）、CI / テスト方法、API ドキュメントなどを追加してください。