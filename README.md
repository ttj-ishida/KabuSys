# KabuSys

日本株自動売買システムの一部（ライブラリ + 起動スクリプト群）。  
このリポジトリはトレーディングロジック（ポートフォリオ構築、ポジションサイズ決定、リスク制御）、監視・アラート、ペーパートレード検証、AI ベースのニュースセンチメント評価、研究用ファクター計算ユーティリティなどを含みます。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は日本株自動売買のためのモジュール群です。主な目的は以下:

- シグナルから銘柄選定・配分・発注までの実行エンジン（ExecutionEngine）
- 実行系の監視（System / Trade / Risk モニタリング）と Kill Switch
- ペーパートレード用の分離された DB と検証レポート
- ニュースを用いた AI センチメント（OpenAI を利用）
- DuckDB を用いたファクター計算・リサーチ
- 環境設定ウィザード & 設定検証ツール

設計方針として「可能な限りフェイルセーフ」「ルックアヘッドバイアスを避ける」「本番とペーパートレードを分離」などが採用されています。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV に応じて本番/ペーパートレードを切替。
  - run_monitoring.py: SystemMonitor のポーリングループを起動（デフォルト 60 秒間隔、環境変数で変更可）。
- 環境設定・検証
  - config_setup.py: 対話式ウィザードで `.env` を作成/更新。
  - validate_config.py: 起動前チェック (.env や config/*.yaml の存在・基本検証)。
- 監視・アラート
  - monitoring_engine, system_monitor, trade_monitor, risk_monitor, kill_switch 等。
  - kill.flag を書き込むことで ExecutionEngine を停止（KillSwitch）。
  - stop_requested.flag により run_* スクリプトの外部停止。
- ポートフォリオ構築
  - 銘柄選定、等ウエイト/スコア配分、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元株丸め、集計キャップ調整）。
- リサーチ
  - DuckDB 接続を受けてファクター（モメンタム、バリュー、ボラティリティ）計算、特徴量解析（IC、統計サマリ）を実行。
- AI（OpenAI）連携
  - news_nlp: ニュースを LLM に投げて銘柄ごとのセンチメントを ai_scores テーブルへ書込み。
  - regime_detector: ETF の MA200 とマクロニュースの LLM 解析を組合せて市場レジーム判定を行い DB に書き込み。
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB から検証レポートを生成（稼働率、注文成功率、レイテンシ等）。

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントなどにより推奨）
- SQLite は標準ライブラリに含まれる
- OS により一部機能（プロセス優先度、CPU affinity）は psutil に依存

1. リポジトリを取得し、パッケージとしてインストール（開発モード推奨）
   - python -m pip install -e .

2. 依存パッケージ（例）
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（validate_config の YAML 検証を有効にする場合）
   インストール例:
   - python -m pip install duckdb psutil openai PyYAML

3. ディレクトリを作成（必要に応じて）
   - data/ （SQLite DB、pid/flag ファイル用）
   - logs/（ログ出力、setup_logging が作成可能）
   例:
   - mkdir -p data logs

4. 環境変数設定
   - 対話式で作る場合:
     - python -m kabusys.config_setup
   - 手動または CI 用に .env を作成し、以下の必須値を設定:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（主なもの）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（監視 DB、デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時の専用 DB）
     - LOG_LEVEL
     - OPENAI_API_KEY（AI 機能）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒）

5. 自動 .env ロードの制御:
   - デフォルトでプロジェクトルートの `.env` / `.env.local` を自動ロードします。
   - 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 使い方

以下は主要な起動例・ツールの実行例です。

- 環境検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - これにより .env を対話式に生成・更新できます。

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - 実行中に停止させるには:
    - data/stop_requested.flag を作成すると run_execution の監視ループが検知して停止します。
    - Kill Switch（監視コンポーネントが条件を満たすと data/kill.flag を書き込み）で ExecutionEngine を停止できます。
  - 注意:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。本番 DB と完全分離されます。
    - 実行中は data/execution.pid に PID が書かれます。

- 監視ループの起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。
  - run_monitoring は常に本番の sqlite_path（Settings.sqlite_path）を使用して監視 DB を開きます（KABUSYS_ENV に依存しません）。

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを明示可能。環境変数 PAPER_TRADING_SQLITE_PATH が優先されます。

- AI (ニュース NLP / レジーム判定)
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数に指定）。
  - 例（コード内から呼び出し）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="sk-...")

- ログ
  - setup_logging により logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/ ディレクトリ）。
  - 環境変数 LOG_DIR で変更可。

停止・フラグ関連の仕組み（重要）
- data/stop_requested.flag: run_execution / run_monitoring はこのファイル存在をポーリングしてプロセス停止を行います。外部から安全に停止させる用途。
- data/kill.flag: KillSwitch が書き込むファイルで、ExecutionEngine に対する停止シグナル（kill_flag_path は Settings.kill_flag_path から取得可能）。既存の場合は上書きしない（冪等）。

注意点 / 推奨
- 本番運用時は KABUSYS_ENV=live を使用。validate_config で警告や設定ミスを確認してください。
- psutil による優先度設定は OS に依存します（権限不足で失敗する場合はログに警告）。
- OpenAI を使う機能は API レート制限やエラーに備えリトライやフォールバック（スコア 0 など）を実装していますが、キーの管理は慎重に行ってください。

---

## ディレクトリ構成（主要ファイルと役割）

（src/kabusys 以下を示します）

- kabusys/
  - __init__.py
  - config.py
    - Settings クラス、.env の自動ロード、環境変数取得ユーティリティ
  - config_setup.py
    - .env 作成用の対話式ウィザード
  - validate_config.py
    - 起動前チェック CLI（必須環境変数、config/*.yaml、パス等を確認）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
  - tools/
    - __init__.py
    - paper_verification_report.py
      - ペーパートレード検証レポート生成 CLI
  - ai/
    - __init__.py
    - news_nlp.py
      - raw_news を LLM で処理して ai_scores テーブルに書き込むロジック
    - regime_detector.py
      - ETF MA200 とマクロニュースの LLM 解析でレジーム判定
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化と読み書きラッパ（MonitoringDB）
    - monitoring_engine.py
      - 各 Monitor を束ねるポーリングエンジン
    - system_monitor.py
      - CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - trade_monitor.py (実装は本リストに部分的に含まれています)
    - kill_switch.py
      - Kill Switch 実装（条件満たせば kill.flag を書き込む）
    - alert_manager.py (アラート送信ロジック: LINE 等)
  - portfolio/
    - portfolio_builder.py
      - 候補選定、等重/スコア重み計算
    - position_sizing.py
      - 株数計算（リスクベース / 等分 / スコアベース）
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー ファクター計算（DuckDB）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ
    - __init__.py
  - utils/
    - logging_setup.py
      - 共通のログ設定ユーティリティ（Stream + TimedRotatingFileHandler）
    - process_priority.py
      - OS に依存しないプロセス優先度 / CPU affinity 設定
    - __init__.py

- その他
  - config/*.yaml: 各種設定ファイル（存在しない場合は validate_config で警告）
  - data/: デフォルトの DB / PID / flag 保存ディレクトリ（手動で作成するか起動時に作成されます）
  - logs/: デフォルトのログ出力先

---

## よくある質問・トラブルシューティング

- Q: run_monitoring のポーリング間隔を短くしたい
  - A: 環境変数 MONITOR_POLL_INTERVAL（秒）を設定。例: export MONITOR_POLL_INTERVAL=30

- Q: ペーパートレードのデータを本番 DB と分離したい
  - A: KABUSYS_ENV=paper_trading に設定すると、run_execution は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

- Q: OpenAI API 呼び出しで失敗する
  - A: OPENAI_API_KEY が設定されているか確認、また依存パッケージのバージョンを確認してください。API の 429/5xx に対してはコード内でリトライ処理が組み込まれています。

- Q: ログファイルが作成されない
  - A: デフォルトでは logs/ ディレクトリを作成しようとしますが権限の問題で失敗する場合は標準出力のみになります。LOG_DIR 環境変数や setup_logging の引数で変更できます。

---

## 開発者向けメモ

- DuckDB に接続している関数は外部副作用（DB 書き込み）を伴うものとそうでないものがあるため、テスト時は DB 接続を差し替える（モック/一時 DB）ことを推奨します。
- news_nlp / regime_detector は OpenAI クライアント呼び出しを専用関数に抽象化しているため、ユニットテスト時はその呼び出しを patch して HTTP 呼び出しを避けてください。
- Settings は .env の自動ロードを行いますが、テスト時にこれを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README に追記します。たとえば、各モジュールの API ドキュメント、設定ファイルのサンプル（.env.example）、依存パッケージの厳密なバージョン、Docker 化手順などを追加できます。どの情報を優先して追記しましょうか？