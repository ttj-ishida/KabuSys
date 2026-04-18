README
=====

概要
----
KabuSys は日本株自動売買のためのモジュール群を集めた小規模フレームワークです。
主な用途は以下のとおりです。

- 日次のファクター計算 / ポートフォリオ構築（research, portfolio）
- Execution Engine（発注・リスク管理・約定記録） — paper_trading と本番の分離
- 監視（システム状態、注文の滞留、ドローダウン監視）と Kill Switch
- ニュース NLP によるセンチメントスコアリング（OpenAI 利用）
- ペーパートレード検証レポート生成ツール

本リポジトリは、各機能を Pure function / 小さなコンポーネントに分割しており、
. env による設定、SQLite / DuckDB を用いたローカル永続化、および外部 API (kabuapi, J-Quants, OpenAI) との連携を想定しています。

主な機能
--------
- Execution（kabusys/run_execution.py）
  - 環境に応じて実発注か MockBroker（paper_trading）を選択
  - paper_trading 用 DB を本番 DB と分離（デフォルト: data/paper_trading.db）
  - プロセス優先度設定、PID ファイル管理、停止フラグ検出

- Monitoring（kabusys/run_monitoring.py / monitoring/*）
  - SystemMonitor: CPU/メモリ/ディスク、データ鮮度、Execution プロセス生存確認
  - TradeMonitor / RiskMonitor: 注文滞留、約定異常、ドローダウン・ポジション上限監視
  - KillSwitch: リスク条件で data/kill.flag を書き込み Execution を停止させる
  - MonitoringEngine: 上記を統合してポーリング・アラート発行

- Portfolio（kabusys/portfolio/*）
  - 銘柄選定、等重・スコア加重、セクター制限、レジーム乗数、ポジションサイズ計算

- Research（kabusys/research/*）
  - モメンタム・ボラティリティ・バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン、IC 計算、ファクター統計サマリー

- AI（kabusys/ai/*）
  - news_nlp: raw_news を OpenAI に投げて銘柄毎にセンチメントを ai_scores に格納
  - regime_detector: ETF の MA とマクロニュースの LLM スコアを合成して市場レジーム判定

- ツール
  - config_setup: 対話的 .env 生成ウィザード（python -m kabusys.config_setup）
  - validate_config: .env / config/*.yaml の検証（python -m kabusys.validate_config）
  - paper_verification_report: ペーパートレード DB から検証レポート出力（python -m kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提: Python 3.10+（typing の Union 短縮表記を使用）を想定しています。

1. リポジトリをクローン／展開
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出されます。

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 本プロジェクトで使われる主要ライブラリ:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証用、必須ではない）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がなければ上記を個別にインストールしてください）

4. 環境変数 (.env) の作成
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - あるいは手動で .env を作成（.env ファイルは絶対に Git にコミットしないでください）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 便利な環境変数（例）:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
     - LOG_LEVEL (DEBUG/INFO/...)
     - OPENAI_API_KEY（AI 機能を使う場合）

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - strict モード（警告もエラー扱い）:
     - python -m kabusys.validate_config --strict

使い方
------
いくつかの主要なスクリプトの起動方法を示します。

- 環境セットアップ（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution Engine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
    - 実行時に data/execution.pid を作成します（設定により異なる）。
    - 停止は data/stop_requested.flag の作成で行います（run_execution は停止フラグを監視して停止します）。
    - 起動時に KILL_FLAG_CLEAR_ON_START=1 だと kill.flag を自動クリアします（本番では 0 推奨）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト: 60）。
    - 例: export MONITOR_POLL_INTERVAL=30
  - 監視ループは data/stop_requested.flag の存在で停止します。
  - Monitoring は設定にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用してログを記録します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定してください（デフォルト: data/paper_trading.db）。

停止・Kill Switch
- Execution を外部から停止したい場合:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して終了します。
  - KillSwitch（監視による自動停止条件）がトリガーした場合は data/kill.flag に理由が書き込まれ、Engine は停止されます。
- Kill flag の手動クリア:
  - ファイルを削除する（rm data/kill.flag）。KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に自動クリアされますが、本番では 0 を推奨。

ロギング
- デフォルトのログディレクトリ: logs/
- setup_logging により stdout と日次ローテーションファイル（logs/<app_name>.log）へ出力します。
- LOG_DIR 環境変数で変更可能。LOG_LEVEL でログレベルを制御します。

データベース
- DuckDB: 分析用（デフォルト data/kabusys.duckdb）
- SQLite (monitoring): 監視ログ・オーダー履歴（デフォルト data/monitoring.db）
- Paper trading 用 SQLite: PAPER_TRADING_SQLITE_PATH（分離される）

主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV（development | paper_trading | live）
- DUCKDB_PATH（例: data/kabusys.duckdb）
- SQLITE_PATH（例: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用）
- LOG_LEVEL（DEBUG/INFO/…）
- OPENAI_API_KEY（AI 機能で必須）
- MONITOR_POLL_INTERVAL（監視ポーリング秒、run_monitoring 用）
- PAPER_FILL_MODE（paper_trading の Mock 動作: instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリア: 0/1）

トラブルシューティング
--------------------
- OpenAI API キー未設定:
  - AI 機能（news_nlp, regime_detector）を実行すると ValueError が発生します。OPENAI_API_KEY を設定してください。
- PyYAML 未インストール:
  - validate_config は YAML の内容検証をスキップしますが、警告が出ます。必要なら pip install pyyaml。
- ログディレクトリ作成失敗:
  - 権限等で logs/ の作成に失敗した場合、コンソール出力のみになります（警告が出力されます）。
- DuckDB / SQLite のパス:
  - .env の DUCKDB_PATH / SQLITE_PATH が指す親ディレクトリが存在しない場合、validate_config が警告を出します。起動時に自動作成されることもありますが、事前に作成しておくと安全です。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings クラス
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

サブパッケージ（代表）
- ai/
  - news_nlp.py
  - regime_detector.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py      (参照あり)
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py      (参照あり)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

（注）上記は本リポジトリで提供される主要なモジュールを抜粋したものです。実際の実装では execution 配下に broker_factory や execution_engine、order_manager など多数のモジュールが連携します。

開発メモ / 設計上のポイント
--------------------------
- Paper trading と Live の DB は分離される設計（誤発注を防ぐ）。
- 重要な外部キー（API キー等）は .env で管理。.env は決して VCS にコミットしないでください。
- 監視コンポーネントは冪等性を重視し、部分失敗時でもログや既存データを不必要に消さないように実装されています（例: ai_scores の書き込みは対象コードのみ置換）。
- OpenAI 呼び出しはリトライ/バックオフを実装し、API 失敗時はフェイルセーフ（スコア 0.0 等）で継続します。

貢献
----
バグ報告・修正提案は PR／Issue を送ってください。セキュリティ上の機密情報（API キー等）は公開せず、.env はコミットしないでください。

以上。必要があれば、README に含めるコマンド例や env のサンプルを追加で作成します。