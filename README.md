KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究・監視を支援する Python 製のモジュール群です。本コードベースは以下の主要機能を含みます。

- 実行エンジン（ExecutionEngine）の起動スクリプト（本番 / ペーパートレード切替）
- 監視（Monitoring）サブシステム（システム状態・注文・リスク監視、Kill Switch）
- ポートフォリオ構築・ポジションサイズ計算などの純粋関数群
- 研究用モジュール（ファクター計算・特徴量解析）
- ニュース NLP / レジーム判定（OpenAI を利用したセンチメント評価）
- ユーティリティ（ロギング設定、プロセス優先度設定、設定ウィザード・検証ツール）
- 運用向けツール（Paper Trading 検証レポート生成等）
- 監視ログ保存用の SQLite 層（monitoring_db）

主な特徴
--------
- 環境（KABUSYS_ENV）に応じた振る舞い（development / paper_trading / live）
- ペーパートレード時は MockBroker を使い、DB を本番から分離（data/paper_trading.db）
- .env ウィザード（config_setup）と起動前検証（validate_config）で安全にセットアップ
- OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント・レジーム判定機能（API キー必要）
- ロギングは統一インターフェース（console + 日次ローテーションファイル）
- 監視サブシステムは kill.flag による外部停止シグナルや各種アラート発行をサポート

必要条件
--------
- Python 3.10 以上（PEP 604 の型 | を使用）
- 推奨パッケージ（pip でインストール）:
  - duckdb
  - openai
  - psutil
  - pyyaml（config 検証で YAML をパースする場合）
- SQLite3 は標準ライブラリで利用

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ...（リポジトリ URL）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate   （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - （requirements.txt がある場合）pip install -r requirements.txt
   - ない場合:
     pip install duckdb openai psutil pyyaml

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成後、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を確認してください。

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - --strict フラグを付けると警告も失敗扱いになります。

6. data/ および logs/ ディレクトリの確認
   - デフォルトの DB や PID/flag ファイルは data/ 以下に作られます。必要なら権限や配置を調整してください。
   - ログは logs/<app_name>.log に日次ローテートで出力されます。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading モード時）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使うときに必要）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動でクリアするか（デフォルト 0）
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（コマンド例）
-------------------
- 環境作成ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動（本番/ペーパーは KABUSYS_ENV で制御）:
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ※ 実行中に停止させたい場合は data/stop_requested.flag を作成するか、監視側の kill.flag を利用してください。
  ※ ExecutionEngine はデフォルトで data/execution.pid を作成します（設定で変更可）。

- Monitoring（監視ループ）起動:
  export MONITOR_POLL_INTERVAL=60   # 省略時は 60 秒
  python -m kabusys.run_monitoring
  ※ 監視は本番 sqlite_path（SQLITE_PATH）を使用してログを残します（KABUSYS_ENV に依らず本番 DB を参照）。

- Paper Trading 検証レポート生成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  または
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（Python API 利用例）
  from openai import OpenAI
  import duckdb
  from kabusys.ai import score_news, score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # news スコアを生成（target_date は datetime.date オブジェクト）
  count = score_news(conn, target_date, api_key="sk-...")

  # レジーム判定
  score_regime(conn, target_date, api_key="sk-...")

運用上のポイント / 注意
---------------------
- ペーパートレード: KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。本番 DB と分離されるため安全です。
- Kill Switch: リスク条件が満たされると monitoring が data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。KillSwitch は冪等（既に存在すれば上書きしない）です。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START=1 とすると自動クリアしますが、本番では推奨されません。
- 監視停止（強制終了）: data/stop_requested.flag を作成すると run_monitoring/run_execution のループが検知して終了します。
- ロギング: logs/ 配下にアプリ別ログが日次ローテーションで保存されます。ログディレクトリが作れない場合はコンソールのみになります。
- OpenAI 利用: API 呼び出しはリトライロジックやバリデーションを備えていますが、API キーや料金に注意してください。AI モジュールは外部 API に依存するためフェイルセーフ（失敗時は中立値で継続）を実装しています。

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数読み込み・Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring ポーリング起動スクリプト

パッケージ / サブモジュール
- ai/
  - news_nlp.py            — ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py     — マーケットレジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py       — SQLite 用永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py      — システム状態 / データ鮮度監視
  - trade_monitor.py       — （実装内の取引監視ロジック）
  - risk_monitor.py        — ドローダウン / ポジション上限監視
  - kill_switch.py         — kill.flag 書き込みロジック
  - monitoring_engine.py   — 各モニター束ねるエンジン
  - alert_manager.py       — （アラート通知ロジック: LINE 等）
- execution/
  - execution_engine.py    — ExecutionEngine（セッション制御・注文処理）
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py   — 候補選定・重み付け
  - position_sizing.py     — 発注株数決定ロジック
  - risk_adjustment.py     — セクター上限・レジーム乗数
- research/
  - factor_research.py     — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py — forward returns, IC, 統計サマリー
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成
- utils/
  - logging_setup.py       — ロギング初期化ユーティリティ
  - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

補足
----
- code 内に各種設計注釈・フェイルセーフ・互換性配慮のコメントが多数含まれています。運用時は config/*.yaml（存在すれば）や .env を適切に設定した上で起動してください。
- config 検証ツールは PyYAML が無ければ YAML 内容の検証をスキップします（警告が出ます）。可能なら pyyaml を入れておくと便利です。

貢献 / 開発
------------
- 変更を加える際はユニットテストやローカルでの動作確認を行ってください。
- 本番環境（KABUSYS_ENV=live）での起動前には validate_config を用いた確認と、LINE 等の通知設定の確認を必ず行ってください。

以上が本リポジトリの README（概要・セットアップ・使い方）です。必要であれば各モジュール（ExecutionEngine、Monitoring の各部）の詳細な使い方や API ドキュメント、サンプル設定ファイル（.env.example / config/*.yaml の雛形）を追加します。どの部分を詳しく書いて欲しいか指定してください。