KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。  
本READMEはリポジトリ内の主要コンポーネントと起動・運用に必要な手順を簡潔にまとめたものです。

要点
----
- Pythonパッケージ: kabusys
- 主な機能: 実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AIベースのニュースセンチメント評価（OpenAI利用）など
- 永続化: DuckDB（分析用） / SQLite（監視・発注ログ用）
- 設定: 環境変数または .env ファイル（対話式ウィザードあり）

プロジェクト概要
----------------
KabuSys は自動売買のコアロジック（シグナル / ポートフォリオ構築 / ポジションサイズ計算 / リスク管理）と、実行・監視・レポート作成のユーティリティを提供します。  
主な責務は次のとおりです。

- ExecutionEngine: ブローカークライアントを用いた発注・注文管理（paper_trading時はモックブローカーを使用）
- Monitoring: システム状態・注文状況・リスク（ドローダウン等）を定期ポーリングしてログ／アラート／Kill Switch を制御
- Research: DuckDB上でのファクター計算（momentum、volatility、value など）
- AIモジュール: ニュースを LLM（OpenAI）でスコアリングしてテーブルへ保存、レジーム判定など
- Tools: ペーパートレードの検証レポート生成 等

主な機能一覧
-------------
- 環境設定ウィザード: python -m kabusys.config_setup（.env を対話的に作成）
- 設定検証: python -m kabusys.validate_config（.env と config/*.yaml の事前検証）
- 実行エンジン起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBroker を使用し paper_trading 用 DB に記録
- 監視ループ起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60秒）
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- ポートフォリオ構築: 候補選定 / 重み計算 / ポジションサイズ算出（等分、スコア重み、リスクベース）
- AI: OpenAI を利用したニュースセンチメントスコア（ai_scores）と市場レジーム判定（market_regime）
- ログ管理: 共通の setup_logging による stdout + 日次ローテートファイル（logs/<app>.log）

セットアップ手順
----------------
1. Python環境を準備
   - Python 3.9+ を推奨（コードは型注釈等を使用）
   - 必要パッケージの例（requirements.txt がある場合はそれを使用してください）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証用：任意）
   - 例:
     pip install duckdb psutil openai pyyaml

2. リポジトリルートで data / logs 等のディレクトリを作成（多くは自動作成されますが事前に用意すると権限問題を回避できます）
   mkdir -p data logs

3. 環境変数設定 (.env)
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - 主要な必須環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 主要な任意／デフォルト:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - OPENAI_API_KEY: AI モジュール利用時に必要
     - MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring では環境変数名 MONITOR_POLL_INTERVAL を参照）

4. 設定検証（起動前チェック）
   python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いで exit(1) になります

5. DB初期化
   - 実行スクリプト（run_monitoring / run_execution）が起動時に必要なテーブルを自動作成します（init_monitoring_db を利用）

使い方（起動・停止・運用）
-------------------------
- 監視プロセス起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL（秒）でポーリング。既定60秒。
  - 監視は Settings.sqlite_path に接続（環境にかかわらず本番 sqlite_path を使用する設計）
  - 監視中に data/stop_requested.flag を作成するとループは終了します（安全な停止トリガ）

- 実行エンジン起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録し本番 DB から分離
  - start 前に data/stop_requested.flag が存在すると起動をスキップ
  - 実行中に data/stop_requested.flag を作成するとエンジンに停止を通知（ExecutionEngine.stop() を呼び安全停止）

- Kill Switch（自動停止シグナル）:
  - 監視モジュールがドローダウンやポジション上限超過などの重大リスクを検知すると、data/kill.flag を書き込みます（KillSwitch）。
  - kill.flag は ExecutionEngine 側が参照して発注停止へつなげます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動的にクリアされますが、本番では 0 を推奨します。

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で指定可能
  - 稼働率、注文成功率、送信率、レイテンシ(P95) 等を評価し PASS/FAIL を出力

環境変数一覧（主要）
--------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（ログ出力先、デフォルト: logs/）
- OPENAI_API_KEY（AI機能を使う場合に必須）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔上書き）
- KILL_FLAG_CLEAR_ON_START（本番での自動Killフラグクリア: 0/1）

ログと監視
----------
- ログ: setup_logging() によって stdout と日次ローテートファイル（logs/<app>.log）へ出力されます。ログディレクトリが作成できない場合はコンソール出力のみになります。
- 監視ログ: monitoring.db（Settings.sqlite_path） に system_status / trade_logs / positions / risk_logs / dashboard を保存します。
- DuckDB: 分析や研究（research）用途のテーブルを保持します（settings.duckdb_path）。

トラブルシューティング / 運用注意
---------------------------------
- 必須環境変数が未設定だと Settings のプロパティで ValueError が発生します。まず validate_config を実行してください。
- AI 関連（news_nlp, regime_detector）を使うためには有効な OPENAI_API_KEY が必要です。キーが無い場合は例外や ValueError が出ます。
- run_monitoring は MONITOR_POLL_INTERVAL が不正（0以下や非整数）の場合、デフォルト 60 秒にフォールバックします。
- run_execution は paper_trading 環境時に本番 DB を汚さないよう設計されています。paper_trading 用 DB のパスを確認してください。
- ディレクトリ作成やファイル書き込みで権限エラーが出ることがあるため、logs/ と data/ に対する書き込み権限を確認してください。

主要なディレクトリ構成
----------------------
リポジトリの主要ファイルと簡単な説明:

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数/.env ロードと Settings クラス（アプリ設定全般）
  - config_setup.py — .env 作成対話式ウィザード（CLI）
  - validate_config.py — 設定検証 CLI
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py — SQLite 監視テーブルの初期化・CRUD ラッパー
    - system_monitor.py — CPU/memory/disk/データ鮮度/プロセス監視
    - trade_monitor.py — (取引監視モジュール) ※実装ファイルあり
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の書き込み
    - monitoring_engine.py — 各モニタとアラートを束ねるエンジン
    - alert_manager.py — (通知処理、LINE等) ※実装ファイルあり
  - execution/
    - execution_engine.py — 実行エンジン（セッション管理）
    - broker_factory.py — ブローカークライアント生成（Mock含む）
    - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行周りのコンポーネント
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・投下資金制限
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB使用）
    - feature_exploration.py — forward returns, IC, 統計サマリー
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングし ai_scores へ書き込み
    - regime_detector.py — MA200 + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

開発メモ（設計上のポイント）
--------------------------
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行うため、CWD に依存しません。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能です。
- Monitoring は設計上、本番 sqlite_path を使用して監視ログを一元管理します（monitoring は KABUSYS_ENV にかかわらず production sqlite_path を使用する実装の箇所あり）。
- Paper Trading は本番 DB と完全分離されるよう配慮されています（settings.is_paper に応じた sqlite_path 選択）。
- ロギングは全起動スクリプトで setup_logging(app_name=...) を使うことで一貫化しています。

ライセンス / 貢献
----------------
この README はコードベースを読むだけで起動できるようにまとめたものです。実際の運用前に必ず設定検証と十分なテストを行ってください。貢献や改善提案は Pull Request / Issue で歓迎します。

補足（コマンド一覧）
-------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 監視起動: python -m kabusys.run_monitoring
- 実行起動: python -m kabusys.run_execution
- Paper 検証: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

以上。運用や開発で必要な箇所があれば、この README に追記します。