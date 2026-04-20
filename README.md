# KabuSys

日本株自動売買システム（ライブラリ/実行スクリプト群）

このリポジトリは、シンプルな自動売買フレームワークと周辺ツールを含みます。
主要機能は戦略の研究（ファクター計算・特徴量解析）、ポートフォリオ構築、発注実行（本番／ペーパートレード）、監視・アラート、ならびにニュース NLP によるセンチメント計算です。

---

## 概要

- 戦略研究用モジュール（duckdb を用いたファクター計算、将来リターン、IC 計算 等）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出・セクター制約）
- ExecutionEngine（発注、リスク管理、オーダー管理）：
  - KABUSYS_ENV によって paper_trading（MockBroker）と live（実ブローカー）を切替
  - paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離
- 監視（Monitoring）：システム状態・注文ログ・リスクを定期ポーリングして DB に記録、Kill Switch を発動
- AI 製品群（ニュース NLP, レジーム判定）：OpenAI API を利用してニュースからスコア算出
- ツール：Paper Trading の検証レポート生成スクリプト等
- 各種 CLI：.env 作成ウィザード、設定検証ツール、run_monitoring/run_execution、ツール群

---

## 主な機能一覧

- 環境設定ウィザード（.env の対話的作成）：kabusys.config_setup
- 設定検証：kabusys.validate_config（YAML ファイル・必須環境変数のチェック）
- ExecutionEngine 起動スクリプト：run_execution.py
  - KABUSYS_ENV=paper_trading では MockBroker を使用
  - paper_trading 用 DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
- Monitoring 起動スクリプト：run_monitoring.py
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視ログは SQLite（settings.sqlite_path）へ永続化（monitoring DB テーブルを自動作成）
- Paper Trading 検証レポート生成：kabusys.tools.paper_verification_report
- ポートフォリオ構築・リスク調整・ポジションサイジング：kabusys.portfolio.*
- ファクター計算・研究ツール：kabusys.research.*
- ニュース NLP とレジーム判定（OpenAI 連携）：kabusys.ai.*
- ロギング設定ユーティリティ、プロセス優先度設定ユーティリティ等のユーティリティ群

---

## 必要要件（例）

- Python 3.10+（型アノテーションの使用を想定）
- パッケージ（最小限の例）
  - duckdb
  - psutil
  - openai
  - pyyaml（設定検証で YAML のパースを行う場合に任意）
- sqlite3（Python 標準モジュール）
- 上記は環境に合わせて pip install してください（requirements.txt は本リポジトリに含まれていないため適宜作成してください）。

---

## セットアップ手順

1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows の場合は .venv\Scripts\activate）

2. 必要なパッケージをインストール
   - pip install duckdb psutil openai pyyaml

3. .env の作成（対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードが終了するとプロジェクトルートに `.env` が生成されます。
   - 必須項目（例）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な環境変数（抜粋）:
     - KABUSYS_ENV: development | paper_trading | live
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR
     - OPENAI_API_KEY: OpenAI を利用する場合に設定（news_nlp / regime_detector 用）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

5. データ・ログディレクトリの準備
   - `data/` と `logs/` は自動作成されますが、権限やマウント先を事前に確認してください。

---

## 使い方（主要コマンド）

- ExecutionEngine を起動（対話・デーモン管理は環境に合わせて動作させてください）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
    - 実行中は PID が data/execution.pid に書き込まれます（設定で変更可）。

- Monitoring を起動
  - MONITOR_POLL_INTERVAL（秒）でポーリング間隔を指定可能:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 挙動:
    - 監視は settings.sqlite_path（monitoring DB）を使用します（KABUSYS_ENV に依存せず本番 DB を参照）。
    - 監視ロジックは system_monitor / trade_monitor / risk_monitor を順に実行し、必要に応じて kill.flag を書き込みます。

- 停止方法
  - run_execution / run_monitoring はプロセス内で `data/stop_requested.flag` を監視しており、該当ファイルが存在するとループを終了します。
  - monitor が条件を満たした場合（KillSwitch）、`data/kill.flag` が書き込まれ、ExecutionEngine 側が検出して終了処理を行います。
  - 手動で停止したい場合は、適宜 stop_requested.flag を作成するかプロセスを kill してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db で上書き可能）
  - 出力: 標準出力にレポート（各種指標と PASS/FAIL 判定）

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY（news_nlp / regime_detector を使う場合）
- KABUSYS_ENV（development / paper_trading / live）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading 時のマッチング挙動: instant | partial | never | reject）
- LOG_LEVEL（デフォルト INFO）
- LOG_DIR（デフォルト logs）
- MONITOR_POLL_INTERVAL（run_monitoring での間隔、秒。デフォルト 60）
- KILL_FLAG_PATH（KillSwitch のパス。Settings で取得）

---

## ログとファイル

- ログファイル: logs/<app_name>.log（app_name は monitoring / execution 等）
  - ローテーション: 日次、30 日分保持（TimedRotatingFileHandler）
- PID / フラグ:
  - data/execution.pid — ExecutionEngine の PID（デフォルト）
  - data/stop_requested.flag — 手動停止フラグ（監視/実行スクリプトはこれを見て終了）
  - data/kill.flag — Monitoring の KillSwitch が書き込む停止理由（ExecutionEngine に通知）

---

## 開発者向けディレクトリ構成（抜粋）

以下は `src/kabusys` 以下の主要ファイル／モジュール（提供コードベースから抜粋）。

- run_monitoring.py — Monitoring のポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — 環境変数 / 設定読み込みロジック、Settings クラス
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI

- ai/
  - news_nlp.py — ニュースの NLP（OpenAI）によるセンチメントスコア算出
  - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）

- monitoring/
  - monitoring_db.py — SQLite を使った監視ログ永続化層（初期化・CRUD）
  - system_monitor.py — システム状態・データ鮮度の監視
  - trade_monitor.py — 注文ログの監視（滞留注文・異常約定など）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の書き込みロジック
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - alert_manager.py —（アラート送信ロジック、ソース内に参照あり）

- execution/
  - execution_engine.py — ExecutionEngine（セッション管理・発注ループ等）
  - broker_factory.py — ブローカークライアント生成（Mock / 実装切替）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 発注管理関連

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数算出・資金配分
  - risk_adjustment.py — セクター上限、レジーム乗数

- research/
  - factor_research.py — モメンタム／バリュー／ボラティリティ等ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

- tools/
  - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度（nice / Windows priority）・CPU affinity 設定

---

## 注意事項 / 運用上のポイント

- 本番（KABUSYS_ENV=live）での起動は慎重に行ってください。validate_config は本番向けの警告チェックを行います。
- .env ファイルは機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- Monitoring は settings.sqlite_path（監視 DB）を常に使います。paper_trading でも監視 DB は共有されます（設計上の挙動）。
- ExecutionEngine は paper_trading の場合に paper_sqlite_path を使用して発注ログを本番から分離します。
- OpenAI API を利用する機能（news_nlp / regime_detector）は API キー（OPENAI_API_KEY）を環境変数に設定する必要があります。API コール回数と料金に注意してください。
- ログディレクトリ作成に失敗した場合、コンソール出力のみで継続します。権限やディスク空き容量を監視してください。

---

以上がこのコードベースの簡易 README です。必要であれば「運用手順（systemd ユニット例）」「デバッグ方法」「拡張ポイント」などの追記や、各モジュールの API 参照（関数引数・戻り値の詳細）を別ドキュメントとして整備できます。どの部分を詳しく追加しましょうか？