KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買／研究用ライブラリ兼実行スクリプト群です。
主な機能は発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、
ファクター計算・研究、AI を用いたニュースセンチメント評価などです。

主なポイント
- 実行スクリプト（run_execution / run_monitoring）を通じて本番／ペーパートレードを起動可能
- DuckDB / SQLite を使ったデータ格納・分析
- OpenAI を用いたニュース NLP（センチメント）・レジーム判定モジュール
- .env ウィザード（config_setup.py）／起動前検証（validate_config.py）を備え安全に起動可能
- ログは stdout と logs/*.log に出力（日時ローテーション）

前提
- Python 3.10 以上（typing の "|" 等の構文を使用）
- 推奨ライブラリ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証に利用。未インストールでも動作するが、YAML 検証はスキップされます）
- OS: Linux / macOS / Windows（プロセス優先度設定・CPU affinity は一部 OS に依存）

機能一覧
- 実行（Execution）
  - ExecutionEngine：Broker クライアント経由で発注管理、OrderManager, RiskManager, Reconciler 等を統合
  - paper_trading モード: MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセスの生存確認・データ鮮度チェック
  - TradeMonitor：発注ログの滞留・約定異常検出（実装参照）
  - RiskMonitor：ドローダウン・ポジション数上限監視、ダッシュボード更新
  - KillSwitch：条件に応じて data/kill.flag を書き込み ExecutionEngine 停止を要求
  - MonitoringEngine：上記をまとめてポーリング・アラート送信
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、ポジションサイズ計算、セクター上限・レジーム乗数
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Information Coefficient）、ファクター統計サマリー
- AI（OpenAI）
  - news_nlp: raw_news を LLM（gpt-4o-mini）で評価し ai_scores テーブルへ書込
  - regime_detector: MA200 とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツール
  - paper_verification_report: ペーパートレード DB から検証レポートを生成

セットアップ手順（開発環境向け）
1. リポジトリをクローンして venv を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install -U pip
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt がある場合はそれを使用）

3. Python パッケージとして開発インストール（任意）
   - pip install -e .

4. .env を作成（対話式ウィザード）
   - python -m kabusys.config_setup
     - 対話式に .env（デフォルト: プロジェクトルート/.env）を生成・更新します。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにしたい場合:
     - python -m kabusys.validate_config --strict

主要な環境変数（代表）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - paper_trading: 発注は MockBroker、DB は data/paper_trading.db（分離）
- OPENAI_API_KEY — OpenAI を使用する機能（news_nlp / regime_detector）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（INFO 等）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒, run_monitoring 側で使用、デフォルト 60）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant|partial|never|reject）

使い方（よく使うコマンド）
- .env 作成ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - Strict モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBroker を使用
  - 実行中の停止：
    - 停止フラグを立てる: touch data/stop_requested.flag （実際にファイルに理由を書いても可）
    - ExecutionEngine は起動時に data/kill.flag の自動クリア設定を確認する（KILL_FLAG_CLEAR_ON_START）

- 監視ループ起動（Monitoring）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能の利用（スクリプトから呼び出す）
  - OPENAI_API_KEY を設定してから news_nlp.score_news / regime_detector.score_regime を呼ぶ
  - 例（簡易）:
    - python -c "from kabusys.ai.news_nlp import score_news; import duckdb, datetime, os; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key=os.environ['OPENAI_API_KEY']))"

停止・制御ファイル
- data/stop_requested.flag
  - run_execution.py / run_monitoring.py がこのファイルを検知すると安全に停止します。
  - 起動中の停止要求はこのファイルを作成してください。
- data/kill.flag
  - KillSwitch が条件を満たした場合に書き込まれ、ExecutionEngine に停止シグナルを与えます。
  - data/kill.flag を削除することでクリアできます（ExecutionEngine の起動時に自動クリア設定も可能）。

ログ
- setup_logging によりルートロガーは stdout（StreamHandler）と logs/<app_name>.log（日次ローテーション）へ出力します。
- デフォルトログディレクトリ: logs/
- ログレベルは LOG_LEVEL 環境変数または setup_logging の引数で制御します。

ディレクトリ構成（主要ファイル）
- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境変数 / Settings 管理（.env 自動読込）
    - config_setup.py             — .env 対話式ウィザード
    - validate_config.py          — 起動前設定検証 CLI
    - run_execution.py            — ExecutionEngine 起動スクリプト
    - run_monitoring.py           — Monitoring ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py               — ニュース NLP スコアリング
      - regime_detector.py        — 市場レジーム判定
    - monitoring/
      - monitoring_db.py          — SQLite 永続化層（schema/migration）
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py          —（注）アラート送信ロジック（未抜粋）
    - execution/
      - execution_engine.py      — ExecutionEngine（主ロジックはここ）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - data/                       — 実行時に使用するファイル群（DB・フラグ等）
    - utils/
      - logging_setup.py
      - process_priority.py
      - その他ユーティリティ

設計上の注意点・運用メモ
- 環境は KABUSYS_ENV により切り替わります。paper_trading は発注系を分離して安全に検証できます。
- OpenAI を利用する機能は API 呼び出しに失敗した場合にフェイルセーフ（スコア 0 など）で継続する設計です。API キーの管理には注意してください。
- run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとします。権限不足で失敗する場合はログに警告が出ます。
- monitoring の DB（SQLITE_PATH）と paper_trading の DB（PAPER_TRADING_SQLITE_PATH）は分離推奨。
- .env ファイルは絶対にリポジトリにコミットしないでください（config_setup.py のヘッダにも明記）。

トラブルシューティング
- ログディレクトリ作成失敗 → ファイルハンドラは無効化されコンソール出力のみになります。パーミッション等を確認してください。
- DuckDB / SQLite のファイルパスが存在しない場合、validate_config で警告が出ます。必要ならディレクトリを事前に作成してください。
- OpenAI 関連でレスポンスが期待通りでない場合はログ（警告）を確認し、API レスポンス形式やネットワークを確認してください。

貢献・拡張
- 研究用モジュール（research）やポートフォリオ構築のロジックは純粋関数として実装されておりユニットテストが書きやすい設計です。拡張・検証を歓迎します。
- BrokerClient（broker_factory）を拡張して他ブローカーの実装を追加できます（抽象化済み）。

ライセンス・バージョン
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください。

以上が README の概要です。必要であれば以下の補足を提供します：
- 具体的な .env のテンプレート（.env.example 風）
- 実行ログの例
- よくあるエラーと対処法

どの補足情報が必要か教えてください。