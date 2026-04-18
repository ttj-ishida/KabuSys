# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のソースコード群です。取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI ベースのニュース NLP などの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を持つモジュール群から構成された自動売買フレームワークです。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム稼働・注文・リスク監視、Kill Switch）
- Portfolio（銘柄選定、配分、ポジションサイズ計算）
- Research（ファクター計算、特徴量解析）
- AI（ニュースのセンチメント解析、レジーム判定）
- 小道具（設定ウィザード・設定検証・検証レポート生成）

設計上のポイント：
- 環境変数（.env）により設定を管理
- Paper Trading 用に本番 DB と分離（data/paper_trading.db）
- DuckDB を分析用途、SQLite を監視・ログ用途に利用
- OpenAI API を利用した NLP 機能（任意）
- ロギングは標準化されたセットアップ（logs/*.log）

---

## 主な機能一覧

- 設定関連
  - 対話式 .env 作成ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config

- 実行・監視
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い data/paper_trading.db に記録
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
    - 停止は data/stop_requested.flag により制御

- ポートフォリオ構築
  - 候補選定、スコア重み、等金額重み
  - セクターキャップ、レジーム乗数
  - ポジションサイズ計算（単元株丸め、利用可能資金スケール）

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - news_nlp: OpenAI を用いた銘柄別ニュースセンチメント算出（ai_scores テーブルへ書込）
  - regime_detector: ETF（1321）MA200 乖離 + マクロニュースで日次レジーム判定

- ツール
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## セットアップ手順（ローカル開発向け）

1. Python 環境を用意（推奨: 3.10+）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要なパッケージ例:
     - duckdb
     - psutil
     - openai
     - pyyaml (設定検証時に config/*.yaml のパースを行う場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （リポジトリに requirements.txt がある場合はそちらを利用してください）

3. .env を作成
   - 対話式ウィザードを使うのが簡単:
     - python -m kabusys.config_setup
   - 主要な環境変数（例）:
     ```
     # 必須
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password

     # 任意 / デフォルトあり
     KABUSYS_ENV=development            # development | paper_trading | live
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     LOG_LEVEL=INFO
     OPENAI_API_KEY=sk-xxxx...         # AI 機能を使う場合必須
     LINE_CHANNEL_ACCESS_TOKEN=        # アラート通知を行う場合
     LINE_USER_ID=
     ```
   - .env を Git にコミットしないこと（セキュリティ上の理由）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにする: python -m kabusys.validate_config --strict

5. データディレクトリの作成（必要に応じて）
   - デフォルトの DB / pid / flag 保存場所は data/ 配下です。起動スクリプトが自動で作成する場合もありますが事前作成しておくと安心です。
     - mkdir -p data logs

---

## 使い方（起動・実行例）

- 監視サービスの起動（バックグラウンドや systemd 等での運用想定）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で指定（例: 30）
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

  - 停止:
    - data/stop_requested.flag を作成するとループが検知して終了します

- 実行エンジンの起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading に設定すると MockBrokerClient を使い paper_trading 用 DB に記録
  - 実行中のプロセス優先度は起動時に高優先度にセットされます（可能であれば）

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告で exit(1) になります

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY を設定
  - モジュール関数を直接呼ぶ:
    - kabusys.ai.score_news(conn, target_date)
    - kabusys.ai.regime_detector.score_regime(conn, target_date)

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development | paper_trading | live）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、監視起動スクリプト用）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）

注意: .env.example を参考に .env を準備してください（リポジトリに含まれている場合）。

---

## ログ・フラグ・PID

- ログ: デフォルト logs/ ディレクトリにアプリケーションごとのログファイルが生成されます（例: logs/monitoring.log, logs/execution.log）。
- 停止フラグ:
  - data/stop_requested.flag — run_monitoring / run_execution が監視する停止フラグ
  - data/kill.flag — KillSwitch が書き込む停止指示用フラグ（ExecutionEngine 停止トリガ）
- PID:
  - data/execution.pid — ExecutionEngine が利用する PID ファイル（Settings.pid_file_path 経由で変更可）

---

## ディレクトリ構成（抜粋）

以下は主なファイル・モジュールの構造（src/kabusys 以下）です：

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - execution/                — 発注関連コンポーネント（Engine, BrokerFactory, OrderManager 等）
    - data/                     — （実行時に作られる）DB / flags / pid などの配置先
    - config/                   — YAML 設定テンプレート群（system_config.yaml 等）

（実際のリポジトリにはさらに多くのモジュール・補助ファイルが含まれます）

---

## よくあるトラブルシューティング

- 起動時に必須環境変数が足りない:
  - python -m kabusys.validate_config を実行して不足項目を確認してください。
- OpenAI を利用する機能で API キーがない:
  - 環境変数 OPENAI_API_KEY を設定する必要があります。テスト時はモック化可能です（モジュール内の API 呼び出しを差し替え）。
- SQLite / DuckDB のファイルアクセスエラー:
  - パスの親ディレクトリが存在しない場合は作成してください（logs/ や data/）。ロギングユーティリティはログディレクトリ作成失敗時にコンソールのみ出力にフォールバックします。
- run_execution がすぐ終了する:
  - data/stop_requested.flag が存在すると起動をスキップします。必要に応じて削除してください。

---

## 開発・拡張のヒント

- テストを書く際は Settings の自動 .env ロードを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。
- AI 系の API 呼び出し部分は内部で _call_openai_api を用いているため、ユニットテスト時はパッチしてエミュレーションできます。
- DuckDB 接続をモックしてファクター計算/リサーチ関数を単体テストすると良いです。

---

この README は主要な使い方と構造の概要を示しています。詳細は各モジュールの docstring（ソースコード内の説明）を参照してください。必要があれば導入手順や systemd ユニット例、デプロイ手順などを追加で作成します。