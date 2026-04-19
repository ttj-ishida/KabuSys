# KabuSys

日本株向けの自動売買 / 研究プラットフォームの一部実装です。  
このリポジトリには、ポートフォリオ構築・ポジションサイジング・ファクター計算・AI ベースのニュースセンチメント評価・実行エンジン起動スクリプト・監視（Monitoring）等のモジュールが含まれます。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム用ユーティリティ群です。主な目的は以下です。

- 市場データ（DuckDB）を用いたファクター計算・特徴量解析
- ポートフォリオ構築（候補選定・重み計算）と株数決定（単元丸め・リスク配分）
- AI（OpenAI）を使ったニュースセンチメント評価と市場レジーム判定
- 実行エンジン（ExecutionEngine）を起動するためのスクリプト（paper/live 切替をサポート）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- Paper Trading の検証レポート生成ツール
- .env 対話式ウィザードと設定検証ツール

---

## 機能一覧

- 設定管理
  - .env 自動ロード（プロジェクトルートを探索）
  - config_setup.py による対話式 .env 生成
  - validate_config.py による起動前チェック

- 実行系
  - run_execution.py: ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper/live 切替）
  - Paper Trading の場合は MockBroker を使用し、専用 SQLite に記録

- 監視系
  - run_monitoring.py: SystemMonitor ポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
  - MonitoringEngine: System / Trade / Risk モニタを束ね、アラートや Kill Switch を評価
  - MonitoringDB: SQLite にログやダッシュボードを永続化

- ポートフォリオ
  - 銘柄選定（スコア降順）／等重・スコア重み付け
  - セクター上限チェック、レジーム乗数
  - 株数決定（risk_based / equal / score）、単元株丸め、aggregate cap 的スケーリング

- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ

- AI（OpenAI）
  - news_nlp: raw_news を集約して LLM でセンチメントを算出し ai_scores に保存
  - regime_detector: ETF（1321）の MA200 乖離 + マクロセンチメントから市場レジーム判定

- ツール
  - tools.paper_verification_report: Paper Trading DB から検証レポートを生成

---

## セットアップ手順

前提:
- Python 3.10+（typing の新機能を使用）
- Git リポジトリのルートにプロジェクトがあること（.env 自動ロードで .git または pyproject.toml を探索します）

1. リポジトリをクローン / checkout

2. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 必須（主に本コードで参照されるもの）:
     - duckdb
     - psutil
     - openai
   - 任意（YAML 検証を行う場合）:
     - PyYAML
   例:
     pip install duckdb psutil openai PyYAML

   （requirements.txt はこのリポジトリに含まれていない想定のため、上記を直接インストールしてください）

4. .env を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合:
     python -m kabusys.validate_config --strict

6. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 以下に DB や PID/フラグファイルが作られます
   - ログは logs/ 以下に出力されます（ログディレクトリは環境変数 LOG_DIR でも変更可）

---

## 環境変数（主要）

以下は主要な環境変数です。詳しい説明は config_setup.py / config.py を参照してください。

必須（少なくとも起動前に設定）:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

運用関連:
- KABUSYS_ENV: execution 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")

データパス:
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

Paper / Mock ブローカー:
- PAPER_FILL_MODE: ペーパートレード時の約定モード ("instant" | "partial" | "never" | "reject")

OpenAI:
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）

LINE 通知（任意、本番向け）:
- LINE_CHANNEL_ACCESS_TOKEN
- LINE_USER_ID

ロギング / その他:
- LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs）
- PID_FILE_PATH: 実行エンジンの PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch 用フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリアするか（"1" はクリア、デフォルト "0"）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）

自動ロード:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用

  停止:
  - run_execution はループ中に data/stop_requested.flag の存在を監視します。
    停止させたい場合は stop_requested.flag を作成するか、ExecutionEngine 側で Kill Switch が kill.flag を書き込みます。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  停止:
  - run_monitoring はリポジトリルートの data/stop_requested.flag を監視します。ファイルを作成するとループを抜けます。

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI モジュール（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- これらはパッケージ内 API を直接呼び出す形を想定しています（unit tests / スクリプトから利用）。
- OpenAI の呼び出しは API キーが必要で、失敗時はフェイルセーフ（多くの場所で 0.0 などにフォールバック）として設計されています。

---

## 停止 / Kill Switch / フラグファイル

- stop_requested.flag: run_monitoring / run_execution の外部停止用フラグ（起動スクリプトが検知して安全に終了）
  - パス: <project_root>/data/stop_requested.flag

- kill.flag: KillSwitch（監視側）が発動したときに作成され、ExecutionEngine に対して停止シグナルとして機能
  - パスは Settings.kill_flag_path で変更可能（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動クリアする（本番では 0 推奨）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要なファイル・モジュール構成です（完全ではありませんが主要なものを列挙しています）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py  (参照あり)
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py  (参照あり)
    - execution/
      - execution_engine.py  (参照あり)
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
    - data/  (実行時に生成される)
      - monitoring.db (デフォルト)
      - paper_trading.db (paper_trading 用)
      - execution.pid
      - kill.flag
      - stop_requested.flag
    - logs/
      - execution.log
      - monitoring.log
      - ...（日次ローテーション）

---

## 開発時の注意 / ベストプラクティス

- .env は絶対に Git にコミットしないでください（config_setup.py にもその注意書きあり）
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を推奨
- OpenAI API を使用する機能は API 使用量に注意して実行してください（バッチ / リトライ実装はありますがコストは発生します）
- DuckDB / SQLite のパスは本番とテストで分離する（paper_trading 用 DB を利用することで本番 DB と干渉しない）
- ログは logs/ に日次ローテーションで出力されます。ログ保存先 / レベルは環境変数で変更可能

---

## 依存関係（概略）

- Python 3.10+
- duckdb
- psutil
- openai
- PyYAML（任意、config の YAML 検証で使用）

インストール例:
pip install duckdb psutil openai PyYAML

---

必要であれば、README に以下の追加を行えます：
- 各モジュール（ExecutionEngine / TradeMonitor 等）の詳細な API ドキュメント
- Docker / systemd ユニットのサンプル（プロダクション運用向け）
- CI / テスト実行方法（ユニットテストがある場合）
- requirements.txt や constraints.txt の生成

他に補足して欲しい箇所（例: 実行例、systemd ユニット、Dockerfile、API ドキュメントなど）があれば教えてください。