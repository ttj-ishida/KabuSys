# KabuSys

日本株自動売買システムのモジュール群（ライブラリ / 起動スクリプト / ツール群）

## プロジェクト概要

KabuSys は日本株向けの自動売買システムコンポーネント群です。本リポジトリは以下の主要機能を含みます。

- ExecutionEngine（発注エンジン）と Broker クライアントの組み立て・起動処理
- 監視（Monitoring）コンポーネント（システム・注文・リスク監視、Kill Switch）
- ポートフォリオ構築 / ポジションサイズ算出等の純粋関数ライブラリ
- リサーチ（ファクター計算、特徴量解析）
- AI モジュール（OpenAI を利用したニュースセンチメント評価、レジーム判定）
- 管理用 CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポートなど）

設計上の特徴：
- 環境変数 / .env による設定管理（自動読み込み機構あり）
- DuckDB（分析用）・SQLite（監視 / 発注ログ）を併用
- Paper Trading と Live を分離（paper_trading 時は MockBrokerClient を利用し別 DB を使用）
- OpenAI を利用する機能は API キーを環境変数で指定可能（フェイルセーフあり）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて paper_trading と live を切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（監視ログの永続化）
- 設定管理 / ツール
  - config_setup.py: .env 対話式ウィザード（初期作成 / 更新）
  - validate_config.py: .env および config/*.yaml の妥当性検証 CLI
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成
- モニタリング関連
  - monitoring_db.py: SQLite の監視テーブル初期化および永続化 API
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック
  - monitoring_engine.py: 複数モニタを束ねたポーリング実行
  - kill_switch.py: kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る
- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定・重み計算
  - portfolio/position_sizing.py: 発注株数決定ロジック（丸め・上限・集約キャップ）
  - portfolio/risk_adjustment.py: セクター上限・レジーム乗数
- リサーチ / AI
  - research/*.py: ファクター計算、将来リターン、IC 計算など
  - ai/news_nlp.py: OpenAI を使ったニュースセンチメント評価（ai_scores へ書込）
  - ai/regime_detector.py: MA とマクロ ニュースを組合せた市場レジーム判定

---

## セットアップ手順

推奨: Python 3.9+（ソース中の型ヒント等を想定）。仮想環境での利用を推奨します。

1. リポジトリをクローン / 配布物を配置
2. 仮想環境作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無ければ代表的な依存をインストール:
     - pip install psutil duckdb openai
   - （任意）YAML 検証に PyYAML を使用:
     - pip install pyyaml
4. .env の準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または .env を手動作成（ルートに配置）。主な環境変数とデフォルト:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — デフォルト: data/paper_trading.db
     - LOG_LEVEL — デフォルト: INFO
     - OPENAI_API_KEY — AI 機能使用時
     - PAPER_FILL_MODE — paper_trading の fill モード（instant|partial|never|reject）
     - KILL_FLAG_CLEAR_ON_START — 起動時に Kill Flag を自動クリアするか（0/1）
   - .env の自動読み込み:
     - デフォルトでプロジェクトルートの .env および .env.local を自動読み込みします。
     - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
5. ログディレクトリの作成（任意）
   - デフォルトは logs/
   - LOG_DIR 環境変数で変更可能

---

## 使い方

基本的な操作コマンド例（プロジェクトルートで実行）:

- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告を FAIL とみなす）:
    - python -m kabusys.validate_config --strict
- ExecutionEngine の起動
  - python -m kabusys.run_execution
  - 動作モード:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用しデータは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。live では本番 DB を使用します。
  - 停止方法:
    - data/stop_requested.flag を作成すると実行中の engine は停止を検知して終了します。
  - 実行中は data/execution.pid に PID が書き込まれます。
- Monitoring の起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔の変更:
    - 環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
    - 無効な値（0, 負数, 数字以外）はデフォルトにフォールバック
  - 停止:
    - data/stop_requested.flag を作成すると監視ループが終了します
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH より優先）

主要な挙動メモ:
- run_execution は起動時に KILL フラグ（kill.flag）の自動クリア（KILL_FLAG_CLEAR_ON_START=1）の有無を設定できます。production では 0 を推奨。
- Monitoring は監視結果を SQLITE_PATH（data/monitoring.db）に保存します（init_monitoring_db によりテーブルは冪等で作成されます）。
- AI 機能（news_nlp, regime_detector）は OpenAI API を利用します。利用時は OPENAI_API_KEY を設定してください。API 失敗時はフェイルセーフ（スコア 0 等）で継続する実装になっています。

---

## 主要設定（環境変数）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- OPENAI_API_KEY: OpenAI を使用する機能で必要
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 時の模擬約定挙動）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（0/1）

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/            # ExecutionEngine 系（発注ロジック、BrokerFactory など）
      - ... (order_manager, order_repository, reconciler, risk_manager 等)
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - data/                 # 実行時に利用するデータファイルを置く（例: data/*.db, flags）

ログはデフォルトで logs/ に出力され、アプリ名毎に daily ローテーションされます（例: logs/execution.log, logs/monitoring.log）。

---

## 運用上の注意 / ベストプラクティス

- production（KABUSYS_ENV=live）では kill.flag の自動クリアを無効（KILL_FLAG_CLEAR_ON_START=0）にすることを推奨します。
- paper_trading は本番 DB と分離されます。テスト時は PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI を利用する機能は API 利用料が発生します。API キーの管理に注意してください。
- .env は絶対にバージョン管理（Git）にコミットしないでください。
- validate_config.py で起動前に設定チェックを行うことを推奨します。
- ログディレクトリが作成できない場合、ファイル出力は無効化されコンソール出力のみになります（setup_logging の挙動）。

---

## 開発・テストのヒント

- 自動 .env 読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- config/*.yaml の検証には PyYAML があると詳細チェックが行われます。無い場合は検証がスキップされます（警告）。
- Monitoring / Execution の停止は data/stop_requested.flag を作ることで優雅に終了を促せます。
- 単体テスト用に内部のファイル呼び出し関数（例: ai の API 呼び出し）をモックする設計になっています（_call_openai_api を patch するなど）。
- DuckDB/SQLite のスキーマは init_monitoring_db で自動作成・マイグレーションされます。

---

README はこのコードベースの主要点をまとめたものです。実際の運用やデプロイ時は環境（ネットワーク / broker の接続・認証）に応じて追加の設定・安全対策を行ってください。必要であれば、起動例や .env.example のテンプレートを追記しますので指示してください。