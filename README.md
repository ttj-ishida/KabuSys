KabuSys — 日本株自動売買システム
===============================

このREADME はリポジトリ内の主要スクリプト・モジュールをもとに作成した概要ドキュメントです。実行前に必須環境変数の設定や依存ライブラリのインストールを行ってください。

プロジェクト概要
----------------
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）による注文発行・リスク管理
- 監視モジュール（Monitoring）によるシステム状態・注文状況・リスクの巡回確認と Kill Switch
- ポートフォリオ構築（選定、重み付け、ポジションサイズ決定、セクター制限）
- 研究モジュール（ファクター計算、特徴量探索、IC 計算）
- AI モジュール（ニュースを LLM でスコアリング、レジーム判定）
- ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）
- Paper Trading 用レポート生成ツール

機能一覧
--------
- 環境設定ウィザード: python -m kabusys.config_setup による .env 生成/更新
- 設定検証: python -m kabusys.validate_config による環境変数 / config/*.yaml の事前チェック
- 実行エンジン起動: python -m kabusys.run_execution （KABUSYS_ENV に応じて本番／ペーパーを切替）
- 監視ループ起動: python -m kabusys.run_monitoring （システム／トレード／リスク監視）
- Paper Trading レポート: python -m kabusys.tools.paper_verification_report
- ポートフォリオ構築関数群: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- 研究機能: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary
- AI: news_nlp.score_news（ニュースセンチメントを書き込み）、regime_detector.score_regime（市場レジーム判定）
- DB 永続化レイヤー: SQLite を用いた監視ログ（monitoring_db.py）
- ロギング: ログは stdout と logs/<app_name>.log（日次ローテーション）に出力

前提・依存関係
--------------
- Python >= 3.10（Union 型等の構文を使用）
- 主要 Python パッケージ（例）:
  - duckdb
  - psutil
  - openai（AI 機能を利用する場合）
  - PyYAML（config/*.yaml の検証を行う場合に推奨）
- SQLite（Python 標準ライブラリの sqlite3 を使用）
- 環境に依存する追加設定（kabuステーション API 等）

（注）requirements.txt はこのコードスニペットには含まれていません。以下のように必要パッケージをインストールしてください:
pip install duckdb psutil openai PyYAML

セットアップ手順
---------------
1. Python（推奨 3.10+）をインストールする。

2. 依存ライブラリをインストールする:
   - 例:
     pip install duckdb psutil openai PyYAML

3. リポジトリルートで .env を作成（推奨: ウィザードを利用）:
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 重要なその他の環境変数（主なもの）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（default: data/paper_trading.db）
     - OPENAI_API_KEY — AI 機能を使用する場合に必要
     - LOG_LEVEL — default: INFO
     - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか (0/1)

4. 設定検証（任意）:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで終了コード 1 を返します。

5. ログ・データディレクトリを作成（通常は自動作成されますが、事前に作る場合）:
   - data/
   - logs/

使い方（実行例）
----------------

- 実行エンジン（ExecutionEngine）を起動:
  - 本番環境の想定:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - ペーパートレードで起動（MockBroker を用い DB 分離）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 備考:
    - paper_trading モードでは MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存されます。
    - 実行中には execution.pid（デフォルト data/execution.pid）が作成されます。
    - data/stop_requested.flag や data/kill.flag による停止制御が組み込まれています。

- 監視ループを起動:
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は常に本番用 sqlite_path を使用して監視テーブルに記録します（KABUSYS_ENV に依存しない）。
  - 監視は data/stop_requested.flag の存在で停止します。

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- 環境設定ウィザード:
  python -m kabusys.config_setup

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db。--db でパス指定可能。

- AI 機能（プログラムで呼び出す例）:
  - ニューススコアリング（DuckDB 接続を渡す）:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

主要ファイル / ディレクトリ構成
-----------------------------
（リポジトリルートを PROJECT_ROOT としたときの想定構成。ソースは src/kabusys 以下に配置されています）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings クラス（自動 .env ロード機能）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py     — マクロ + ETF MA200 を用いた市場レジーム判定

  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化・永続化API (MonitoringDB)
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py       — 発注ログ・約定監視（概念的に存在）
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — data/kill.flag を書く KillSwitch
    - monitoring_engine.py   — 複数モニタを束ねる実行ループ
    - alert_manager.py       — 通知管理（LINE 等）※（存在を示すが省略されている可能性あり）

  - execution/
    - execution_engine.py    — ExecutionEngine 本体（起動・セッション管理）
    - order_manager.py       — 注文管理
    - order_repository.py    — 注文の DB 永続化
    - reconciler.py          — 注文の突合せ
    - risk_manager.py        — リスク制御ロジック
    - broker_factory.py      — BrokerClient の生成（本番/モック切替）

  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 発注株数計算・集計キャップ処理
    - risk_adjustment.py     — セクター上限・レジーム乗数

  - research/
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー計算

  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート

  - utils/
    - logging_setup.py       — ロギング初期化（stdout + 日次ファイルローテーション）
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ

- config/
  - *.yaml                  — 設定テンプレート（system_config.yaml など、validate_config で確認）

- data/
  - monitoring.db           — 監視用 SQLite（デフォルト）
  - paper_trading.db        — ペーパートレード用 DB（paper_trading モード）
  - execution.pid           — 実行中 PID ファイル
  - kill.flag / stop_requested.flag — 停止制御フラグ（Kill Switch / 停止要求）

- logs/
  - execution.log
  - monitoring.log
  - ...                     — 日次ローテーションで過去ログを保持

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では全ての設定（特に API トークン、LINE 通知設定）を慎重に確認してください。validate_config にて本番向けチェックが入ります。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は本番運用で危険な可能性があるためデフォルトは 0（無効）を推奨します。
- monitor と execution はそれぞれ data/stop_requested.flag により安全に停止できます。KillSwitch はリスクイベントに応じて data/kill.flag を書き込み ExecutionEngine を停止させます。
- ログディレクトリの作成に失敗した場合でも stdout 出力は継続されますが、ログファイルは作成されません。

トラブルシューティング
---------------------
- .env が読み込まれない場合:
  - Settings はプロジェクトルートを .git または pyproject.toml から探索して .env/.env.local を自動ロードします。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB / SQLite 周り:
  - DuckDB の接続パスは Settings.duckdb_path（デフォルト data/kabusys.duckdb）。monitoring は常に本番 sqlite_path を参照する点に注意してください。

- AI 呼び出し (OpenAI):
  - OPENAI_API_KEY が必須です。API 呼び出しはリトライやフォールバック（失敗時はゼロやスキップ）を多用してフェイルセーフ設計になっていますが、API のレート制限や料金に留意してください。

貢献・拡張
----------
- strategy / execution / monitoring の個別コンポーネントはモジュール単位で交換・テスト可能です。AI モジュールは外部 API 依存箇所を差し替えやすく設計されています（テスト時は API 呼び出し関数を patch することを想定）。

ライセンス・その他
------------------
- この README はコードスニペットに基づく技術ドキュメントです。実際のライセンス情報・詳細な運用手順・設計ドキュメントはリポジトリ内の別ファイル（LICENSE、docs/ 等）を参照してください。

以上。必要なら、この README をベースに「導入手順をより細かく」「実行例ログを含めて」「運用チェックリストを追加」など、目的に合わせて追記します。どの内容を詳しくしたいか教えてください。