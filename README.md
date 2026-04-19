# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ / 起動スクリプト群）

このリポジトリは、取引エンジン（ExecutionEngine）、監視 (Monitoring)、ポートフォリオ構築、リサーチ、AI ベースのニュース分析などの主要コンポーネントを含むモジュール群で構成されています。各コンポーネントは可能な限り疎結合に設計されており、テストやペーパートレード運用を配慮しています。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数（主なキー）
- ディレクトリ構成
- よくある注意点 / トラブルシュート

---

## プロジェクト概要

KabuSys は、以下を目的とした日本株自動売買システムのコンポーネント群です。

- シグナルに基づくポートフォリオ構築とポジションサイジング
- 発注エンジン（実口座 / ペーパートレードの分離）
- システム稼働監視・リスク監視（Kill Switch を備える）
- ニュースを用いた AI ベースのセンチメント評価・レジーム判定（OpenAI を利用）
- リサーチ用のファクター計算（DuckDB を利用）
- 運用補助ツール（設定ウィザード、検証レポート生成 等）

設計方針として、外部 IO（発注 API 等）は必要な箇所でのみ抽象化し、リサーチ/ポートフォリオ計算は純粋関数として実装しています。

---

## 主な機能一覧

- Execution
  - ExecutionEngine（発注・リスク管理・オーダー管理）
  - paper_trading モードでは MockBroker を使用し、本番 DB と分離
- Monitoring
  - SystemMonitor: CPU/メモリ/Disk・データ鮮度・プロセス存在を監視
  - TradeMonitor / RiskMonitor: 約定・滞留注文・ドローダウン等を監視
  - KillSwitch: 指定条件で data/kill.flag を作成してエンジン停止
  - MonitoringEngine: 各モニタの統合ループ
- Portfolio
  - 候補選定 / 等金額・スコア加重配分 / リスクベースのポジションサイジング
  - セクターキャップ / レジーム乗数
- Research
  - momentum / volatility / value 等のファクター計算（DuckDB）
  - 将来リターン、IC 計算、特徴量サマリ
- AI
  - ニュースの LLM（OpenAI）によるセンチメントスコアリング（ai_scores への書き込み）
  - マクロ + MA200 を組み合わせた市場レジーム判定
- ツール
  - 対話式 .env 作成ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（TimedRotatingFileHandler + stdout）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順（ローカル開発用）

前提: Python 3.9+（型注釈に依存するため推奨）。実行環境に応じてバージョンは調整してください。

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 基本的に必要なもの:
     - duckdb
     - psutil
     - openai
     - PyYAML（config/*.yaml の検証を行う場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそれを使ってください）

4. データディレクトリ作成（ログや DB 用）
   - mkdir -p data logs

5. .env を作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - または直接 .env を作る（下記「環境変数」を参照）

6. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば .env や config/*.yaml を修正

---

## 使い方（主要スクリプト / コマンド）

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成 / 更新します

- 設定検証
  - python -m kabusys.validate_config [--strict]
  - 必須環境変数やファイルの存在などをチェックします

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV によって以下の挙動が変わります:
    - paper_trading: MockBroker を使用し、デフォルトで data/paper_trading.db を使用（本番 DB と完全分離）
    - live/development: settings.sqlite_path（デフォルト data/monitoring.db）や実ブローカを使用
  - 停止方法:
    - data/stop_requested.flag を作成するとループが安全に終了します
    - Kill Switch（data/kill.flag）が作動すると ExecutionEngine に停止命令が送られます

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒、デフォルト 60）で上書き可能
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して永続化します（監視ログは本番 DB に保存）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI / リサーチ用関数（ライブラリ呼び出し）
  - ニューススコアリング: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ファクター: kabusys.research.calc_momentum / calc_volatility / calc_value
  - これらは DuckDB 接続や OpenAI API キーを引数で受け取ります（環境変数も利用可能）

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要な任意/設定系:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の注文充足挙動（instant / partial / never / reject。デフォルト: instant）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...。デフォルト: INFO）
- LOG_DIR — ログファイル格納ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（ニュース NLP / レジーム判定で必要）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_PATH — Kill Switch 用の flag パス（デフォルト: data/kill.flag）
- PID_FILE_PATH — ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

注意:
- PAPER_FILL_MODE の有効値は "instant", "partial", "never", "reject" のいずれかです。
- OPENAI_API_KEY が未設定の場合、AI 機能は動作しないか、明示的に api_key を渡す必要があります。

例 (.env に想定される最小例):
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

（重要）.env は絶対にリポジトリにコミットしないでください。

---

## ディレクトリ構成（主要ファイル）

（src をルートとしたパッケージ構成の抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / .env の読み込みと Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py       (存在：コードベース参照)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       (存在：通知管理)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
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
  - data/ (運用時に作成される / DB・フラグ等を格納)
  - logs/ (ログ出力先デフォルト)

※ 一部ファイルはここに抜粋されていないかもしれません（省略あり）。実装の詳細は各モジュールの docstring を参照してください。

---

## よくある注意点 / トラブルシュート

- DB ファイルや logs ディレクトリのパーミッション:
  - ログディレクトリや data ディレクトリに書き込み権限が必要です。作成・権限設定を確認してください。
- OpenAI API:
  - OPENAI_API_KEY がないと news_nlp / regime_detector の機能は動作しません。API 呼び出しは失敗時にフェイルセーフ（スコア 0 等）を取る箇所もありますが、完全機能の検証にはキーが必須です。
- PyYAML:
  - validate_config は PyYAML がない場合、config/*.yaml の内容検証をスキップします（警告が出ます）。YAML 検証が必要なら PyYAML をインストールしてください。
- psutil の権限:
  - プロセス優先度設定や CPU affinity は権限によって失敗することがあります（警告ログによりスキップされます）。
- MONITOR_POLL_INTERVAL:
  - 環境変数で秒数を指定します。不正な値（数字でない、または 1 未満）は無視されデフォルト 60 秒に戻ります。
- 停止フラグ
  - run_monitoring / run_execution はプロジェクトルート下の data/stop_requested.flag を監視して安全に停止します。
  - KillSwitch は data/kill.flag を作成して ExecutionEngine に強制停止をトリガします（本番運用では注意して扱ってください）。
- ペーパートレード
  - KABUSYS_ENV=paper_trading にすると発注周りは MockBroker を使い、デフォルトで data/paper_trading.db に履歴を書きます。本番 DB とは完全に分離されます。

---

この README はコードベースの主要点をまとめたものです。各モジュールには docstring に動作や設計上の注意が記載されていますので、実際に利用・拡張する際は該当ファイルを参照してください。必要であれば、README へ実行例や運用手順（systemd / supervisor 用のサービス定義例など）を追記します。