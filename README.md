KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
戦略（ファクター計算 / 特徴量解析）、ポートフォリオ構築、ポジションサイズ計算、実行（ExecutionEngine）、
監視（Monitoring）、AI ベースのニュース NLP / レジーム判定、ペーパートレード検証ツールなどを含みます。  
モジュールは可能な限り副作用を排し、DuckDB/SQLite をデータ層に用いる設計になっています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution）
  - 本番 / ペーパートレードを分離して実行（KABUSYS_ENV=paper_trading のとき専用 DB と MockBroker を使用）
  - プロセス優先度設定、PID 管理、停止フラグ検出
- Monitoring（run_monitoring / monitoring_engine）
  - システム稼働状況・データ鮮度・注文ログ・リスク監視（ドローダウン、ポジション数上限）
  - Kill Switch による安全停止（data/kill.flag）
  - アラート送信ポイント（LINE 等を介した通知設定に対応）
- 設定管理ツール
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
  - 起動前検証 CLI（python -m kabusys.validate_config）
- 研究・リサーチ
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Information Coefficient）など
- ポートフォリオ構築
  - 銘柄選定、スコア加重・等配分、セクター制限、レジーム乗数、ポジションサイズ計算（単元丸め・aggregate cap）
- AI モジュール
  - ニュース NLP（OpenAI を使った銘柄別センチメント）と market regime 判定
  - バッチ・リトライ・レスポンス検証や結果の DuckDB への永続化を備える
- ユーティリティ
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）
  - ログ設定ユーティリティ、プロセス優先度設定ユーティリティ 等

セットアップ
-----------
前提
- Python 3.10 以上（typing の最新構文を利用）
- 必要な外部ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（validate_config で YAML 内容検証を行う場合）
- SQLite は標準ライブラリで利用可能

手順（開発マシン例）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - ※実際の requirements.txt がある場合はそれを使用してください
4. .env を作成
   - python -m kabusys.config_setup
   - J-Quants / kabu API 等の必須環境変数を対話式にセットします
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります

主要な環境変数（主要項目）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live）デフォルト: development
- OPENAI_API_KEY（AI 機能利用時に必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- LOG_LEVEL（DEBUG / INFO / ...）
- KILL_FLAG_CLEAR_ON_START（1 にすると起動時に kill.flag を自動クリア。production は 0 推奨）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒）。デフォルト 60）

起動・使い方
------------
- 環境ファイルの作成
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 実行エンジン起動（本番 / ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、paper_trading 用 DB に書き込まれ、本番 DB と分離されます
  - 実行中に data/stop_requested.flag を作成すると安全にシャットダウンします
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は環境にかかわらず sqlite_path（本番 path）を使用します
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- AI スコア / レジーム判定（コード呼び出し例）
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - これらは DuckDB 接続を受け取り、結果をテーブルへ書き込みます

停止・Kill Switch
-----------------
- 安全停止シグナル:
  - data/stop_requested.flag を作成すると run_execution/run_monitoring が検知して終了処理を行います
- Kill Switch（リスクトリガーにより ExecutionEngine 停止）
  - data/kill.flag を書き込むと ExecutionEngine は次のチェックで停止します
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされます（本番では 0 推奨）

ログ
---
- ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/ ディレクトリ）
- setup_logging を全スクリプトで使用して一貫したログ出力となっています
- 環境変数 LOG_DIR、LOG_LEVEL で制御可能

ディレクトリ構成（主要ファイル / ディレクトリ）
------------------------------------
src/kabusys/
- __init__.py
- config.py                   — .env 自動読み込み・Settings ラッパ
- config_setup.py             — 対話式 .env 作成ウィザード（CLI）
- validate_config.py          — 起動前設定検証 CLI
- run_execution.py            — ExecutionEngine 起動スクリプト
- run_monitoring.py           — Monitoring 起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート CLI
- utils/
  - logging_setup.py          — ログ設定ユーティリティ
  - process_priority.py       — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py          — SQLite 永続化層（system_status / trade_logs / risk_logs / dashboard / positions）
  - system_monitor.py         — システム状態 / データ鮮度監視
  - trade_monitor.py          — （注文滞留・約定異常等の監視）※実装ファイルあり
  - risk_monitor.py           — ドローダウン / ポジション上限監視
  - kill_switch.py            — kill.flag の管理
  - monitoring_engine.py      — 各 Monitor をまとめるループ
  - alert_manager.py          —（アラート送信をまとめる, 実装に依存）
- execution/
  - execution_engine.py       — 実行エンジン本体（EngineConfig, run_session 等）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
  - broker_factory.py         — ブローカークライアント生成（Mock / 実ブローカー切替）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py               — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py        — レジーム判定（MA + マクロ NLP）
- data/                       — データ / DB のデフォルト場所（リポジトリ直下に data/ を作る想定）
- logs/                       — デフォルトのログ出力先

注意事項・運用上のヒント
------------------------
- 本番運用時は KABUSYS_ENV=live を設定し、LINE などの通知設定を必ず確認してください（validate_config の live ガードで注意喚起あり）。
- .env は絶対にリポジトリにコミットしないでください（config_setup でも警告しています）。
- AI 系機能は OpenAI の API キー（OPENAI_API_KEY）が必須。呼び出しはレート制限・エラーを考慮して設計されていますが、API 利用料に注意してください。
- run_monitoring は監視用の SQLite（SQLITE_PATH）を使います。Monitoring は KABUSYS_ENV に依存せず本番 sqlite_path を参照する点に注意してください。
- run_execution は paper_trading 時に専用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込み、本番 DB と完全分離されます。

トラブルシューティング（よくある問題）
------------------------------------
- validate_config で YAML 検証が skipped される:
  - PyYAML が未インストールのため。インストールすると config/*.yaml の構文チェックが有効になります。
- OpenAI 呼び出しで例外が出る:
  - OPENAI_API_KEY を設定しているか確認。ネットワークやレート制限によりリトライされる設計です。
- ログファイルが作成されない:
  - 権限や LOG_DIR の作成に失敗している可能性あり。setup_logging は失敗時にコンソール出力にフォールバックします。

ライセンス / バージョン
-----------------------
- パッケージバージョン: __version__ = 0.1.0（src/kabusys/__init__.py）
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

貢献
----
バグ報告・改善提案は Issue を通してお願いします。大きな変更は PR にてテストと説明を添えてください。

以上がこのコードベースの概要と基本的な利用方法です。必要であれば、各サブモジュール（ExecutionEngine、Monitoring の詳しい起動オプションや設定項目）について別途詳細ドキュメントを作成します。どの部分の詳細が欲しいか教えてください。