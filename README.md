README
======

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
本リポジトリは以下の主要コンポーネントを含みます:

- ExecutionEngine（発注エンジン） — 実際の発注／ペーパートレードを実行  
- Monitoring（監視） — プロセス・システム状態、注文ログ、リスク監視、Kill Switch  
- Portfolio（ポートフォリオ構築） — 銘柄選定・重み付け・ポジションサイジング  
- Research（リサーチ） — ファクター計算・特徴量探索・IC 計算などの分析機能  
- AI（ニュース NLP / レジーム判定） — OpenAI を利用したニュースセンチメント評価と市場レジーム判定  
- Utils / Tools — ロギング設定、プロセス優先度、CLI ユーティリティ（.env ウィザード、設定検証、レポート生成 等）

主な特徴
--------
- 実運用を意識した設計（本番 / ペーパーの DB 分離、Kill Switch、ロギング、PID 管理）  
- DuckDB（分析テーブル）と SQLite（監視・発注ログ）の併用  
- OpenAI を用いたニュースセンチメント集約（AI モジュールは API キー必須）  
- PortfolioConstruction / Risk 制御に基づく純粋関数群（ユニットテストしやすい）  
- 監視ループとアラート送出（LINE 連携のためのトークンを環境変数で設定可能）  
- ペーパートレード検証レポート生成ツール

セットアップ手順
----------------
0. 前提
   - Python 3.9+（コードは型ヒントを使用）
   - 必要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定 YAML 検証時に必要）
   - 仮想環境を推奨（venv / pipenv / poetry 等）

1. 仮想環境作成・依存インストール（例）
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

2. .env の準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で .env を作成する場合は .env.example を参考に必要な環境変数を設定してください。
   - 自動ロード:
     - プロジェクトルートに .env / .env.local があると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

3. 必須環境変数
   - 最低限設定が必須なもの:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要な設定（代表）:
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY: AI 機能を使う場合に必須
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
     - LOG_LEVEL, LOG_DIR, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方
------
エントリポイントはモジュールとして実行します。代表的なコマンドは次のとおり。

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV に従います:
    - paper_trading: MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - live / development: Settings の sqlite_path を使用
  - 停止制御:
    - data/stop_requested.flag を作成するとループが検知して停止します
    - data/execution.pid に PID が書き出されます

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔:
    - デフォルト 60 秒
    - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（本番 DB）を常に参照します（監視は実行環境に依らず本番 DB を利用）
  - 監視を停止するには data/stop_requested.flag を作成

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH

運用上のポイント
- ログ
  - logs/<app_name>.log に日次ローテーションでログが出力されます（TimedRotatingFileHandler、30日保持）
  - setup_logging() でルートロガーを統一設定
- Kill Switch
  - kill.flag（Settings.kill_flag_path デフォルト data/kill.flag）を書き込むことで ExecutionEngine に停止シグナルを送れます
  - KillSwitch はリスク監視や手動オペレーションで利用
- PID / stop フラグ
  - run_execution は data/execution.pid を使用/作成
  - stop_requested.flag（data/stop_requested.flag）は run_* スクリプトがループ中に停止を検知するために使います
- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し本番 DB と完全分離します
  - PAPER_FILL_MODE（instant/partial/never/reject）で模擬約定動作を制御

ディレクトリ構成
----------------
（ src/kabusys 配下の主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI で銘柄ごとにセンチメント）
    - regime_detector.py       — レジーム判定（MA + マクロセンチメント合成）
  - monitoring/
    - monitoring_db.py        — SQLite スキーマ初期化と読み書きラッパー
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 発注ログ監視（滞留注文・異常約定検出）※実装あり
    - risk_monitor.py         — ドローダウン / ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — アラート通知（LINE など）※実装あり
    - monitoring_engine.py    — 各 Monitor を束ねるループ
  - execution/
    - broker_factory.py       — ブローカークライアント生成（実ブローカ or Mock）
    - execution_engine.py     — 発注エンジン本体
    - order_manager.py        — 注文管理
    - order_repository.py     — DB 操作（orders）
    - reconciler.py           — 発注結果の突合せ
    - risk_manager.py         — リスク管理ロジック
  - portfolio/
    - portfolio_builder.py    — 候補選定、重み計算
    - position_sizing.py      — 株数決定・制限・単元丸め
    - risk_adjustment.py      — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py      — Momentum / Value / Volatility 等のファクター計算（DuckDB）
    - feature_exploration.py  — 将来リターン計算、IC、統計サマリ
  - monitoring/               — （上記）
  - utils/
    - logging_setup.py        — ログの統一設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/ (実行時に生成)
    - monitoring.db (SQLITE_PATH デフォルト)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH デフォルト)
    - kabusys.duckdb (DUCKDB_PATH デフォルト)
    - kill.flag, stop_requested.flag, execution.pid などの制御ファイル

追加情報 / 注意事項
-------------------
- OpenAI を利用する機能（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）が必須です。API 利用料に注意してください。  
- Settings や validate_config によって許容される環境値・既定値が定義されています。KABUSYS_ENV は development / paper_trading / live のいずれかでなければなりません。  
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。  
- 実運用（KABUSYS_ENV=live）の場合は KILL_FLAG_CLEAR_ON_START を 0 のままにすることを推奨します（本番で自動クリアは危険）。  
- DB スキーマの初期化やマイグレーションロジックは monitoring_db.init_monitoring_db に含まれています。

貢献 / 開発
-----------
- 新しい依存を追加する場合は README に追記し、requirements.txt / pyproject.toml を更新してください。  
- 単体テストが書ける設計（副作用を小さくする純粋関数群）になっています。ユニットテスト追加を歓迎します。

お問い合わせ
-----------
実装や設計に関する質問があればリポジトリの Issue を作成してください。

---  
以上。README に記載してほしい追加の項目（例: 実際のコマンド例、環境変数の例 .env テンプレート、依存バージョンなど）があれば教えてください。