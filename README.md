# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量フレームワークです。本コードベースは以下の主な機能を含みます。

- 実行エンジン（ExecutionEngine）と監視サービス（Monitoring）
- Paper Trading（ペーパートレード）モードの分離実装（実DBと分離）
- ポートフォリオ構築／ポジションサイズ計算／リスク調整の純粋関数群
- ファクター計算・特徴量探索（研究用 DuckDB ベース）
- ニュースの NLP スコアリング / レジーム判定（OpenAI を利用）
- 監視 DB（SQLite）に対する永続化層とリスク監視ロジック
- 開発用の設定ウィザード・検証スクリプト・検証レポートジェネレータ

主要な設計方針
- 実行（発注）関連は環境変数 KABUSYS_ENV によって paper_trading / live / development を切り替え可能。paper_trading 時は MockBroker を使い、paper 用 DB に記録される（本番 DB と分離）。
- DuckDB は分析（研究・AI）用途に使用。prices_daily / raw_financials 等のテーブルを前提とした処理を行う。
- OpenAI を使う機能（ニュース NLP / レジーム判定）は API キーとネットワーク接続が必要。失敗時はフェイルセーフで継続する設計。

機能一覧
---
- 実行関連
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて本番 or Paper Trading）
  - 注文管理・リスク管理・照合（OrderManager, RiskManager, Reconciler 等）

- 監視関連
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - MonitoringEngine: System / Trade / Risk Monitor を束ね通知・Kill Switch を評価
  - monitoring_db: 監視用 SQLite のスキーマと操作ラッパー

- ポートフォリオ構築（純粋関数）
  - 選定: select_candidates
  - ウェイト計算: calc_equal_weights / calc_score_weights
  - リスク調整: apply_sector_cap / calc_regime_multiplier
  - ポジションサイズ: calc_position_sizes

- 研究（DuckDB を利用）
  - factor_research: momentum / volatility / value ファクター計算
  - feature_exploration: forward returns, IC 計算, 統計サマリ

- AI
  - news_nlp: raw_news を集約して OpenAI API で銘柄別センチメントを算出・ai_scores に保存
  - regime_detector: ETF (1321) の ma200 とマクロニュースの LLM センチメントを合成して market_regime を判定

- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 設定検証 CLI（--strict オプションあり）
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成

セットアップ手順
---
前提
- Python 3.9+（型ヒントに一部 Union 型等を利用）
- SQLite（標準で利用可能）
- DuckDB（Python パッケージ）
- psutil（プロセス優先度・CPU情報取得）
- OpenAI SDK（AI 機能を使う場合）
- PyYAML（config 検証で YAML を検証する場合に任意で使用）

推奨インストール例（仮の requirements が無い場合の例）
```
pip install duckdb psutil openai
# 任意:
pip install pyyaml
```

環境変数（重要）
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 推奨 / オプション（例）
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用監視 DB（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR（デフォルト: INFO）
  - LOG_DIR: ログ保存先（デフォルト: logs/）
  - OPENAI_API_KEY: OpenAI API を利用する場合に必要
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番での通知設定（任意）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

.env の作成
1. 対話ウィザードを使う（推奨）
   python -m kabusys.config_setup

2. 作成後、設定検証
   python -m kabusys.validate_config
   # 警告もエラー扱いにする場合:
   python -m kabusys.validate_config --strict

初期ディレクトリ作成（必要に応じて）
- data/: DB・PID・フラグファイル等を格納（実行時に自動作成されることが多い）
- logs/: ログ出力（setup_logging が自動作成を試みる）

使い方（起動コマンド例）
---
- 実行エンジン起動（Execution）
  - Paper Trading（KABUSYS_ENV=paper_trading を .env で設定）
  - 実行:
    python -m kabusys.run_execution
  - 動作:
    - プロセス優先度を高に設定
    - sqlite / duckdb に接続
    - BrokerClientFactory に従ってブローカークライアントを生成（paper_trading 時は Mock）
    - ExecutionEngine を別スレッドで run_session し、stop フラグ（data/stop_requested.flag）を監視

- 監視プロセス起動（Monitoring）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - Monitoring は KABUSYS_ENV に関わらず設定された sqlite_path を使用して監視情報を永続化

- 設定ウィザード
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  # 警告を FAIL 扱いにする
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB は環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能

運用に関するポイント
- Kill Switch / 停止フラグ
  - KillSwitch は data/kill.flag を書き込むことで ExecutionEngine に停止を促す仕組みです（監視側が条件を満たすと書き込む）。
  - run_execution/run_monitoring は data/stop_requested.flag を見てシャットダウンします（プロセスの即時停止用）。
  - KILL_FLAG_CLEAR_ON_START=1 にすると ExecutionEngine 起動時に kill.flag を自動クリアしますが、本番では 0 を推奨します。

- DB の分離
  - paper_trading モードでは専用の PAPER_TRADING_SQLITE_PATH を使用し、本番の monitoring.db と完全に分離されるようになっています。

- ログ
  - ログは stdout とファイル（logs/<app_name>.log）に出力されます。ログディレクトリの作成に失敗しても stdout のみで継続します。

- OpenAI
  - news_nlp / regime_detector では OPENAI_API_KEY が必要です。API 呼び出しはリトライ・フェイルセーフを備えていますが、API 使用はコストやレートに注意してください。
  - news_nlp は gpt-4o-mini を想定し JSON モードでレスポンスを受け取ります。

ディレクトリ構成（主要ファイル）
---
src/
  kabusys/
    __init__.py
    config.py                # 環境変数・自動 .env ロード・Settings
    config_setup.py          # .env 対話式ウィザード
    validate_config.py       # 設定検証 CLI
    run_execution.py         # ExecutionEngine 起動スクリプト
    run_monitoring.py        # SystemMonitor ポーリングループ起動スクリプト

    utils/
      logging_setup.py       # ログ設定ユーティリティ
      process_priority.py    # プロセス優先度 / CPU affinity
      __init__.py

    execution/               # 実行関連モジュール（OrderManager, ExecutionEngine 等）
      ... (未掲載のファイル)

    monitoring/
      monitoring_db.py       # SQLite テーブル初期化 & 操作ラッパー
      system_monitor.py      # システム・データ鮮度監視
      risk_monitor.py        # ドローダウン / ポジション上限監視
      trade_monitor.py       # (概要) 注文の滞留／約定異常検出（ファイル内参照）
      alert_manager.py       # (概要) 通知送信（LINE 等）
      kill_switch.py         # data/kill.flag を扱う
      monitoring_engine.py   # 各 Monitor を束ねる

    portfolio/
      portfolio_builder.py   # 候補選定 / 重み計算
      risk_adjustment.py     # セクターキャップ / レジーム乗数
      position_sizing.py     # 株数決定・集約キャップ
      __init__.py

    research/
      factor_research.py     # Momentum / Volatility / Value
      feature_exploration.py # forward returns / IC / summary
      __init__.py

    ai/
      news_nlp.py            # ニュースの LLM スコアリング
      regime_detector.py     # マクロ+ETF でレジーム判定
      __init__.py

    data/                    # 実行時に作成されることが多い（DB, PID, flags）
      (例) monitoring.db
      (例) paper_trading.db
      execution.pid
      kill.flag
      stop_requested.flag

    tools/
      paper_verification_report.py
      __init__.py

サンプル .env（最小）
---
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
# OPENAI_API_KEY=sk-...   # AI 機能を使う場合に設定

開発・テストのヒント
- 自動 .env ロードは config.py によりプロジェクトルートの .env / .env.local を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- validate_config.py は PyYAML があれば config/*.yaml の構文チェックも行います（未インストールならスキップで警告）。
- run_execution/run_monitoring は最初にプロセス優先度を上げようとします（psutil による; 権限がない場合は警告）。
- テスト時は AI 呼び出し部分（news_nlp._call_openai_api など）をモックすることを推奨します（コード内に差し替え用の注釈あり）。

ライセンス・貢献
---
（この README は与えられたコードベースから生成されています。ライセンス表記や貢献ガイドはリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください。存在しない場合はプロジェクトポリシーに従って追記してください。）

以上がプロジェクトの概要と基本的な使い方です。必要であれば、各モジュール（ExecutionEngine、OrderManager、AlertManager 等）の詳細な使用例・API ドキュメントも作成できます。どの部分のドキュメントを優先して欲しいか教えてください。