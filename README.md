KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買システム（KabuSys）のコードベースです。
本 README ではプロジェクトの概要、主要機能、セットアップ手順、実行方法、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
---------------
KabuSys は以下の機能を持つ自動売買システムのモジュール群です。

- データインジェスト / DuckDB を用いたファクター計算（research）
- ポートフォリオ構築・ポジションサイジング（portfolio）
- 発注エンジン（ExecutionEngine、ブローカークライアント抽象化、ペーパートレード対応）
- リスク監視 / Kill Switch（monitoring）
- AI を使ったニュースセンチメント評価（OpenAI 経由、ai）
- 運用ユーティリティ（ログ設定・プロセス優先度設定・設定ウィザード等）
- 検証用ツール（Paper Trading 検証レポート等）

設計上のポイント
- DuckDB は分析用データベース、SQLite は監視・注文ログ用に使用。
- Paper Trading は本番 DB と分離され、環境変数により専用 SQLite が使用されます。
- .env ファイルを自動読み込み（プロジェクトルート検出）する仕組みがありますが、無効化可能です。
- 実行スクリプトはパッケージ内のモジュールとして提供（python -m kabusys.xxx 形式で実行）。

主要機能一覧
---------------
- 環境設定ウィザード: kabusys.config_setup（対話式で .env を作成）
- 設定検証 CLI: kabusys.validate_config（.env と config/*.yaml を事前チェック）
- 実行エンジン起動: kabusys.run_execution（本番 / paper_trading モード対応）
- 監視ループ起動: kabusys.run_monitoring（SystemMonitor をポーリング）
- Paper Trading 検証レポート: kabusys.tools.paper_verification_report
- ニュース NLP（OpenAI）: kabusys.ai.score_news（raw_news を評価して ai_scores に書き込み）
- 市場レジーム判定（AI + MA200）: kabusys.ai.regime_detector.score_regime
- ポートフォリオ構築: select_candidates / calc_equal_weights / calc_score_weights
- ポジションサイズ計算: calc_position_sizes（複数アルゴリズム対応）
- 監視 DB 層: monitoring.monitoring_db（SQLite テーブル生成・読み書きユーティリティ）
- ログ設定ユーティリティ: utils.logging_setup（コンソール + 日次ローテート）

前提条件
---------
- Python 3.10+（型ヒント等に合わせて）
- 必須パッケージ（代表例）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（設定ファイル検証を行う場合）
- （環境に応じて）kabuステーション API の接続情報、J-Quants API トークンなど

セットアップ手順
----------------

1. リポジトリをクローン
   - git clone <repo_url>
   - リポジトリルートに移動（pyproject.toml または .git がある場所がプロジェクトルートとして認識されます）

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は最低限 duckdb, psutil はインストールしてください:
     - pip install duckdb psutil

4. 環境変数設定（.env の作成）
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいはプロジェクトルートに .env を手動で作成してください。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN：J-Quants API リフレッシュトークン（必須）
     - KABU_API_PASSWORD：kabuステーション API パスワード（必須）
   - その他の重要な変数（任意/デフォルトあり）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
     - OPENAI_API_KEY: OpenAI を使う場合に設定
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR（デフォルト: INFO）
     - LOG_DIR: ログ保存先（デフォルト: logs/）

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も FAIL 扱いになります。

使い方（主要コマンド）
---------------------

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 動作モードは KABUSYS_ENV で制御:
    - paper_trading: MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - live: 本番ブローカーを使用（注意して実行）
  - 起動前に data/stop_requested.flag が存在する場合は起動をスキップします。
  - 実行中は data/stop_requested.flag を作成することで停止シグナルを送れます。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 監視は常に本番 sqlite_path を使用（環境にかかわらず）
  - 停止は data/stop_requested.flag を作成することで行います。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI 機能（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news と news_symbols を集約し OpenAI API による評価を行い ai_scores に書き込みます。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成して market_regime に保存します。
  - API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。

重要な挙動・運用上の注意
-----------------------
- Paper Trading は本番データベースと分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- 実行中はプロセス優先度を "high" に設定しようとします（utils.process_priority）。
  - 権限や OS によっては設定に失敗することがあり、その場合は警告を出して続行します。
- Kill Switch:
  - RiskMonitor 等が基準を超えた場合、KillSwitch が data/kill.flag を書き込み Execution 停止のトリガーを生成します。
  - 本番では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（自動クリアは危険）。
- 停止フラグ:
  - run_execution/run_monitoring は data/stop_requested.flag の存在を監視して優雅にシャットダウンします。
- ログ:
  - kabusys.utils.logging_setup により標準出力と日次ローテーションファイル（logs/<app_name>.log）にログが出力されます。
  - LOG_DIR 環境変数でログディレクトリを変更できます。

設定（主な環境変数とデフォルト）
--------------------------------
- JQUANTS_REFRESH_TOKEN — 必須
- KABU_API_PASSWORD — 必須
- KABUSYS_ENV — development / paper_trading / live（default: development）
- DUCKDB_PATH — data/kabusys.duckdb
- SQLITE_PATH — data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — data/paper_trading.db
- PAPER_FILL_MODE — instant | partial | never | reject（default: instant）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- LOG_LEVEL — INFO（デフォルト）
- LOG_DIR — logs/
- PID_FILE_PATH — data/execution.pid（ExecutionEngine の PID ファイル）
- KILL_FLAG_PATH — data/kill.flag
- KILL_FLAG_CLEAR_ON_START — 0/1（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒）

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要モジュールと役割の一覧です（抜粋）。

- __init__.py
  - パッケージ定義（バージョン等）

- config.py
  - 環境変数 / .env 自動ロードと Settings クラスを提供

- config_setup.py
  - .env を対話式に作成するウィザード

- validate_config.py
  - 起動前設定の静的チェック CLI

- run_execution.py
  - ExecutionEngine を起動するスクリプト（KABUSYS_ENV に応じたブローカー切替、停止フラグ対応）

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔指定可）

- utils/
  - logging_setup.py: 共通ログ設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

- monitoring/
  - monitoring_db.py: SQLite による監視ログ永続化（テーブル作成・CRUD）
  - system_monitor.py: システムリソース・データ鮮度監視
  - trade_monitor.py: （trade 関連の監視、滞留／約定異常検出 等）
  - risk_monitor.py: ドローダウン／ポジション上限監視
  - kill_switch.py: kill.flag の作成 / 判定
  - monitoring_engine.py: 各 Monitor を束ねる実行エンジン
  - alert_manager.py: （アラート送信管理: LINE 等）

- execution/
  - ExecutionEngine / OrderManager / RiskManager / Reconciler / broker_factory 等（発注ロジック）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 株数計算・キャップ適用
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン・IC 計算など

- ai/
  - news_nlp.py: ニュース NLP（OpenAI）で銘柄ごとセンチメント算出と ai_scores 書込
  - regime_detector.py: ETF MA + マクロニュースで市場レジーム判定

- tools/
  - paper_verification_report.py: Paper Trading の検証レポートを生成

- data/ （ランタイムで作成されるデータディレクトリ）
  - monitoring.db（デフォルト） / paper_trading.db / kill.flag / stop_requested.flag / execution.pid など

追加情報 / 運用ヒント
---------------------
- 本番運用時（KABUSYS_ENV=live）は特に設定とアラート受信設定（LINE など）を要確認してください。
- .env は機密情報を含むため絶対に Git にコミットしないでください。
- Docker / systemd 等でデーモン運用することを想定して PID ファイルやログディレクトリ、stop/kill フラグの適切な配置を検討してください。
- AI 機能は外部 API を用いるため、レート制限や失敗時のフォールバック（ログ／スキップ）挙動を理解した上で運用してください。

ライセンス / コントリビューション
---------------------------------
（ここにライセンス情報や貢献方法を書いてください。リポジトリに LICENSE ファイルがあればその内容に従ってください。）

以上が本リポジトリの概要と使い方の要約です。細かい実装や追加のスクリプトは各モジュールの docstring / 関数コメントを参照してください。必要であれば README を拡張して CI/デプロイ手順や systemd ユニット例なども追記できます。