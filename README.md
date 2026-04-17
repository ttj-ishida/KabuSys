README
======

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコードベースです。本リポジトリは以下の主要機能を含むモジュール群で構成されています。
- 発注エンジン（ExecutionEngine）
- モニタリング（System / Trade / Risk）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量探索）
- AI 補助（ニュースセンチメント／市場レジーム判定）
- ユーティリティ（設定管理、プロセス優先度など）
データ永続化には DuckDB（分析用）と SQLite（監視・発注ログ）を使用します。

主な特徴
--------
- 環境別挙動（development / paper_trading / live）に対応
  - paper_trading では MockBroker を用い、発注は data/paper_trading.db に隔離保存
- モニタリングと自動 Kill Switch（閾値超過で停止フラグを書き込み）
- ポートフォリオ構築は純関数群（テストしやすい設計）
- DuckDB を用いた高速なファクター計算・リサーチ
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロ判定機能（オプション）
- シンプルな .env ウィザードと設定検証ツール

セットアップ
----------
1. Python 仮想環境を作成して有効化
   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate
   - Windows (PowerShell):
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1

2. 必要パッケージをインストール
   - 最低限必要なパッケージ例:
     pip install duckdb psutil openai
   - YAML 検証（validate_config の config/*.yaml 検査）を使いたい場合:
     pip install pyyaml
   - 追加パッケージやバージョン管理はプロジェクト内の requirements.txt / pyproject.toml を参照してください（存在する場合）。

3. .env の作成
   - 対話式ウィザードで生成:
     python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成してください。
   - 重要: .env をバージョン管理にコミットしないでください（機密情報を含む）。

主要環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant | partial | never | reject。デフォルト: instant）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、default 60）

設定検証
-------
起動前に設定を検証できます。
- 基本検証:
  python -m kabusys.validate_config
- 警告も失敗扱い（CI 等）:
  python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------
- 設定ウィザード（.env 作成）:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config [--strict]

- ExecutionEngine（発注エンジン）起動:
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用して data/paper_trading.db に記録します。
  - 実行中に停止させたい場合、data/stop_requested.flag を作成するとエンジンが停止します。
  - エンジンは data/execution.pid に PID を書き込みます（監視でプロセス存否チェックに使用）。

- Monitoring（監視ループ）起動:
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視ログを残します。
  - 停止は data/stop_requested.flag によって制御されます。

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI キーを環境変数 OPENAI_API_KEY に設定して使用します。
  - ニューススコアリング: kabusys.ai.score_news（モジュール API）
  - レジーム判定: kabusys.ai.regime_detector.score_regime（モジュール API）
  - 直接 CLI 実行用ラッパーは含まれていませんが、これら関数をスクリプトから呼び出すことで利用可能です。

停止・Kill Switch の仕組み
------------------------
- run_execution / run_monitoring はプロジェクト内 data/stop_requested.flag を監視して安全に停止します。
- KillSwitch（監視モジュール内）は条件により data/kill.flag を作成し、ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動でクリアする挙動を許容しますが、本番では 0 を推奨します。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
  - パッケージ定義（__version__ 等）
- config.py
  - 環境変数と .env 自動読み込みロジック、Settings クラス
- config_setup.py
  - .env 作成対話ウィザード
- validate_config.py
  - 設定検証 CLI

- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading では DB を分離）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト

- execution/
  - execution_engine.py, order_manager.py, order_repository.py, broker_factory.py, reconciler.py, risk_manager.py ...
  - 発注処理・リスク制御・注文管理の実装（主に発注ロジック） — （一部ファイルはサンプル参照コード）

- monitoring/
  - monitoring_db.py
    - SQLite による監視ログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py
    - システム状態監視、取引監視、リスク判定、アラート管理、Kill Switch など

- portfolio/
  - portfolio_builder.py
    - 候補選定・等重/スコア重み付け関数
  - position_sizing.py
    - 株数計算、単元株丸め、資金配分ロジック
  - risk_adjustment.py
    - セクターキャップ、レジーム乗数など

- research/
  - factor_research.py
    - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 接続を使用）
  - feature_exploration.py
    - 将来リターン、IC 計算、統計サマリー等

- ai/
  - news_nlp.py
    - raw_news を集約して OpenAI で銘柄ごとのセンチメントを算出し ai_scores に書き込む
  - regime_detector.py
    - ETF MA200 値とマクロニュースセンチメントを組み合わせて市場レジームを算出

- tools/
  - paper_verification_report.py
    - Paper Trading の稼働・注文・レイテンシ指標を集計してレポート出力

- utils/
  - process_priority.py
    - psutil を用いたプロセス優先度 / CPU affinity 設定ユーティリティ

データ / ファイル（プロジェクトルート）
- data/kabusys.duckdb (デフォルト DUCKDB_PATH)
- data/monitoring.db (デフォルト SQLITE_PATH)
- data/paper_trading.db (paper_trading 用)
- data/execution.pid (ExecutionEngine が書き込む PID)
- data/kill.flag (Kill Switch が書き込む停止フラグ)
- data/stop_requested.flag (手動停止用フラグ。run_* スクリプトはこの存在を見て停止)

注意事項 / ベストプラクティス
----------------------------
- 機密情報（API トークン、パスワード等）は .env に保存してもよいですが、決して Git にコミットしないでください。
- 本番（KABUSYS_ENV=live）では設定値（LINE 通知、KILL_FLAG_CLEAR_ON_START など）を十分に検証してください。validate_config は本番リスクを検出するチェックを提供します。
- OpenAI を用いるモジュールは API キーと利用料金が必要です。使用前に OPENAI_API_KEY を設定してください。
- paper_trading モードは発注をシミュレートし、発注ログを分離 DB に残すため本番 DB を汚染しません。

トラブルシューティング
----------------------
- .env 自動ロードを無効化したい場合:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストやコンテナ化で有用）。
- MONITOR_POLL_INTERVAL に不正な値を入れるとデフォルト（60 秒）にフォールバックします。
- DuckDB / SQLite のパスの親ディレクトリが無い場合、起動時に自動作成されるケースがあります。validate_config は親ディレクトリの存在を警告します。

貢献・拡張
-----------
- ファクターやストラテジーの追加は research/ 以下に純関数として実装し、ExecutionEngine 側で組み合わせる設計を推奨します。
- Broker クライアントの追加は execution/broker_factory.py を拡張してください（Mock と実ブローカを切替可能にする設計）。
- アラートの実装（LINE 以外）やアダプタは monitoring/alert_manager.py を実装・拡張してください。

ライセンス・その他
------------------
- 本リポジトリのライセンス情報はプロジェクトルートの LICENSE（存在する場合）を参照してください。

以上が基本的な README 内容です。必要であれば、導入手順に合わせた具体的なコマンド例（systemd ユニット、docker-compose、CI 設定例）や各モジュールの API 仕様（関数シグネチャ）を追記します。どの部分を詳細化しましょうか？