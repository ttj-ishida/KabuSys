README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコアライブラリ群です。本リポジトリは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution）
- システム監視（SystemMonitor）と監視ループ（run_monitoring）
- 監視ログの永続化（SQLite ベース）
- ポートフォリオ構築・ポジションサイズ計算の純粋関数群（portfolio パッケージ）
- ファクター計算・リサーチ用ユーティリティ（research パッケージ）
- ニュース NLP（OpenAI 連携）による銘柄センチメント評価（ai パッケージ）
- モニタリング・キルスイッチ、アラート管理、リスク監視
- 開発用ユーティリティ（.env ウィザード、設定検証、レポート生成など）

設計方針の抜粋
- 実マーケットでの発注は KABUSYS_ENV により切り替え（paper_trading / live / development）。
- DB は DuckDB（分析用）と SQLite（監視・履歴）を併用。
- 多くの処理は副作用を持たない純粋関数で実装され、テスト容易性を重視。
- OpenAI を使う処理は失敗時にフォールバックするようフェイルセーフ設計。

主な機能一覧
---------------
- 実行 / 監視
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合は MockBroker を使い paper DB に記録）
  - run_monitoring.py: SystemMonitor をポーリングして system_status / risk_logs / trade_logs 等を記録
- 設定管理
  - config_setup.py: .env の対話式ウィザードで初期設定を作成
  - validate_config.py: .env と config/*.yaml の起動前チェック
  - Settings（kabusys.config）: 環境変数ラッパーと既定値
- 監視関連
  - monitoring/monitoring_db.py: SQLite テーブルの作成と CRUD ヘルパー
  - monitoring/system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py: 各種監視ロジック
  - monitoring/kill_switch.py: ドローダウン等に応じて data/kill.flag を書き込む Kill Switch
- ポートフォリオ構築（純粋関数）
  - portfolio/select_candidates, calc_equal_weights, calc_score_weights
  - portfolio/calc_position_sizes（リスクベース／等配分等）
  - portfolio/apply_sector_cap, calc_regime_multiplier
- リサーチ
  - research/factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB を想定）
  - research/feature_exploration.py: 将来リターン計算・IC 等
- AI（OpenAI 連携）
  - ai/news_nlp.py: ニュース記事を OpenAI に投げて銘柄ごとにスコアリング → ai_scores へ書込み
  - ai/regime_detector.py: ETF (1321) 等の MA とマクロ記事センチメントを合成して market_regime を決定
- ツール
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポート生成

前提 / 必要環境
---------------
- 推奨 Python: 3.10+（typing の新構文を利用）
- 推奨パッケージ（requirements.txt があればそちらを利用してください）:
  - duckdb
  - psutil
  - openai
  - pyyaml（config の YAML 検証を行う場合）
- SQLite は標準ライブラリの sqlite3 を使用

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリへ移動します。
   - git clone ... && cd <repo>

2. 仮想環境を作成・有効化して依存をインストールします（例: venv）。
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がある場合:
   - pip install -r requirements.txt

3. .env ファイルの作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードで J-Quants トークン、kabu API パスワード、KABUSYS_ENV 等を設定します。
     - 生成された .env をプロジェクトルートに保存してください（.env は Git にコミットしないこと）。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合は --strict を付けると警告があると exit(1) になります。

主要環境変数（主なもの）
-----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading 時）
- PAPER_FILL_MODE: paper_trading の約定モード（instant | partial | never | reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector が必要な場合）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag をクリアするか（"1"でクリア）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト: 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID ファイル / kill flag のパス（Settings でデフォルトあり）

使い方（コマンド例）
-------------------
- .env を対話式に作る
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（デーモン化は systemd / supervisor 等で管理）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading のときは paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
    - 起動前に data/stop_requested.flag が存在すると起動をスキップします。
    - エンジンは data/execution.pid を作成します。

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（デフォルト 60）。
    - 監視は常に本番用 sqlite_path を使います（KABUSYS_ENV に依存しない）。
    - 停止は data/stop_requested.flag を作成すると検出してループを終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で別ファイルを指定可能。

- AI スコア／レジーム判定の利用例（スクリプト等から呼び出す）
  - kabusys.ai.score_news(duckdb_conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

ログ出力
--------
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存されます（デフォルト保存期間 30 日）。
- 実行時に setup_logging(app_name="execution" や "monitoring") が呼ばれ、コンソール出力は stdout へ行きます。

停止フラグ / キルスイッチ
------------------------
- stop_requested.flag: run_execution / run_monitoring がループを抜けるための「停止リクエスト」ファイル（data/stop_requested.flag）
- kill.flag: KillSwitch が条件を満たした場合に作成され、ExecutionEngine に停止を促す（設定により起動時に自動クリアされることあり）
- Settings.kill_flag_clear_on_start が "1" のとき、起動時に kill.flag を削除する設定です（本番では無効推奨）。

DB とマイグレーション
--------------------
- monitoring_db.init_monitoring_db() は起動時に呼ばれ、必要なテーブルやインデックスを冪等に作成します。スキーマ変更（カラム追加）は一部自動で ALTER TABLE を行います。
- DuckDB は分析用途。prices_daily / raw_financials / raw_news 等のテーブルを想定しており、research および ai モジュールで参照されます。

ディレクトリ構成 (抜粋)
-----------------------
以下は主要なファイル・パスの概観（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                # Settings / .env 自動ロード
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (参照される実装)
    - alert_manager.py (参照される実装)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                # ExecutionEngine 周りの実装（BrokerFactory, Engine 等）
    - ... (別ファイル群)
  - data/ (runtime)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kill.flag, stop_requested.flag, execution.pid など

開発者向けメモ
---------------
- Settings モジュールは起動時に自動でプロジェクトルートの .env を読み込みます。自動読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Logging は setup_logging() を通して統一しており、既存ハンドラがある場合は一旦クリアされます（重複出力防止）。
- OpenAI 連携関係は外部 API 呼出しで失敗し得るため各所でリトライとフェイルオープン処理を実装しています。テスト時は API 呼び出し関数をモックしてください（各モジュールに差し替えポイントあり）。
- DuckDB の SQL は直接文字列で組み立てられている箇所があり、適切なパラメータバインドを使っていることに留意してください。

よくある操作例（サンプル）
-------------------------
- 開発用ローカル起動（ペーパートレード）
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.config_setup   # .env を作成
  - python -m kabusys.validate_config
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring

- Paper トレード結果の検証
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）

問い合わせ / 貢献
-----------------
バグ修正・機能追加のプルリクエスト歓迎です。大きな設計変更を行う場合は事前に Issue を立てて相談してください。

以上。README に記載してほしい追加情報（実行例、依存の固定バージョン、systemd ユニット例など）があれば教えてください。必要に応じてサンプルを追記します。