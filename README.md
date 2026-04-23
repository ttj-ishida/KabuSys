# KabuSys — README

日本株自動売買システムの一部を抜粋したコードベース向けREADMEです。以下はプロジェクトの概要、提供機能、セットアップ手順、使い方、ディレクトリ構成の要約です。

## プロジェクト概要
KabuSys は日本株の自動売買・研究・監視を目的としたモジュール群です。本リポジトリは以下を含みます（抜粋）:
- Execution: 注文発行／管理を行う ExecutionEngine とその周辺（ブローカーファクトリ、オーダーマネージャ等）
- Monitoring: システム稼働状況、注文ログ、リスク監視、Kill Switch、アラート管理
- Portfolio: 銘柄選定・重み計算・ポジションサイズ計算・セクター制約など
- Research: ファクター計算（Momentum/Value/Volatility 等）と特徴量探索・IC 計算
- AI: ニュースの NLP スコアリング（OpenAI）および市場レジーム判定
- Tools: Paper Trading の検証レポート生成スクリプト 等
- Utils: ロギング設定、プロセス優先度設定、環境変数ロードユーティリティ 等

バージョン: 0.1.0（src/kabusys/__init__.py）

## 機能一覧
主な機能（抜粋）:
- 実行環境モード:
  - development / paper_trading / live（KABUSYS_ENV）
  - paper_trading では MockBroker を使用し、本番 DB と完全分離された data/paper_trading.db を使用
- ExecutionEngine: ブローカーとのやり取り、注文管理、リスク管理、照合（reconciler）
- Monitoring:
  - system monitor（CPU/メモリ/ディスク、Execution プロセス存在確認、データ鮮度）
  - trade monitor（注文滞留・約定異常の検出）
  - risk monitor（ドローダウン・ポジション上限監視）
  - Kill Switch：閾値超過時に data/kill.flag を書き込み Execution を止める
  - 永続化：SQLite（monitoring DB）へのログ保存
- Portfolio construction:
  - 候補選定、等重／スコア加重、リスクベースの数量計算、セクターキャップ、レジーム乗数
- Research:
  - DuckDB を利用したファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI:
  - ニュースを LLM（OpenAI）でセンチメント評価して ai_scores に書き込み
  - マクロニュース + ETF MA200 による市場レジーム判定（score_regime）
- ツール:
  - Paper Trading 検証レポート生成（paper_verification_report）

## 必要条件（主な Python パッケージ）
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config ファイル検証を行う場合）
- （その他、ブローカークライアント等の実装に依存するパッケージがある可能性）

インストール例（仮）:
pip install duckdb psutil openai PyYAML

※ 実際の requirements.txt がある場合はそちらを参照してください。

## セットアップ手順
1. リポジトリをクローン / 展開
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install -r requirements.txt  （存在する場合）
   - または個別インストール: pip install duckdb psutil openai PyYAML
4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env ファイルを手動作成（下記の最小例を参照）
   - 自動ロードはデフォルトで有効（プロジェクトルートの .env / .env.local を読み込み）
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict オプションで警告をエラー扱いにできます

最小の .env 例（必須項目）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

環境変数の一覧は下の「環境変数」を参照してください。

## 使い方（起動・操作）
主な起動コマンド（プロジェクトルートで実行）:

- ExecutionEngine を起動:
  - python -m kabusys.run_execution
  - 動作: Settings に従って SQLite / DuckDB を接続。paper_trading モードなら専用 DB を使用。
  - 停止方法: 実行中に data/stop_requested.flag を作成するとエンジンが停止します（run_execution は起動時・ループ中に _STOP_FLAG を監視）。

- Monitoring を起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定（デフォルト 60）
  - 監視は Settings.env に関わらず本番 sqlite_path（data/monitoring.db）を使用
  - 停止方法: data/stop_requested.flag を作成すると停止

- 環境設定ウィザード:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数を上書き）

- AI モジュールの利用（プログラムから）:
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key=...)  # conn は duckdb connection
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key=...)

  OpenAI API キーは OPENAI_API_KEY または関数引数 api_key から渡します。

ログ出力:
- logs/<app_name>.log に日次ローテーションで出力（logs/ ディレクトリは自動作成）
- コンソールは stdout に出力（kabusys.utils.logging_setup.setup_logging）

PID / フラグファイル:
- 実行時に data/execution.pid（デフォルト）に PID を書く設計
- 停止リクエスト用フラグ: data/stop_requested.flag（run_execution / run_monitoring が監視）
- Kill Switch: data/kill.flag（KillSwitch が書き込む。Execution 側はこれを参照して停止する想定）

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

推奨 / オプション（抜粋）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading モードの SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 本番アラート用（任意）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 本番での自動 kill.flag クリア（"0" 推奨）

自動 .env 読み込み:
- プロジェクトルートの .env と .env.local を自動で読み込みます（OS 環境変数は上書きされません）
- 自動読み込み停止: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

## 停止・Kill 操作
- 強制停止（プロセスレベル）: システム信号等
- 優雅な停止（内部フラグ）:
  - data/stop_requested.flag を作成 → run_monitoring / run_execution のループが検知して終了
  - KillSwitch による停止: 監視が閾値を超えた場合、data/kill.flag が生成され、ExecutionEngine 側で参照して停止される想定
- Kill flag の自動クリアは KILL_FLAG_CLEAR_ON_START=1 で有効（本番では推奨しない）

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主なファイル／ディレクトリ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理
  - config_setup.py               — .env 対話ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py            — SQLite 永続化レイヤ
    - system_monitor.py           — システム状態チェック
    - trade_monitor.py            — 注文関連監視（参照されるが抜粋未表示）
    - risk_monitor.py             — DD/ポジション上限監視
    - kill_switch.py              — kill.flag 書込みロジック
    - monitoring_engine.py        — 監視ループのオーケストレーション
    - alert_manager.py            — アラート送信（抜粋未表示）
  - execution/                     — Execution 関連（Engine, BrokerFactory, OrderManager 等）
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py        — 候補選定・重み計算
    - position_sizing.py          — 株数決定・投下資金管理
    - risk_adjustment.py          — セクター上限・レジーム乗数
  - research/
    - factor_research.py         — Momentum/Value/Volatility 等
    - feature_exploration.py     — 将来リターン / IC / summary
  - ai/
    - news_nlp.py                — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         — マーケットレジーム検出（MA200 + LLM）
  - data/                         — 実行時に生成される DB / flag / pid / logs 等（リポジトリに含めないこと）

（上記は抜粋です。実装ファイルはリポジトリに応じて増減します。）

## 開発・運用上の注意
- .env は機密情報を含むため Git にコミットしないでください（config_setup.py でも注意文が書かれています）。
- paper_trading モードは本番 DB と分離されますが、設定ミスに注意してください（validate_config でチェック推奨）。
- OpenAI API を利用する機能は API コストが発生します。レートリミットや失敗時のフォールバック実装（多くは安全側フォールバック）に注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります（setup_logging の挙動）。

---

このREADME はコードベースの主要部分を要約したものです。各モジュールの詳細な使用法・設計方針は該当ファイルのドキュメント文字列（docstring）を参照してください。追加で README に含めたい情報（例: CI/CD、デプロイ手順、詳しい設定例など）があれば教えてください。