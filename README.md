README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
本リポジトリには以下の主要機能を備えたモジュール群が含まれます:

- 発注実行エンジン（ExecutionEngine） — live / paper_trading をサポート
- 監視サブシステム（Monitoring） — システム状態・注文挙動・リスク監視、Kill Switch
- ポートフォリオ構築ロジック（選定・重み付け・ポジションサイズ）
- リサーチ系（ファクター計算・特徴量解析）
- AI 支援（ニュース NLP / 市場レジーム判定：OpenAI を利用）
- 運用ユーティリティ（.env ウィザード / 設定検証 / レポート生成 等）

特徴
----
- 開発 / ペーパー取引 / 本番（KABUSYS_ENV）を環境別に切替可能
- paper_trading 時は MockBroker を使い、発注履歴を本番 DB と分離
- DuckDB（分析）と SQLite（監視・発注ログ）を併用
- ログはコンソール＋日次ローテートファイル出力（logs/<app>.log）
- Kill Switch（data/kill.flag）により自動で Execution を停止可能
- OpenAI と連携したニュースセンチメントやレジーム判定（API Key 必要）
- 各種防御（リトライ、フェイルセーフ、データ鮮度チェック、リスクアラート）

セットアップ手順
--------------
前提:
- Python 3.9+（タイプヒントなどの構文を利用）
- 仮想環境の使用を推奨（venv / pipenv / poetry 等）

1. リポジトリをチェックアウトし、仮想環境を作成・有効化
   - 例:
     - git clone ...
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 最低限の依存（プロジェクトに合わせて追加してください）:
     - duckdb
     - psutil
     - openai  (AI 機能を使う場合)
     - PyYAML （config 検証で YAML チェックを行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （本リポジトリに requirements.txt が無い場合は上記を手動で管理してください）

3. 環境変数設定
   - 推奨: .env を用意（ルートに .env）
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - 重要な環境変数（必須）
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用
     - KABU_API_PASSWORD — kabuステーション API 用
   - 任意 / 運用関連
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
     - OPENAI_API_KEY: OpenAI を使う機能で必要
     - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いする strict モード:
     - python -m kabusys.validate_config --strict

使い方
------
主要なスクリプト／モジュールの使い方（プロジェクトルートから実行）:

- .env の初期化（対話式）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も exit 1 扱いになります

- 監視ループ起動（Monitoring）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60）
  - python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するか Ctrl+C

- 実行エンジン起動（ExecutionEngine）
  - KABUSYS_ENV に応じて paper_trading（モック）／live（実際発注）を切替
  - python -m kabusys.run_execution
  - paper_trading の DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で変更可）
  - 停止: data/stop_requested.flag を作成するか Kill Switch により停止

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（省略時は PAPER_TRADING_SQLITE_PATH 環境変数 または data/paper_trading.db）

- AI / NLP 機能
  - OpenAI API Key が必要（OPENAI_API_KEY または関数引数）
  - ニュースセンチメント:
    - kabusys.ai.score_news (API を呼ぶ Pythonコード経由)
  - 市場レジーム判定:
    - kabusys.ai.regime_detector.score_regime (DB 接続・日付・API Key 必須)

運用に関する注意点
- paper_trading モードは本番 DB と物理的に分離されます（PAPER_TRADING_SQLITE_PATH）。
- Kill Switch:
  - KillSwitch は monitoring の判定結果から data/kill.flag を書き込み、
    ExecutionEngine はそれを検知して停止します。Kill flag は Settings.kill_flag_path で制御。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 にするのは危険（デフォルト 0）。
- ログ:
  - デフォルト logs/ ディレクトリに app ごとにログファイルを保存（logs/execution.log, logs/monitoring.log 等）
  - LOG_DIR 環境変数または setup_logging の引数で変更可能
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_* スクリプトは安全に停止します
  - run_execution は data/execution.pid を利用（PID 管理）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要モジュールとファイルの概要です。
（実際のリポジトリではこの下にさらに細かいファイル群があります）

- src/
  - kabusys/
    - __init__.py               — パッケージ定義（バージョン等）
    - config.py                 — 環境変数 / 設定読み込みと Settings クラス
    - config_setup.py           — .env 対話式ウィザード
    - validate_config.py        — 設定検証 CLI
    - run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py        — ログセットアップユーティリティ
      - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py        — SQLite 監視 DB 初期化・アクセス層
      - system_monitor.py       — システム状態・データ鮮度監視
      - trade_monitor.py        — 注文関連の監視（滞留注文・異常約定等）※実装ファイルあり
      - risk_monitor.py         — ドローダウン / ポジション上限監視
      - kill_switch.py          — Kill Switch ロジック
      - monitoring_engine.py    — 各モニタを束ねるエンジン
      - alert_manager.py        — 通知管理（LINE 等）※実装ファイルあり
    - execution/
      - execution_engine.py     — 実行エンジン本体（セッション管理等）
      - broker_factory.py       — Broker クライアント生成
      - order_manager.py        — 注文管理
      - order_repository.py     — 注文永続化
      - reconciler.py           — 注文整合性チェック
      - risk_manager.py         — 発注前リスクチェック
    - portfolio/
      - portfolio_builder.py    — 候補選定・重み計算
      - position_sizing.py      — 株数計算・上限/スケール調整
      - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - research/
      - factor_research.py      — ファクター計算（momentum/value/volatility 等）
      - feature_exploration.py  — 将来リターン & IC 計測、統計サマリー
    - ai/
      - news_nlp.py             — ニュースからセンチメントを生成して ai_scores に保存
      - regime_detector.py      — マクロ + ma200 で市場レジーム判定
    - tools/
      - paper_verification_report.py — Paper Trading の検証レポート生成スクリプト

環境変数の主な項目（まとめ）
-----------------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / ログ / DB
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
  - DUCKDB_PATH — デフォルト data/kabusys.duckdb
  - SQLITE_PATH — デフォルト data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
  - LOG_LEVEL — DEBUG/INFO/...
  - LOG_DIR — ログ保存先

- AI
  - OPENAI_API_KEY — OpenAI 機能を利用する場合に必須

- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など（config.Settings 経由）

補足 / 開発メモ
--------------
- DuckDB と SQLite を併用しており、研究処理は DuckDB、監視＆発注ログは SQLite に格納されます。
- OpenAI 関連はネットワークやコストに依存するため、開発や CI ではモックを利用することを推奨します。
- .env は絶対にリポジトリへコミットしないでください（機密情報含む）。
- config/*.yaml のサンプルや生成スクリプトが参照される箇所があります（存在しない場合は警告）。必要に応じて scripts/generate_config.py 等で生成してください。

ライセンス／作者
----------------
（ここにライセンス情報や作者・連絡先を追記してください）

以上。必要があれば、README に記載するコマンド例や .env のサンプルテンプレートを追記します。どの情報を詳細化しますか？