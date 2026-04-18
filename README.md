README
======

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤のサンプル実装です。本リポジトリは以下の責務を持つコンポーネント群で構成されています。

- 実行エンジン (ExecutionEngine)：発注・約定管理、リスク管理を行う（paper_trading モードではモックブローカを使用して本番 DB と分離）
- 監視（Monitoring）：システム状態・注文状態・リスクをポーリングしてログ／アラート／Kill Switch を扱う
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算・セクター制限等）
- リサーチ（ファクター計算・特徴量探索）
- AI 補助（ニュース NLP によるセンチメント評価、市場レジーム判定）
- ユーティリティ（ロギング設定、プロセス優先度設定など）
- CLI ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

特徴
----
主な機能一覧（抜粋）:

- 環境設定ウィザード（python -m kabusys.config_setup）による .env 生成/更新
- 起動前の設定検証（python -m kabusys.validate_config）
- ExecutionEngine の起動（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と完全分離
- Monitoring の起動（python -m kabusys.run_monitoring）
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（デフォルト 60 秒）で上書き可能
  - 停止は data/stop_requested.flag または data/kill.flag を利用
- Paper Trading の検証レポート生成（python -m kabusys.tools.paper_verification_report）
- DuckDB を用いた時系列・財務データ処理（research/*.py）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価 / レジーム判定（環境変数 OPENAI_API_KEY を使用）
- ログは stdout と日次ローテートファイル（logs/<app>.log）へ出力
- プロセス優先度・CPU affinity のクロスプラットフォーム設定（psutil ベース）

前提 / 必要な依存
-----------------
推奨 Python バージョン: 3.10+

主な Python パッケージ（最低限）:
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証を行う場合に必要）

インストール例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. リポジトリをクローン
    git clone <repo-url>
    cd <repo-root>

2. Python 仮想環境の準備と依存のインストール（上記参照）

3. .env の作成（ウィザード推奨）
    python -m kabusys.config_setup

   ウィザードは .env を対話的に作成します。作成後は設定検証を実行してください:

    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict  # 警告も失敗扱いにする

4. データディレクトリの作成（必要時）
   デフォルトの DB / PID / フラグは data/ 以下を参照します。必要に応じて .env の DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を変更してください。

主要な環境変数（まとめ）
-----------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - paper_trading: 発注はモック、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）。デフォルト: INFO
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

使い方（起動例）
----------------

- .env を用意したら設定を検証:
    python -m kabusys.validate_config

- ExecutionEngine を起動:
    python -m kabusys.run_execution

  - 起動時にプロセス優先度を "high" に設定します。
  - KABUSYS_ENV=paper_trading の場合は paper 用 DB に記録します。
  - 停止: data/stop_requested.flag を作成すると安全に停止します。Kill Switch が発動すると data/kill.flag が作成されます。

- Monitoring を起動:
    python -m kabusys.run_monitoring

  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更できます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は常に本番用の sqlite_path を参照します（環境にかかわらず）。

- Paper Trading 検証レポートを生成:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを明示することも可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）。

- .env の対話式生成:
    python -m kabusys.config_setup

- 設定検証（CI 等で利用）:
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

停止 / フラグファイル
--------------------
- data/stop_requested.flag: run_monitoring / run_execution のループを終了させるための外部停止フラグ（存在を検出すると安全に終了します）。
- data/kill.flag: KillSwitch（監視）によって作成される停止フラグ。ExecutionEngine はこのフラグの存在に応じて動作を停止します。
- data/execution.pid: ExecutionEngine の PID を書く場所（実装上の既定値）。

ログ
---
- logging_setup により stdout と logs/<app_name>.log（日次ローテーション）へ出力します。
- デフォルトログディレクトリ: logs/
- ログレベルは .env の LOG_LEVEL または setup_logging の引数で制御できます。

ディレクトリ構成（主要ファイル）
--------------------------------
以下はソースツリー（src/kabusys 以下）の主要モジュールと簡単な説明です。

- __init__.py
- config.py
  - Settings クラス: 環境変数 / .env 自動読み込み / 各種設定アクセス
- config_setup.py
  - .env 対話ウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト（プロセス優先度設定・DB 接続・スレッド管理）
- run_monitoring.py
  - SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL に対応）
- utils/
  - logging_setup.py: ログ設定ユーティリティ
  - process_priority.py: プロセス優先度 / CPU affinity 設定（psutil ベース）
- monitoring/
  - monitoring_db.py: SQLite のスキーマ初期化・永続化 API（system_status, trade_logs, positions, risk_logs, dashboard 等）
  - system_monitor.py: システム状態・データ鮮度チェック
  - trade_monitor.py: （注文関連監視、コードベースに含まれる）
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag の生成 / クリア
  - alert_manager.py: （アラート送信を管理、実装により LINE 等に通知）
  - monitoring_engine.py: 各モニタの統括ループ
- execution/
  - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
    （Execution エンジンと関連の発注・リスク評価ロジック）
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    （候補選定、重み付け、サイズ計算、セクター制限、レジーム乗数）
- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン計算、IC 計算、統計サマリー
- ai/
  - news_nlp.py: ニュース記事を OpenAI でスコア化し ai_scores テーブルへ書込み
  - regime_detector.py: ETF の MA とマクロニュースで市場レジーム判定
- tools/
  - paper_verification_report.py: Paper Trading 検証レポート生成（SQLite 参照）

開発メモ / 注意事項
------------------
- .env は機密情報（API トークン等）を含むため、絶対に Git にコミットしないでください。
- KABUSYS_ENV=live の場合は設定を慎重に確認してください。validate_config にて本番向けガードを行っています。
- AI 機能（news_nlp / regime_detector）は OpenAI API を呼び出します。API キーとコストに注意してください。API 呼び出しはリトライやフォールバックロジックを備えていますが、失敗した場合は安全なデフォルト（例: macro_sentiment=0.0）で続行します。
- DuckDB は大規模時系列データの分析に用います。prices_daily / raw_financials / raw_news 等のテーブルを前提にしています。
- 実行スクリプトはプロセス優先度を "high" に設定しますが、権限や OS により設定できない場合があるため、その場合は警告をログに出します。

貢献 / 拡張案
-------------
- order_manager / broker_interface の実装を任意のブローカー API に合わせて拡張
- テスト用モックの充実（OpenAI 呼び出し、ブローカークライアント等）
- 単体テスト・CI の追加（validate_config を CI に組み込む等）
- 銘柄別 lot_size をサポートするためのマスタデータ導入（position_sizing の TODO）

ライセンス / 著作権
------------------
（本リポジトリのライセンス・著作権情報をここに記載してください）

お問い合わせ
------------
実装に関する質問や改善提案はリポジトリの Issue にてお願いします。