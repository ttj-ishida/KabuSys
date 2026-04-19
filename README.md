README
=====

概要
----
KabuSys は日本株向けの自動売買・研究・監視を目的とした軽量フレームワークです。
このリポジトリは、発注エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、
ポートフォリオ構築・ポジションサイジング、ファクター計算・研究ツール、
およびニュース NLP / レジーム判定などの AI 補助モジュールを含みます。

主な設計方針
- 本番／ペーパートレードを環境変数で切り替え可能（KABUSYS_ENV）
- DuckDB を使った分析用データ、SQLite を使った運用ログの永続化
- OpenAI API を利用する NLP 処理は外部 API キーに依存（フェイルセーフ設計）
- 各サブシステムは疎結合でテストしやすい純粋関数群を多用

機能一覧
--------
- Execution（run_execution.py）
  - ブローカークライアントの生成（実口座または Mock：KABUSYS_ENV=paper_trading）
  - Order 管理、Risk 管理、Reconciler、ExecutionEngine の起動
  - paper_trading の場合は data/paper_trading.db に記録して本番 DB と分離

- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視
  - kill.flag による ExecutionEngine 強制停止（Kill Switch）
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整可能（デフォルト 60 秒）

- データベース初期化
  - monitoring 用 SQLite テーブル作成・マイグレーション（monitoring_db.init_monitoring_db）

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定（select_candidates）、等配分/スコア重み（calc_equal_weights / calc_score_weights）
  - ポジションサイズ計算（calc_position_sizes）
  - セクター上限適用・レジーム乗数（apply_sector_cap / calc_regime_multiplier）

- 研究（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算・統計サマリ（feature_exploration）

- AI（kabusys.ai）
  - ニュースセンチメント評価（news_nlp.score_news）：OpenAI を用いた銘柄ごとのスコア化
  - レジーム判定（ai/regime_detector.py）：ETF MA と LLM センチメントの合成（別モジュール）

- ツール
  - 環境設定ウィザード（config_setup.py）: 対話式で .env を生成
  - 設定検証 CLI（validate_config.py）: 環境変数 / config/*.yaml の事前チェック
  - Paper Trading 検証レポート（tools/paper_verification_report.py）

セットアップ手順
--------------
前提
- Python 3.10+（PEP 604 の union 型表記（|）を利用しているため）
- 仮想環境の利用を推奨（venv / poetry / pipx 等）

依存ライブラリ（主要）
- duckdb
- psutil
- openai (OpenAI Python SDK)
- PyYAML（config 検証時のみ必要）
- そのほか標準ライブラリ

インストール例（pip）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

（※ requirements.txt がある場合は pip install -r requirements.txt を利用してください）

初期設定
1. ウィザードで .env を作成
   - python -m kabusys.config_setup
   - 対話式に従って必要な環境変数を入力します（J-Quants トークン・kabu API パスワード等）

2. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告もエラーとして扱う場合: python -m kabusys.validate_config --strict

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN : J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD      : kabuステーション API パスワード（必須）
- KABUSYS_ENV            : 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- DUCKDB_PATH            : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            : 監視 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL              : ログレベル（"INFO" 等、デフォルト: INFO）
- OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector で必要）
- MONITOR_POLL_INTERVAL  : 監視ポーリング間隔（秒、run_monitoring 用、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする (0/1, default 0)

使い方
-------

.env の準備
- 対話式: python -m kabusys.config_setup
- 既に .env がある場合は編集して各環境変数を設定

設定検証（任意）
- python -m kabusys.validate_config
- --strict を付けると警告があると exit(1) で失敗扱い

実稼働スクリプト
- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは data/paper_trading.db に記録され本番 DB と分離されます。

- 監視ループ起動（Monitoring）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を指定可能（例: export MONITOR_POLL_INTERVAL=30）
  - python -m kabusys.run_monitoring

プロセス停止制御
- 実行停止（外部からの制御）
  - data/stop_requested.flag: run_execution/run_monitoring のループ停止を指示するために用いられているファイル（存在するとループを抜ける）
  - data/kill.flag: KillSwitch が書き込むことで ExecutionEngine に停止を要求（Execution 側で kill.flag の存在を監視）
- KillSwitch の操作（プログラム的）
  - KillSwitch.clear() により kill.flag を削除できます（または手動で data/kill.flag を削除）

Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD  --to YYYY-MM-DD で期間指定
  - --db PATH で DB パス指定（環境変数 PAPER_TRADING_SQLITE_PATH を優先して使用）

AI 関連
- news_nlp.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）
  - raw_news / news_symbols / ai_scores テーブルを利用
- regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）やマクロ記事を使った日次レジーム判定（OpenAI 使用）

ログ
- デフォルトで logs/ ディレクトリに日次ローテートログが出力されます（kabusys.utils.logging_setup.setup_logging を使用）
- ログファイル名は <app_name>.log（例: execution.log, monitoring.log）

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数 / .env の読み込みロジック
  - config_setup.py              -- .env 対話式ウィザード
  - validate_config.py           -- 設定検証 CLI
  - run_execution.py             -- ExecutionEngine 起動スクリプト
  - run_monitoring.py            -- Monitoring 起動スクリプト
  - data/                        -- （実行時に作成される想定）SQLite/DuckDB/pid/flag など
  - logs/                        -- ログ出力先（デフォルト）
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照されるが実装ファイルはこの一覧に依存)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py

設計上の注意点 / 運用上のヒント
--------------------------------
- KABUSYS_ENV が "live" の場合は本番運用となるため、kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は避けることを推奨します。
- news_nlp / regime_detector は OpenAI API を利用するため、API レート制限や接続エラーを考慮した運用が必要です。コード内でリトライ・フェイルセーフが組まれていますが、キーの管理・請求上の注意は運用者の責任です。
- monitoring のチェックでは process の生存監視やデータ鮮度を評価します。監視間隔は MONITOR_POLL_INTERVAL で調整してください。
- paper_trading は本番 DB と完全分離されるよう設計されています。検証やオフラインテストは paper_trading モードを利用してください。

貢献 / 開発
------------
- ローカル開発: Python 仮想環境を使い、.env を作成後に各モジュールのユニットテストを追加してください。
- フォーマット・型チェック: 好みに応じて black / ruff / mypy 等を導入してください。
- 重要なマイグレーション（monitoring DB の列追加等）は init_monitoring_db に実装済みです。DB スキーマ拡張時は互換性に注意してください。

問題や質問
----------
- 実行時に必要な追加の依存パッケージや実行手順はプロジェクトのドキュメントに随時追記してください。
- バグ報告・提案は Issue を作成してください。

以上。README の内容はコードの主要部分をベースにまとめています。実際の運用環境に合わせて .env / DB パス / ログ設定を調整してください。