README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリには以下の主要機能を含むモジュール群が含まれます:

- 発注エンジン（ExecutionEngine）・発注管理
- 監視（Monitoring）・Kill Switch
- ポートフォリオ構築（候補選別、重み付け、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算・特徴量探索）
- ニュース分析（LLM を使ったセンチメント評価）および市場レジーム判定
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード／検証ツール）
- ペーパートレード用の検証レポート出力

この README ではセットアップ、使い方、主要機能の説明、ディレクトリ構成を日本語でまとめます。

特徴（主な機能）
----------------
- 発注実行（本番 / ペーパートレード切替）
  - KABUSYS_ENV により paper_trading / live / development を切替可能
  - paper_trading 時は専用 SQLite（data/paper_trading.db）を使用して本番 DB と分離
- 監視（System / Trade / Risk）
  - システムリソース、データ鮮度、滞留注文、ドローダウン等の監視
  - Kill Switch（条件満たした場合 data/kill.flag を生成して ExecutionEngine を停止）
- LLM ベースのニュースセンチメント（OpenAI）
  - raw_news から記事を集約し OpenAI（gpt-4o-mini）へバッチで問い合わせ
  - ai_scores テーブルへ書き込み
- 市場レジーム判定
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを組み合わせて daily 判定
- リサーチ機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC 計算
- ポートフォリオ構築ユーティリティ
  - 候補選択、等金額・スコア重み、リスクベースのポジションサイズ計算、セクター上限適用
- ツール
  - .env 対話式ウィザード（config_setup）
  - 設定チェック（validate_config）
  - ペーパートレード検証レポート生成

前提（依存関係）
----------------
最低限の推奨環境:
- Python 3.10 以上（型注釈で | が使われています）
- 必要なパッケージ（プロジェクトで使う主要パッケージの一例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml 検証時に任意で使用）
必要に応じて requirements.txt を用意して pip install してください（本リポジトリには requirements.txt が無いので手動でインストールしてください）:

例:
  pip install duckdb psutil openai pyyaml

セットアップ手順
----------------
1. リポジトリルート（pyproject.toml/.git がある位置）に移動します。
2. Python 仮想環境を作成して有効化（推奨）。
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール:
   pip install duckdb psutil openai pyyaml
4. .env の初期作成:
   python -m kabusys.config_setup
   - 対話式に入力することで .env を生成します（.env は絶対に Git にコミットしないでください）。
5. 設定検証（任意）:
   python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。
6. データディレクトリの確認:
   - デフォルトでは data/ 配下に SQLite / DuckDB 等が作られます。起動前にディレクトリが自動作成されますが、必要なら手動で作成してください。
7. OpenAI を使う機能を使う場合は OPENAI_API_KEY を .env に設定してください。

重要な環境変数（抜粋）
-----------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（ニュース NLU / レジーム判定で必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60）

起動・使い方（主要スクリプト）
------------------------------

- 環境設定ウィザード
  python -m kabusys.config_setup
  - 対話式で .env を生成・更新します。

- 設定検証
  python -m kabusys.validate_config [--strict]
  - .env や config/*.yaml の基本的な妥当性やパスの存在などをチェックします。

- 監視ループ（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=120）
  - ログ: setup_logging を使い logs/monitoring.log に日次ローテーション出力されます。
  - 停止: プロセスは data/stop_requested.flag の存在を検知してループを終了します。

- Execution（ExecutionEngine）起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - Execution 側も data/stop_requested.flag を監視して停止します。
  - Execution の PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

停止・Kill 操作
----------------
- 実行中の監視/実行プロセスを安全に停止するにはプロジェクトルートの data/stop_requested.flag を作成してください（空ファイルで OK）。
  - 例: mkdir -p data && touch data/stop_requested.flag
- Kill Switch（自動停止）:
  - リスク・ドローダウン等の条件を満たすと KillSwitch が data/kill.flag を書き込み、ExecutionEngine に停止を促します。
  - 実運用時は KILL_FLAG_CLEAR_ON_START 設定に注意してください（本番では 0 推奨）。

ログとプロセス優先度
-------------------
- 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出してログを設定します。
  - コンソール（stdout）と logs/<app_name>.log（日次ローテーション、30日分保持）に出力します。
- 起動時にプロセス優先度を High に設定します（psutil による実装で OS により差異あり）。

データベース（概要）
------------------
- SQLite（monitoring.db / paper_trading.db）
  - テーブル例: system_status, trade_logs, positions, risk_logs, dashboard
  - init_monitoring_db によりスキーマを冪等に作成・マイグレーションします
- DuckDB（分析用 kabsys.duckdb）
  - prices_daily や raw_financials, raw_news, ai_scores, market_regime などの分析テーブルを想定

主要モジュール（概観）
--------------------
- kabusys.config
  - Settings クラスで環境変数をラップ。自動的に .env/.env.local をロード（無効化可）。
- kabusys.config_setup
  - .env を対話式生成するウィザード。
- kabusys.validate_config
  - .env と config/*.yaml の前提チェックツール。
- kabusys.run_monitoring
  - SystemMonitor をポーリングして monitoring DB に記録。MONITOR_POLL_INTERVAL を環境変数で上書き可。
- kabusys.run_execution
  - ExecutionEngine を起動（paper_trading 時は専用 SQLite を使用）。
- kabusys.monitoring.*
  - MonitoringDB（永続層）、SystemMonitor、TradeMonitor、RiskMonitor、MonitoringEngine、KillSwitch、AlertManager 等
- kabusys.portfolio.*
  - 候補選定、重み計算、セクター適用、ポジションサイズ計算（純粋関数で DB 参照しない）
- kabusys.research.*
  - ファクター計算（momentum/value/volatility）、将来リターン計算、IC 等
- kabusys.ai.*
  - news_nlp.py: OpenAI によるニュースセンチメント集計（score_news）
  - regime_detector.py: MA200 とマクロセンチメントを合成して daily レジーム判定（score_regime）
- kabusys.utils.*
  - logging_setup、process_priority（優先度 / CPU affinity）など

よく使うコマンド例
------------------
- .env を作る（ウィザード）:
  python -m kabusys.config_setup
- 設定検証:
  python -m kabusys.validate_config
- 監視を起動（ポーリング間隔 60 秒）:
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
- Execution を起動（ペーパートレード）:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要ファイル・ディレクトリの抜粋です（実際のツリーはこのリポジトリに依存します）。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py  (アラート処理)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/ (※上記)
  - tools/
    - __init__.py
    - paper_verification_report.py
  - data/ (ランタイムで使用、例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid)
  - config/ (YAML 設定ファイル群: system_config.yaml, data_config.yaml, ...)

補足・運用上の注意
------------------
- .env は機密情報（API キー等）を含むため絶対に Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 のままにすることを推奨します（自動クリアは危険）。
- OpenAI を用いる機能は API コストとレート制限に注意してください（本実装はバッチ / リトライ戦略を持ちますが運用で制御してください）。
- DuckDB / SQLite ファイルのバックアップ・スナップショット運用を検討してください（特に本番ログ・取引履歴）。

ライセンス / バージョン
-----------------------
パッケージバージョン: __version__ = "0.1.0"（src/kabusys/__init__.py）

問い合わせ・貢献
----------------
不具合や改善提案は Issue を立ててください。コード変更の際はテスト追加と設定検証を忘れずに行ってください。

以上。必要であれば README にチュートリアルやより詳細な設定例（.env のサンプル、system_config.yaml の例、起動スクリプトの systemd/cron での運用方法など）を追加します。どの情報が欲しいか教えてください。