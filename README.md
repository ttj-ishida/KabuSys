# KabuSys — 日本株自動売買システム

このリポジトリは日本株の自動売買・研究・監視を目的とした内部ライブラリ群です。
README はプロジェクトの概要、主な機能、セットアップ手順、基本的な使い方、およびディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 株価データや財務データを用いたファクター計算・研究（research）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- ExecutionEngine を介した発注管理（実際の発注 or ペーパートレード）
- 監視（System / Trade / Risk）と Kill Switch による自動停止機構
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- Paper Trading の検証レポート生成ツール

設計上のポイント:
- 設定は .env（自動ロード機構あり）や config/*.yaml で管理
- ペーパートレード用 DB は本番 DB と分離（PAPER_TRADING_SQLITE_PATH）
- LLM（OpenAI）利用部分は API 呼び出しとエラー処理を慎重に扱う（リトライ・フォールバック）

---

## 機能一覧（抜粋）

- 環境設定ウィザード: python -m kabusys.config_setup
- 設定検証 CLI: python -m kabusys.validate_config
- Execution エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading で MockBroker を使用し専用 DB に記録
- Monitoring 起動（定期ポーリング）: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（デフォルト 60 秒）
- Kill Switch（data/kill.flag）による ExecutionEngine 停止
- Paper Trading 検証レポート生成ツール:
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
- ポートフォリオ構築:
  - 候補選定（スコア順）、等重配分、スコア加重配分、リスクベースの株数算出
- 研究用モジュール:
  - momentum / volatility / value 等のファクター計算（DuckDB を使用）
  - 将来リターン・IC（Information Coefficient）計算、特徴量サマリ
- AI モジュール:
  - news_nlp: ニュース記事を OpenAI でセンチメント化し ai_scores テーブルに書き込み
  - regime_detector: ETF（1321）MA とマクロニュースで市場レジーム判定

---

## セットアップ手順（ローカル開発向け）

以下は最小限のセットアップ手順の例です。実際の依存関係は pyproject.toml / requirements.txt を参照してください。

1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   （requirements.txt がない場合は duckdb, psutil, openai, pyyaml などを個別に入れる）

4. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（.env は絶対に Git にコミットしないでください）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 下にログや DB が作成されます
   - paper_trading を利用するなら data/paper_trading.db が使用されます

注意:
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を .env に設定してください。
- J-Quants / kabuステーション API の資格情報は必須項目です（ウィザードで設定）。

---

## 環境変数（主要）

主要な環境変数とデフォルト値／意味の概要:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (LLM を使うときに必要)
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト development
  - paper_trading: ペーパートレード用の専用 SQLite を使用
  - live: 本番（注意して使用）
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject、デフォルト instant）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード DB）
- DUCKDB_PATH: data/kabusys.duckdb（分析用）
- SQLITE_PATH: data/monitoring.db（監視用 / production 用）
- LOG_LEVEL: INFO（または DEBUG, WARNING, ...）
- LOG_DIR: ログ出力先（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

ファイルベースのフラグ / PID:
- data/kill.flag — KillSwitch が書き込む停止フラグ（ExecutionEngine 停止トリガ）
- data/stop_requested.flag — run_monitoring / run_execution で検知してループを終了するためのストップファイル
- data/execution.pid — ExecutionEngine の PID ファイル（起動時に設定される）

---

## 使い方（主要コマンド）

- 環境設定ウィザード（初期 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード: python -m kabusys.validate_config --strict

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ data/paper_trading.db に記録されます
  - 起動前に data/stop_requested.flag が存在すると起動しない（安全仕様）

- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring（ポーリング間隔を上書き）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで別 DB を指定可（未指定時は環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI スコアリング / レジーム判定（ライブラリ呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り内部で DB 書き込みを行います

停止・Kill:
- kill.flag を作成すると（KillSwitch）ExecutionEngine 停止シグナルが発出されます
  - KillSwitch は risk_monitor の判断等で書き込まれます
- 実行プロセスを手動で停止する場合は data/stop_requested.flag を作成してください（run_* スクリプトが検知して終了）

ログ:
- ログは stdout と logs/<app_name>.log（デイリーローテート）に出力されます
- setup_logging(app_name="...") を各起動スクリプトで呼んで統一管理しています

プロセス優先度:
- 起動スクリプトは起動直後にプロセス優先度を "high" に設定する試みを行います（プラットフォーム依存）

---

## ディレクトリ構成（主要ファイルと説明）

リポジトリの主要なモジュール構成（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（各種設定をプロパティで取得）
  - config_setup.py
    - .env を対話式に作成するウィザード
  - validate_config.py
    - .env と config/*.yaml を検証する CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 用 DB 分離）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py
      - ログ設定（stdout + TimedRotatingFileHandler）
    - process_priority.py
      - プロセス優先度 / CPU affinity のユーティリティ
  - monitoring/
    - monitoring_db.py
      - SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
      - システム状態・データ鮮度監視
    - trade_monitor.py
      - （取引関連の監視ロジック）
    - risk_monitor.py
      - ドローダウン・ポジション数監視
    - kill_switch.py
      - Kill Switch 制御（flag 書き込み・評価）
    - alert_manager.py
      - （通知管理: LINE など）
    - monitoring_engine.py
      - すべての Monitor を束ねるエンジン
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
    - ...（Execution 関連の実装）
  - portfolio/
    - portfolio_builder.py
      - 候補選定・等重／スコア重み計算
    - position_sizing.py
      - 株数算出、リスク制限、単元丸め
    - risk_adjustment.py
      - セクターキャップ、レジーム乗数
  - research/
    - factor_research.py
      - momentum / volatility / value のファクター計算（DuckDB）
    - feature_exploration.py
      - forward returns / IC / factor summary
  - ai/
    - news_nlp.py
      - ニュース記事を OpenAI でスコアリングし ai_scores に書込む
    - regime_detector.py
      - マクロ + ETF MA を用いた市場レジーム判定
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成

（上の説明は主要ファイルのみ抜粋。細かな実装は各モジュールを参照してください）

---

## 開発上の注意点・運用メモ

- .env は機密情報を含むため絶対にリポジトリにコミットしないでください
- KABUSYS_ENV を `live` にする場合は特に注意してください（validate_config が警告を出します）
- ペーパートレードは本番 DB と完全分離されていますが、設定ミスで混在しないよう .env を確認してください
- OpenAI を使う処理は API コストが発生します。テスト時はモック化するか API キーを設定しないでください
- SQLite / DuckDB のパスはデフォルトで data/ 下に置かれます。適宜バックアップ・保守を検討してください
- ログは daily rotate（30 日保持）されます。ディスク容量に注意してください

---

以上がこのリポジトリの README です。追加で「導入ガイド（Docker / systemd / 監視運用例）」「詳細 API ドキュメント」「開発者向けコントリビュート手順」などが必要であれば、目的に合わせて追記できます。