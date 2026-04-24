README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のサンプル実装です。本リポジトリは以下を含みます：
- 注文実行エンジン（ExecutionEngine）とペーパートレード切替
- 監視コンポーネント（System / Trade / Risk）と Kill Switch
- ポートフォリオ構築ユーティリティ（候補選定、重み計算、ポジションサイズ算出 等）
- リサーチ向けファクター計算（モメンタム、ボラティリティ、バリュー）
- ニュース NLP（OpenAI）を用いたセンチメント評価とレジーム判定
- 運用補助ツール（設定ウィザード / 設定検証 / ペーパートレード検証レポート）

このコードベースはライブラリとしても、起動スクリプト（python -m kabusys.xxx）としても利用できます。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading と live を切替
  - paper_trading では MockBrokerClient を使用し data/paper_trading.db に記録
  - プロセス優先度設定・PID 管理・停止フラグ監視対応

- Monitoring（run_monitoring.py / monitoring モジュール）
  - system_status / trade_logs / risk_logs / positions / dashboard を SQLite に永続化
  - System / Trade / Risk 各 Monitor の定期実行とアラート判定
  - Kill Switch（データ駆動で Execution を停止するフラグ書き込み）

- ポートフォリオ関連ユーティリティ（kabusys.portfolio）
  - 候補選択、等重/スコア重み付け、リスク調整（セクターキャップ等）、ポジションサイズ算出（単元丸め、aggregate スケールダウン）

- リサーチ（kabusys.research）
  - DuckDB 接続を利用したファクター計算（モメンタム/ボラティリティ/バリュー）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー

- AI（kabusys.ai）
  - ニュース記事を OpenAI でスコアリングして ai_scores に書き込み
  - マクロニュース × ETF ma200 を組み合わせた市場レジーム判定

- 運用ツール
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

セットアップ手順
----------------
前提
- Python 3.10 以上（typing の | 演算子等を使用）
- git

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境の作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 代表的な依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML (config 検証で任意)
   - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt を使用）

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または .env.example を参考に手動で作成
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (paper_trading 用)
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=... (AI 機能使用時)

5. データ/ログディレクトリ作成（必要に応じて）
   - mkdir -p data logs

使い方（主なコマンド）
--------------------

設定関連
- 設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）

監視（Monitoring）
- 監視ループを起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト: 60）
  - 監視は監視用 SQLite（Settings.sqlite_path）を使用する（KABUSYS_ENV に依存せず production path を参照）
  - 停止するにはプロジェクトルート/data/stop_requested.flag を作成

注文実行（Execution）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合はペーパートレード DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB とは完全分離
  - 起動時に data/execution.pid が使用され、stop は data/stop_requested.flag または kill.flag により制御

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db で DB パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH も参照。

AI / レジーム判定 / ニューススコア（ライブラリ関数）
- OpenAI API を利用する機能は api_key（OPENAI_API_KEY 環境変数）を必要とします。
- 例（ライブラリ呼び出し）:
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key="...")

ログ
- ログは logs/<app_name>.log に日次ローテーションで保存（デフォルト: logs/）
- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一されます。

停止 / Kill Switch
- KillSwitch は data/kill.flag を作成して ExecutionEngine に停止を要求します（Monitoring がルールに従い書き込む）
- run_execution/run_monitoring は stop_requested.flag を検知して自己終了します（data/stop_requested.flag）

設定とファイルパス（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID ファイル: data/execution.pid
- Kill flag: data/kill.flag
- Stop flag: data/stop_requested.flag

ディレクトリ構成（要点）
---------------------
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数 + .env 自動読み込みロジック
    config_setup.py              # .env 対話式ウィザード
    validate_config.py           # 設定検証 CLI
    run_execution.py             # ExecutionEngine 起動スクリプト
    run_monitoring.py            # Monitoring 起動スクリプト

    ai/
      __init__.py
      news_nlp.py                # ニュースセンチメントスコアリング（OpenAI 経由）
      regime_detector.py         # マクロ + ETF ma200 によるレジーム判定

    monitoring/
      monitoring_db.py           # SQLite 永続化層
      system_monitor.py
      trade_monitor.py           # （ファイル内の他モジュールもあり）
      risk_monitor.py
      monitoring_engine.py
      kill_switch.py
      alert_manager.py           # （通知ラッパー、実装参照）

    execution/
      broker_factory.py
      execution_engine.py
      order_manager.py
      order_repository.py
      reconciler.py
      risk_manager.py

    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py

    research/
      factor_research.py
      feature_exploration.py
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py

    data/                        # 実行時に生成される想定ディレクトリ（DB・flag・PID 等）

    utils/
      logging_setup.py
      process_priority.py
      __init__.py

設計上の注意点 / よくある質問
------------------------------
- Paper trading と本番 DB は分離されています。KABUSYS_ENV=paper_trading の時のみ paper_trading DB を使用します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 関連機能は API キーの設定が必須です。API 呼び出しはリトライ / フェイルセーフ実装が入っていますが、API 使用料に注意してください。
- ログディレクトリ作成に失敗した場合、ファイル出力は無効化されコンソール出力のみで継続します。
- system_monitor はデータ鮮度（DuckDB の prices_daily）を確認します。DuckDB のパスは DUCKDB_PATH で指定してください。

貢献・開発
----------
- 開発時は仮想環境を利用し、依存パッケージを明示的に管理してください。
- 主要な CLI は python -m kabusys.<module> で実行できます。ユニットテストや lint を追加して品質維持を行ってください。

ライセンス
---------
（ここにライセンス情報を記載してください）

以上。README の補足や特定機能（例: ExecutionEngine の設定項目、OrderRepository の仕様、AlertManager の設定など）について詳細を追記したい場合は、追って記載します。