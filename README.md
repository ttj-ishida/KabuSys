# KabuSys

日本株自動売買システム「KabuSys」のリポジトリ向け README（日本語）

---

目次
- プロジェクト概要
- 主な機能
- 必須／推奨環境変数
- セットアップ手順
- 使い方（起動スクリプト、ツール、検証）
- ログ・データ／フラグファイルについて
- ディレクトリ構成（抜粋）

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ用ライブラリ兼実行環境です。  
主なコンポーネントは以下です。

- ExecutionEngine: 発注・注文管理・リスク管理を行う実行エンジン
- Monitoring: システム稼働状態・注文状態・リスク監視、および Kill Switch（停止信号）設計
- Research: DuckDB 上の時系列データからファクター計算・特徴量解析
- AI モジュール: ニュースのセンチメント解析や市場レジーム判定（OpenAI を利用）
- ユーティリティ: 設定ウィザード、設定検証、ログ設定など

設計方針として「本番 DB とペーパートレードを分離」「ルックアヘッドバイアスを避ける」「API失敗時はフェイルセーフで継続」などが盛り込まれています。

---

## 主な機能一覧

- Execution
  - 本番 / ペーパートレード切替（KABUSYS_ENV により切替）
  - ブローカークライアントの抽象化（Mock を含む）
  - 注文管理・リスク管理・リコンサイル機能
- Monitoring
  - CPU/メモリ/ディスク監視、プロセス生存確認、データ鮮度監視
  - 取引ログ / リスクログ / ダッシュボードの永続化（SQLite）
  - Kill Switch による安全停止（フラグファイル）
  - アラート送信フック（LINE 等のトークンを利用可能）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）などの統計解析
- AI
  - ニュースの銘柄別センチメント（OpenAI 使用）
  - マクロニュースと ETF MA に基づく市場レジーム判定
- ツール
  - 環境設定ウィザード（.env の対話式生成）
  - 設定検証 CLI（必須環境変数・config/*.yaml のチェック）
  - Paper Trading の検証レポート生成

---

## 必須／推奨環境変数（抜粋）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な環境変数（デフォルトありを含む）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: AI 機能を使う場合に必須
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1、本番は 0 推奨）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）

.env 自動ロード:
- リポジトリルート（.git または pyproject.toml を基準）に `.env` / `.env.local` があれば自動読み込みされます。
- 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（開発向け）

1. リポジトリをクローン
   - git clone ... && cd ...

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合: pip install -r requirements.txt  
     （このコードベースでは duckdb, psutil, openai, PyYAML 等を使用しています）
   - 開発インストール: python -m pip install -e .

4. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

6. データディレクトリ作成（必要に応じて）
   - デフォルト DB / logs ディレクトリが存在しない場合、自動作成されますが事前に作るとパーミッションの問題を防げます

---

## 使い方（起動例）

基本的にはパッケージのモジュールとして実行します。

- ExecutionEngine（取引エンジン）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db に記録します（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すれば起動を中止します。
    - 実行中は data/execution.pid が使われます（pid ファイルパスは Settings.pid_file_path で変更可能）。

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔秒をオーバーライド可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を常に参照します（run_monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します）。
  - 停止は data/stop_requested.flag を作成することで行えます（監視プロセスが検知して終了）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY が必要です（関数はプログラムから呼び出す形式）。
  - 例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を呼ぶ場合に API キーを渡すか環境変数を設定してください。

---

## ログ・DB・フラグファイルについて

- ログ
  - デフォルト出力先: logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - ローテーション: 日次（TimedRotatingFileHandler）、30 日分保持
  - コンソール出力は stdout に出力されます

- データベース
  - DuckDB: デフォルト data/kabusys.duckdb（解析・リサーチ用）
  - SQLite（監視）: デフォルト data/monitoring.db
  - Paper trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

- フラグ / PID ファイル
  - data/stop_requested.flag: launch スクリプト（run_execution/run_monitoring）がループの停止に使用
  - data/kill.flag: Kill Switch が書き込む停止フラグ（ExecutionEngine 側で検出し停止）
  - data/execution.pid: 実行エンジンの PID ファイル（Settings.pid_file_path）

---

## 主要なモジュールと責務（抜粋）

- kabusys.config
  - 環境変数の読み込み・検証・Settings クラスを提供
  - 自動で .env / .env.local をロード（無効化可能）

- kabusys.run_execution
  - ExecutionEngine の起動スクリプト
  - paper_trading 時は専用 DB を使用

- kabusys.run_monitoring
  - SystemMonitor のポーリングループ起動スクリプト
  - MONITOR_POLL_INTERVAL で間隔変更可

- kabusys.monitoring.*
  - monitoring_db: SQLite スキーマ初期化・永続化 API
  - system_monitor / trade_monitor / risk_monitor: 各種チェック
  - kill_switch: フラグファイルによる停止ロジック
  - monitoring_engine: 各 Monitor を束ねて実行

- kabusys.execution.*
  - ExecutionEngine, OrderManager, RiskManager 等（発注・リスク制御）

- kabusys.portfolio.*
  - 銘柄選定、重み計算、ポジションサイズ計算、セクター制約、レジーム乗数等（純粋関数）

- kabusys.research.*
  - ファクター計算（momentum/volatility/value）、特徴量探索、IC 計算

- kabusys.ai.*
  - news_nlp: ニュースセンチメント（OpenAI 依存）
  - regime_detector: 市場レジーム判定（OpenAI + ETF MA）

---

## よくある運用注意点

- 本番環境（KABUSYS_ENV=live）では .env の値・LINE 通知などに特に注意してください（validate_config は live で追加警告を出します）。
- run_monitoring は監視用 DB（SQLite）を常に本番 sqlite_path で開きます。環境にかかわらず監視ログを集めたい意図のためです。
- ペーパートレードは本番データベースと完全に分離されています（paper_trading 用 SQLite を使用）。
- AI モジュールを使う場合、API 呼び出しは外部コスト・レイテンシが発生します。API キーは安全に管理してください。
- kill.flag / stop_requested.flag の存在チェックや自動クリア設定（KILL_FLAG_CLEAR_ON_START）は運用上重要です。特に本番では自動クリアを無効化することを推奨します。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py
- config_setup.py
- validate_config.py
- run_execution.py
- run_monitoring.py

src/kabusys/execution/
- execution_engine.py
- order_manager.py
- order_repository.py
- reconciler.py
- risk_manager.py
- broker_factory.py

src/kabusys/monitoring/
- monitoring_db.py
- system_monitor.py
- trade_monitor.py
- risk_monitor.py
- kill_switch.py
- monitoring_engine.py
- alert_manager.py

src/kabusys/portfolio/
- portfolio_builder.py
- position_sizing.py
- risk_adjustment.py

src/kabusys/research/
- factor_research.py
- feature_exploration.py

src/kabusys/ai/
- news_nlp.py
- regime_detector.py

src/kabusys/utils/
- logging_setup.py
- process_priority.py

src/kabusys/tools/
- paper_verification_report.py

その他:
- data/         （デフォルトの DB / フラグ / pid 等）
- logs/         （ログファイル）

---

README は以上です。運用や導入でさらに詳しい内容（ExecutionEngine の設定項目、ブローカー実装、strategy の追加方法など）が必要であれば、その点について別途ドキュメントを作成します。どの部分を詳細化したいか教えてください。