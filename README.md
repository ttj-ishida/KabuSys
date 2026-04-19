README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のライブラリ群です。  
このリポジトリには以下の主要機能が含まれます:

- 実運用向け ExecutionEngine（発注、リスク管理、整合処理）
- 監視サブシステム（System / Trade / Risk のポーリング、Kill Switch）
- ポートフォリオ構築（候補選定、重み付け、ポジション決定）
- リサーチ／ファクター計算（モメンタム、ボラティリティ、バリュー等）
- AI 製品群（ニュースセンチメント NLP、レジーム判定）
- 運用支援ツール（.env ウィザード、設定検証、ペーパー検証レポート）
- 共通ユーティリティ（ログ設定、プロセス優先度設定等）

特徴
----
- モジュラーデザイン：監視 / 実行 / リサーチ / ポートフォリオ等が分離され、単体テストや部分運用が容易
- フェイルセーフ設計：API エラーやデータ欠損時にフォールバックする実装（Kill Switch、リトライ、ロギング）
- Paper Trading モード：KABUSYS_ENV=paper_trading を使うと発注はモック化され、paper_trading 専用 DB に記録
- AI連携：OpenAI（gpt-4o-mini 等）でニュースセンチメントやマクロ判定を行い、DB に格納
- 軽量 DB：監視は SQLite、分析は DuckDB を使用

前提
----
- Python 3.10+
- 必要な外部依存パッケージ（代表例）:
  - duckdb
  - psutil
  - openai (AI 機能利用時)
  - PyYAML（config の YAML 検証に任意）
- SQLite（Python 標準ライブラリで提供）

セットアップ手順
---------------
1. リポジトリをクローンして仮想環境を作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 例:
     pip install duckdb psutil openai PyYAML

   ※ requirements.txt がない場合は、上の代表パッケージを環境に応じて追加してください。

3. .env を作成（自動 or ウィザード）
   - インタラクティブに作りたい場合:
     python -m kabusys.config_setup
   - 既存の .env がある場合は自動読み込みされます（プロジェクトルートに .env または .env.local があれば読み込まれます）。
   - 自動読み込みを無効化するには:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定の検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 厳密モード（警告も失敗扱い）:
     python -m kabusys.validate_config --strict

主要環境変数（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 専用 DB（paper_trading モード）
- LOG_LEVEL — デフォルト: INFO
- OPENAI_API_KEY — AI 機能利用時に必須
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか (0/1、デフォルト 0)

起動 / 使い方
-------------

- 監視ループを起動（SystemMonitor のポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視が停止するにはプロジェクトルートの data/stop_requested.flag を作成するか、Ctrl+C

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、paper_trading 用 DB に記録（本番 DB と分離）
  - 停止シグナル: data/stop_requested.flag（作成されると既存エンジンを停止）

- .env 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict オプションで警告も失敗とみなす

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可）

- AI 機能（プログラム的利用）
  - ニュース NLP（スコア保存）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="...")

ロギング
--------
- ログはデフォルトで stdout と logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリ）。  
- setup_logging() により、ログディレクトリは環境変数 LOG_DIR または引数で指定可能。

停止フラグ / Kill Switch
-----------------------
- data/stop_requested.flag
  - run_monitoring / run_execution はこのファイルの存在を監視し、存在すると安全にシャットダウンします。

- Kill Switch（監視側）
  - 条件を満たすと kabusys.monitoring.kill_switch.KillSwitch が data/kill.flag（デフォルト）を書き込みます。
  - ExecutionEngine は起動時に kill.flag を検査し、既存であれば起動を拒否できます。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag をクリアします（本番では推奨しません）。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py: パッケージ定義、バージョン
- config.py: 環境変数の読み込みロジックと Settings クラス（.env 自動ロード）
- config_setup.py: .env 作成用の対話ウィザード
- validate_config.py: 起動前の設定検証スクリプト
- run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
- run_execution.py: ExecutionEngine 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py: ニュースを OpenAI でスコアリングして ai_scores に書き込むロジック
  - regime_detector.py: マクロ＋MA200 を合成して market_regime テーブルに書き込む
- monitoring/
  - monitoring_db.py: SQLite スキーマ初期化・簡易 CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: システム・データ鮮度監視
  - trade_monitor.py: （省略されているが）取引関連監視
  - risk_monitor.py: ドローダウンやポジション上限監視
  - kill_switch.py: kill.flag 管理ロジック
  - monitoring_engine.py: 各モニタの束ね処理（ポーリング・アラート連携）
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    - （処理フロー: ブローカ生成 → リポジトリ/マネージャ組立 → ExecutionEngine 起動）
- portfolio/
  - portfolio_builder.py: 候補選定、等配分・スコア配分
  - position_sizing.py: 発注株数算出（リスクベース／等配分等）および集約キャップ処理
  - risk_adjustment.py: セクターキャップ、レジーム乗数
- research/
  - factor_research.py: momentum / volatility / value ファクターの DuckDB ベース計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー等の解析ユーティリティ
- tools/
  - paper_verification_report.py: ペーパートレードのパフォーマンス・ヘルス判定レポート生成
- utils/
  - logging_setup.py: ログの一元設定ユーティリティ
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ

データ / ファイル（実行時生成される代表例）
- data/kabusys.duckdb (デフォルト)
- data/monitoring.db (監視 SQLite DB)
- data/paper_trading.db (paper_trading モード時の DB)
- data/execution.pid (ExecutionEngine の PID ファイル)
- data/stop_requested.flag (外部からの停止指示用)
- data/kill.flag (Kill Switch により書き込まれる停止フラグ)
- logs/<app_name>.log（ログファイル）

補足: DB スキーマ・永続化
-----------------------
- monitoring_db.init_monitoring_db(conn) が監視用 SQLite のテーブルとインデックスを冪等的に作成します（system_status, trade_logs, positions, risk_logs, dashboard）。
- ai/news_nlp や ai/regime_detector は DuckDB 接続を受け取り、prices_daily / raw_news / raw_financials 等のテーブルを想定して処理します。

よくある運用フロー（例）
------------------------
1. .env を作成（python -m kabusys.config_setup）
2. 設定を検証（python -m kabusys.validate_config）
3. データ収集・DuckDB を用意（prices_daily 等の投入）
4. 監視プロセス起動（python -m kabusys.run_monitoring）
5. 実行エンジンを必要に応じて起動（python -m kabusys.run_execution）
6. AI スコアやレジーム判定を定期実行して DuckDB に書き込み
7. 異常時は monitoring が kill.flag を作成し、Execution を安全に停止

開発者向けメモ
---------------
- モジュールは基本的に副作用を避ける設計です（DB 接続やクライアントは呼び出し側で渡す）。
- テストやローカル実行時は KABUSYS_ENV=development または paper_trading を使用してください。
- AI 機能をローカルでテストする場合は OPENAI_API_KEY を適切に設定してください。テスト時は _call_openai_api をモックする設計です。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（例: 0.1.0）

問題報告・貢献
--------------
バグ報告や改善提案は Issue を作成してください。Pull Request は歓迎します。README にない具体的な使い方（ExecutionEngine のパラメータや Broker 実装詳細など）については、該当モジュールの docstring / コメントを参照してください。

以上。