KabuSys — 日本株自動売買システム
================================

バージョン: 0.1.0

このリポジトリは日本株向けの自動売買システム（研究・ポートフォリオ構築・発注エンジン・監視・AI 補助機能）を収めたコードベースです。各モジュールは独立性を重視して設計されており、Paper Trading（モックブローカー）と Live（実際の発注）の二形態で動作します。

主な特徴
--------

- ExecutionEngine（発注エンジン）
  - 本番 / ペーパートレード（MockBrokerClient）を切り替え可能
  - リスク管理（ポジション上限、ドローダウン監視等）
  - 注文履歴の永続化（SQLite）

- Monitoring（監視）
  - システムリソース監視（CPU, メモリ, ディスク）
  - データ鮮度チェック（DuckDB の prices_daily 等）
  - トレード監視（遅延注文・異常約定検出）
  - Kill Switch（条件に応じた停止フラグ生成）
  - ログと監視結果の永続化（SQLite）

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - 候補選定、等金額/スコア加重配分、リスクベース配分
  - セクター制約・レジーム補正

- Research（ファクター計算・特徴量解析）
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン・IC 計算・統計サマリ

- AI（ニュースセンチメント・レジーム判定）
  - OpenAI を利用したニュースセンチメント評価（ai_scores へ書込）
  - マクロニュース + ETF MA を組み合わせた市場レジーム判定

- ユーティリティ
  - 環境設定ウィザード（.env 生成）
  - 設定検証 CLI（config/*.yaml や必須環境変数のチェック）
  - ログ設定・プロセス優先度設定ユーティリティ
  - Paper Trading 検証レポート生成ツール

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone ... (省略)

2. Python 環境（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要最低限の主要パッケージ:
     - duckdb
     - psutil
     - openai
     - pyyaml (設定検証で YAML を検査する場合)
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt があればそれを使ってください: pip install -r requirements.txt）

4. 環境変数の初期化（.env）
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照）
   - 自動ロード:
     - 起動時、プロジェクトルートに .env / .env.local があれば自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）

5. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗として扱う）:
     - python -m kabusys.validate_config --strict

6. データディレクトリ作成
   - data/ と logs/ は自動生成されることがありますが、明示的に作る場合:
     - mkdir -p data logs

主要な環境変数（要点）
---------------------

- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live

- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckb)
  - SQLITE_PATH (監視 DB、デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)

- Paper Trading 挙動
  - PAPER_FILL_MODE: instant | partial | never | reject

- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ保存先

- AI
  - OPENAI_API_KEY: OpenAI API キー（ニューススコア / レジーム判定に必要）

- その他
  - KILL_FLAG_CLEAR_ON_START=1: 起動時に kill.flag を自動クリア（本番では 0 推奨）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

使い方（主なエントリポイント）
-------------------------------

- 環境ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db へ記録
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了
  - 実行中に data/stop_requested.flag を作成するとエンジン停止を試みる
  - 実行中は実行 PID を data/execution.pid に書き込み（設定に依存）

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き（秒）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを記録
  - data/stop_requested.flag を検知するとループを終了

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定可能）
  - 注文成功率（fill_rate）やレイテンシ P95、稼働率などを集計して PASS/FAIL を判定

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続、target_date（date オブジェクト）、OpenAI API キー（省略可）
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- ライブラリ関数の利用例
  - ポートフォリオ組成:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - 研究用ファクター:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value

動作のポイント / 注意事項
------------------------

- .env 自動読み込み
  - プロジェクトルートを .git または pyproject.toml で検出し、.env / .env.local を自動で読み込みます
  - テスト等で自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

- Monitoring の DB アクセス
  - run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使います（監視は常に本番 DB を参照する設計）

- Kill Switch / stop flag
  - KillSwitch（条件による自動停止）は data/kill.flag を書き込みます。ExecutionEngine は stop フラグ（data/stop_requested.flag）で安全停止します。

- ログ出力
  - kabusys.utils.logging_setup.setup_logging を起動コード（run_execution/run_monitoring 等）から呼び出して一貫したログを生成します。ログは stdout と logs/<app_name>.log に日次ローテートで出力されます。

- AI 呼び出し
  - OpenAI の呼び出し部はリトライやバックオフ等のフォールトトレラントな実装を含みますが、API キーの管理・レート制限・コストに注意してください。

ディレクトリ構成（主なファイルと説明）
------------------------------------

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定取得ユーティリティ（.env 自動ロード含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores を作成
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py       — SQLite 監視テーブル初期化・永続化層
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — 発注監視（trade_logs 参照） ※実装あり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の生成 / 管理
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - alert_manager.py       — アラート送信（LINE 等） ※実装あり

  - execution/
    - execution_engine.py    — 発注エンジン本体（EngineConfig や run_session）
    - broker_factory.py      — BrokerClient の生成（Mock/実ブローカー切替）
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

  - data/
    - pipeline.py             — DuckDB データパイプライン（get_last_price_date 等）
    - stats.py                — Zスコア正規化等（research 用ユーティリティ）

  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

  - utils/
    - logging_setup.py        — ログ初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ

- data/                      — 実行時に使用する SQLite / PID / フラグ等（プロジェクトルート）
- logs/                      — ログファイル置き場（デフォルト）

追加情報 / 開発メモ
------------------

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等で必要なテーブルとインデックスを作成し、既存 DB に対する簡単なカラム追加マイグレーションも行います。

- テスト容易性
  - OpenAI 呼び出しは内部関数を patch してモック可能（ユニットテスト用に設計）
  - config モジュールはプロジェクトルート探索を行うため、CWD に依存しない挙動を意図しています

- 安全機構
  - Execution / Monitoring 起動時にプロセス優先度を設定（set_process_priority）
  - 監視は冗長性を意識しており、DB 接続/SQL の失敗時はフェイルオープンで継続する箇所が多く実装されています

連絡 / 貢献
-----------

バグ報告や改善提案は issue を立ててください。CLI・ドキュメントの改善、テスト追加、外部ブローカー実装などの貢献歓迎します。

以上。必要なら README に追記する内容（例: systemd ユニットファイル例、Dockerfile、詳細な設定項目一覧など）を教えてください。