# KabuSys

日本株自動売買システムの小規模コアライブラリ（README）

本リポジトリは、取引エンジン・監視・ポートフォリオ構築・リサーチ・AI（ニュース NLP）などの主要コンポーネントを含むモジュール群です。コアは純粋な Python 実装で、DuckDB / SQLite をデータ層に利用します。

## プロジェクト概要
- 目的: 日本株向けの自動売買システムのコアロジック（シグナル生成・ポートフォリオ構築・発注管理・監視・アラート）を提供する。
- 特徴:
  - 発注エンジン（ExecutionEngine）と監視（MonitoringEngine）を分離。
  - Paper Trading（模擬発注）モードをサポートし、本番 DB と分離可能。
  - DuckDB を用いたファクター計算 / リサーチ機能。
  - OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント／レジーム判定機能（任意）。
  - 監視用 SQLite（monitoring.db）で稼働ログやリスクログを永続化。

## 主な機能一覧
- 実行（Execution）
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントファクトリ（実ブローカ or MockBroker）
  - OrderManager / OrderRepository / Reconciler / RiskManager 等
  - Paper trading 用に data/paper_trading.db を使用可能

- 監視（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス監視、データ鮮度チェック
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager（監視ループを実行）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔変更可）

- ポートフォリオ構築（Portfolio）
  - 候補選定、等重・スコア重み付け、ポジションサイズ計算、セクター制限、レジーム乗数などの純粋関数群

- リサーチ（Research）
  - ファクター計算（momentum, value, volatility）、将来リターン計算、IC 計算、統計サマリー（DuckDB 前提）

- AI（ニュース NLP / レジーム判定）
  - raw_news を LLM で評価し ai_scores に保存（score_news）
  - マクロニュース + ETF MA200 を組み合わせたレジーム判定（score_regime）
  - OpenAI API キー（OPENAI_API_KEY）を利用。API 呼び出しは堅牢なリトライやパースの保護付き

- ユーティリティ
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証ツール（validate_config.py）
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - ロギング設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度・CPU affinity ユーティリティ（utils/process_priority.py）

## セットアップ手順（ローカル開発向け）
1. Python 環境
   - 推奨: Python 3.9+（DuckDB / psutil / openai 等のサポートを踏まえて適宜調整）
2. 依存パッケージをインストール
   - 必要最低限のパッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイルの検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt を用意している場合は pip install -r requirements.txt を使用）
3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動でプロジェクトルートに .env を作成し、サンプル値を記載
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
5. データ / ログ ディレクトリの確認
   - デフォルトの DB / ログパス（.env で変更可能）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/（デフォルト）
   - 必要に応じてディレクトリを作成（スクリプト側で自動作成される場合あり）

## 環境変数（主なもの）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログファイル保存ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の fill 動作（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリア (0/1)

注意: .env に機密情報を保存する場合は Git にコミットしないでください（config_setup のヘッダでも警告があります）。

## 使い方（起動例）
- 環境を準備後、下記スクリプトで起動します。

1. 実行エンジン（ExecutionEngine）起動
   - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_sqlite_path（デフォルト data/paper_trading.db）に記録します。
     - プロセス優先度を高く設定します。
     - data/stop_requested.flag を検知すると安全に停止します。
     - 実行時の PID を data/execution.pid に出力します（Settings でパス変更可）。

2. 監視ループ（Monitoring）起動
   - python -m kabusys.run_monitoring
   - 挙動:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）。
     - 監視は常に本番 sqlite_path を使用（環境にかかわらず）。
     - data/stop_requested.flag を検知するとループを終了します。

3. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

4. 設定ウィザード / 検証
   - .env の対話式作成:
     - python -m kabusys.config_setup
   - 設定検証:
     - python -m kabusys.validate_config [--strict]

5. AI 関連（ライブラリ API）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡してニューススコアを生成（OPENAI_API_KEY を利用）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

## 停止と Kill Switch
- run_execution.py / run_monitoring.py はプロジェクトの data/stop_requested.flag（既定）を監視しています。
  - 停止させたい場合は data/stop_requested.flag を作成すると、次のポーリングで検知して停止します。
- Kill Switch:
  - KillSwitch（data/kill.flag）を監視して、危険なリスク状況発生時に ExecutionEngine を停止できます。
  - KILL_FLAG_CLEAR_ON_START=1 にすると Execution 起動時に自動的に kill.flag をクリアします（本番では 0 推奨）。

## ロギング
- ログはコンソール（stdout）とファイル（logs/<app_name>.log）に出力されます。
- ログの初期設定は kabusys.utils.logging_setup.setup_logging() が統一的に行います。
- ローテーション: 日次、30 日分保持

## ディレクトリ構成
（主要ファイルのみを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — レジーム判定
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層
    - monitoring_engine.py    — 監視ループ統合
    - system_monitor.py
    - trade_monitor.py        — （存在を前提、実装が含まれる）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py        — （存在を前提、実装が含まれる）
  - execution/
    - execution_engine.py     — ExecutionEngine（起動・セッション管理）
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時生成される可能性のあるディレクトリ（DB やフラグファイル）
  - config/                   — yaml テンプレート等（system_config.yaml 等）

（上記はリポジトリ内にあるファイル群の概観です。細部は実際の tree を参照してください。）

## 開発 / テストのヒント
- 自動 .env 読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある .env、.env.local を自動的にロードします。
  - テスト等で読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- PyYAML がない場合、validate_config の YAML 検証はスキップされます（警告）。
- OpenAI に関わる機能はネットワーク依存のため、ユニットテストでは API 呼び出し部分をモックしてください（モジュール内で _call_openai_api をパッチする設計を想定）。

## 既知の注意点 / 将来の改善ポイント（抜粋）
- position_sizing: lot_size を銘柄別に持つ拡張や、価格欠損時のフォールバックが未実装（TODO コメントあり）。
- news_nlp / regime_detector: OpenAI のレスポンスの安定性に依存するため、パースロジックやリトライは堅牢化済みだが運用での監視必要。
- Monitoring は監視 DB に書き込みを行うため、DB のバックアップ／ローテーション方針を運用で考慮すること。

---

問題や実行時のエラー、追加したいドキュメント（API リファレンスや設計資料など）があれば教えてください。必要に応じて README にコマンド例や .env.example の具体例も追記します。