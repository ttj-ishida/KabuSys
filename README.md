README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ用ライブラリ兼サービス群です。本リポジトリは以下の責務を持つ複数モジュールから構成されています。

- 実行エンジン（ExecutionEngine）: 発注・約定管理・リスク管理を行うランタイム
- 監視（Monitoring）: システム稼働状態・注文状態・リスクを定期チェックし、Kill Switch を発動する
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ算出
- リサーチ: ファクター計算・特徴量探索・IC 等の統計処理
- AI 補助: ニュースの NLP スコアリング・市場レジーム判定（OpenAI を利用）
- ユーティリティ: 設定管理・ログ設定・プロセス優先度制御 等

本 README はこのコードベースの使い方、設定、主要構成をまとめたドキュメントです。

主な機能一覧
--------------
- 実行（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカー抽象化（paper_trading は専用 DB に分離）
  - RiskManager / OrderManager / Reconciler を組み合わせた ExecutionEngine 起動
  - 停止フラグ（data/stop_requested.flag）による安全停止
- 監視（run_monitoring.py, monitoring/*）
  - SystemMonitor: CPU/メモリ/ディスク・データ鮮度・実行プロセスの死活監視
  - TradeMonitor / RiskMonitor: 滞留注文、約定異常、ドローダウン・ポジション上限監視
  - MonitoringEngine: 上記モニタを束ねてポーリング、AlertManager（通知）/KillSwitch 連携
  - SQLite ベースの監視 DB（monitoring_db.py）を初期化・永続化
- ポートフォリオ（portfolio/*）
  - 銘柄選定（select_candidates）
  - 重み計算（等分配 / スコア加重）
  - セクターキャップ適用、レジーム乗数、ポジションサイズ算出（単元丸め・上限等を考慮）
- リサーチ（research/*）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily/raw_financials を参照）
  - 将来リターン計算、IC 計測、統計サマリ
- AI（ai/*）
  - news_nlp.score_news: raw_news をまとめて OpenAI に投げ、銘柄ごとの ai_score を ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM スコアを合成して market_regime を算出・書込
  - API 呼び出しは堅牢化（リトライ・バリデーション・スコアクリップ等）
- ツール
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前チェック（必須環境変数・ファイル存在・YAML パース等）
  - tools/paper_verification_report: ペーパートレード結果の集計・PASS/FAIL レポート生成
- ユーティリティ（utils/*）
  - logging_setup: 統一ログ設定（コンソール + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - config: .env 自動読み込み・Settings クラスによる環境変数管理

セットアップ手順
----------------
以下はローカル環境で動かすための基本手順（Linux / macOS / Windows 共通概念）。

1. リポジトリをチェックアウト
   - プロジェクトルートには src/kabusys 以下が存在します。

2. Python 環境準備（例）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合、少なくとも次を入れてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（validate_config で YAML 検証を行いたい場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env を作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成（主要キーは下記参照）。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 厳格チェック（警告も FAIL）:
     - python -m kabusys.validate_config --strict

6. データディレクトリ
   - デフォルトでいくつかのファイルを data/ に作成します（logs/ も作成されます）。
   - 実行前に permissions を確認してください。

主要な環境変数（.env）
---------------------
（主要項目。config_setup で自動生成されるテンプレートに沿っています）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR)（デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START (0/1)（本番は 0 推奨）
- OPENAI_API_KEY（AI 機能利用時に必須）

監視・停止フラグ
----------------
- run_monitoring / run_execution は data/stop_requested.flag の存在をチェックして安全停止します。
  - run_monitoring はプロジェクトルートから data/stop_requested.flag を確認します。
  - run_execution は起動中スレッド監視と stop flag を組み合わせて停止します。
- Kill Switch（運用上の強制停止）:
  - Settings.kill_flag_path の既定は data/kill.flag
  - KillSwitch.evaluate がトリガー条件を満たすと flag を書き込み、ExecutionEngine が停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番は推奨しない）。

ログ
---
- ログは logs/<app_name>.log に日次ローテーションで保存されます（デフォルトで 30 日保持）。
- 起動時に共通の logging_setup.setup_logging(app_name="execution" など) を呼んで統一管理します。
- 標準出力（stdout）にも同じログが出力されます。

使い方（主要コマンド）
--------------------

- 環境ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告もエラー扱い）:
    - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 MockBroker を利用し、data/paper_trading.db に記録します。
  - 実行中に data/stop_requested.flag を置くと安全に停止します。

- 監視プロセス起動
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定できます（デフォルト: 60）。
  - python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB ファイルを指定可能。未指定時は PAPER_TRADING_SQLITE_PATH 環境変数または data/paper_trading.db を参照。

- AI 機能（プログラム中から呼ぶ）
  - ニューススコアリング:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key 引数または OPENAI_API_KEY を使用
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- ライブラリ利用（リサーチ / ポートフォリオ関数）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主なファイル / ディレクトリです（抜粋）。

- __init__.py
- config.py                — Settings クラス・.env 自動ロード
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 起動前チェック CLI

- run_execution.py         — 実行エンジン起動スクリプト
- run_monitoring.py        — 監視ループ起動スクリプト

- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度・CPU affinity
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義・永続化 API
  - system_monitor.py
  - trade_monitor.py       — （実装あり。コードベースに含まれる）
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py       — （アラート送信ロジック: LINE 等）
- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py
  - regime_detector.py
- tools/
  - paper_verification_report.py

（注）上記の一部ファイルは抜粋や参照用で、実際のリポジトリに含まれるサブモジュールや追加ファイルがある場合があります。

運用上の注意
--------------
- KABUSYS_ENV=live の場合は本番扱いになります。LINE 通知や Kill Switch の設定を十分に確認してください。
- .env は機密情報（API トークン / パスワード）を含むため Git にコミットしないでください。
- OpenAI API を使う機能はコストとレイテンシが発生します。rate limit やエラーに備えた設定（_MAX_RETRIES 等）を確認してください。
- psutil によるプロセス優先度変更は権限に左右されます。適切な権限の下で動作させてください。
- DuckDB / SQLite ファイルは適切にバックアップしてください（特に本番 DB）。

トラブルシュート
-----------------
- ログが作成されない場合: LOG_DIR / logs/ ディレクトリの作成権限を確認。setup_logging は作成に失敗するとコンソールのみで継続します。
- .env 自動ロードが動かない場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか、プロジェクトルートが検出できるか（.git または pyproject.toml が必要）を確認。
- モジュール間の DuckDB スキーマ不整合やテーブル不足は validate_config の YAML/DB path チェックや MonitoringDB.init で一部対応しています。必要に応じてスキーマ初期化処理を実行してください。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（初期値）。ライセンスはリポジトリの LICENSE を参照してください（本 README には含まれていません）。

参考コマンド一覧（まとめ）
-------------------------
- 仮想環境作成:
  - python3 -m venv .venv && source .venv/bin/activate
- 依存インストール（一例）:
  - pip install duckdb psutil openai PyYAML
- .env 作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行起動:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

補足
----
この README は現状のソースコードから推測できる設計意図・使い方をまとめたものです。内部実装の詳細や追加の設定項目は該当モジュールの docstring（各ファイル冒頭コメント）を参照してください。必要であれば各機能のサンプルや詳細手順をさらに追記します。