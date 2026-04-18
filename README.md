KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的にした Python パッケージです。
このリポジトリには以下の主要コンポーネントが含まれます。

- 実行エンジン (ExecutionEngine)：発注・リスク管理・注文管理を行う処理（run_execution 起動）
- 監視 (Monitoring)：システム状態・注文/リスクの監視と Kill Switch（run_monitoring 起動）
- ポートフォリオ構築ロジック（候補選定・重み計算・ポジションサイズ算出）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定）…OpenAI API を利用
- ユーティリティ（環境設定ウィザード、設定検証、ログ設定 など）
- ツール（Paper Trading の検証レポート生成など）

必要条件
--------
- Python 3.10+
- sqlite3（標準ライブラリ）
- 推奨パッケージ（実行時に必要なもの）:
  - duckdb
  - psutil
  - openai（AI 機能を使用する場合）
  - PyYAML（設定ファイル検証を有効にしたい場合）

通常はプロジェクトに requirements.txt があればそれを利用してください。最低限の手動インストール例:
pip install duckdb psutil openai PyYAML

主な機能
--------
- 環境設定ウィザード（.env の対話的作成）: python -m kabusys.config_setup
- 設定検証 CLI（.env / config/*.yaml の簡易チェック）: python -m kabusys.validate_config
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード分離）: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 sqlite DB（data/paper_trading.db）に記録
- Monitoring 起動スクリプト（定期ポーリング）: python -m kabusys.run_monitoring
  - 環境にかかわらず監視は本番用 sqlite_path を参照（監視ログは data/monitoring.db 等）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で調整（デフォルト 60 秒）
- Kill Switch（kill.flag）: リスクや重大イベント発生時に flag ファイルを書き込んで ExecutionEngine を停止
- Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report
- AI モジュール:
  - kabusys.ai.news_nlp: raw_news を OpenAI に送り銘柄別センチメント (ai_scores) を生成
  - kabusys.ai.regime_detector: ma200 とマクロニュースの LLM センチメントを合成して market_regime を算出
- 研究モジュール: ファクター計算 (momentum, volatility, value)、forward returns、IC（情報係数）計算 等
- ポートフォリオ構築ユーティリティ: 候補選定、等配分/スコア加重、リスク調整、ポジション数算出（単元丸め含む）

セットアップ手順
----------------

1. リポジトリをクローンして Python 環境を用意
   - Python 3.10 以上を推奨
   - 仮想環境の作成（任意）
     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows

2. 依存パッケージをインストール
   pip install duckdb psutil openai PyYAML

   ※ AI 機能を使わない場合は openai のインストールは不要。YAML 検証が不要なら PyYAML は不要。

3. .env の作成（対話式ウィザード推奨）
   python -m kabusys.config_setup

   ウィザードは J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV（development | paper_trading | live）などを設定します。
   生成される .env は絶対に Git にコミットしないでください。

4. 設定検証
   python -m kabusys.validate_config
   --strict を付けると警告もエラー扱い（exit 1）になります。

5. 必要なディレクトリの準備
   ログや DB のデフォルトパスは data/ と logs/ 配下です。自動作成されますが、権限等に注意してください。

使い方
------

基本的な起動例:

- 監視ループ（Monitoring）を起動:
  python -m kabusys.run_monitoring

  環境変数:
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
  - KABUSYS_ENV は Settings に従うが、監視は本番 sqlite_path を使います
  停止方法:
  - data/stop_requested.flag が存在するとループは終了します（スクリプトがチェック）
  - Ctrl-C（KeyboardInterrupt）でも停止します

- 実行エンジン（ExecutionEngine）を起動:
  python -m kabusys.run_execution

  特記事項:
  - KABUSYS_ENV=paper_trading の場合はペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と完全分離されます。
  - 実行中は data/execution.pid に PID を書きます。data/stop_requested.flag を作成すると終了シグナルになります。
  - Settings.kill_flag_path（デフォルト data/kill.flag）に kill.flag が存在すると ExecutionEngine を停止する設計（Kill Switch）。

- 環境設定ウィザード:
  python -m kabusys.config_setup

- 設定検証:
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Paper Trading 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  オプション:
    --db PATH: SQLite DB ファイルパス（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI モジュール（手動利用例）:
  - OpenAI API キーを環境変数 OPENAI_API_KEY に設定しておく（または関数に api_key を渡す）。
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

設定（主要な環境変数）
--------------------
（.env に記載する代表的なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- KABUSYS_ENV: 実行環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- MONITOR_POLL_INTERVAL: 監視のポーリング秒数（run_monitoring が参照）
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

停止フラグ / Kill Switch
-----------------------
- run_monitoring / run_execution は data/stop_requested.flag を見て停止します（手動で作成すれば優雅に停止）。
- KillSwitch（監視側）は Settings.kill_flag_path（デフォルト data/kill.flag）に書き込み、ExecutionEngine に停止を促します。
- 本番で KILL_FLAG_CLEAR_ON_START=1 は危険です。デフォルトは 0（クリアしない）です。

ログ
----
- ログは kabusys.utils.logging_setup.setup_logging によって設定されます。
- デフォルトではコンソール出力（stdout）と logs/<app_name>.log（毎日ローテーション、30日保持）が出力先になります。
- ログディレクトリは環境変数 LOG_DIR で変更可能（デフォルト logs/）。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_monitoring.py         — 監視プロセス起動スクリプト
  - run_execution.py          — 実行エンジン起動スクリプト
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — 監視 DB 層（SQLite）
    - system_monitor.py       — システム・データ鮮度監視
    - trade_monitor.py        — （注文監視、コード内に実装あり）
    - risk_monitor.py         — ドローダウン・ポジション数監視
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — （アラート送信、コード内に実装あり）
  - execution/
    - execution_engine.py     — 実行エンジン本体（EngineConfig, run_session 等）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - data/
    - pipeline.py              — データパイプライン（DuckDB から価格取得等）
    - stats.py                 — 正規化ユーティリティ等
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py       — レジーム判定（ma200 + LLM）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成ツール

補足（設計上の注意事項）
-----------------------
- Settings は .env の自動読み込みを行います（プロジェクトルートは .git または pyproject.toml によって探索）。
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。
- 実行中はプロセス優先度を high に設定しようとします（psutil を使用）。権限がない場合は警告が出ます。
- AI モジュールは外部 API を呼び出します。API 呼び出しはリトライやバックオフ等を実装していますが、APIキーが必須です。
- DB マイグレーション（monitoring_db.init_monitoring_db）は冪等で既存スキーマに column を追加する処理を含みます。

よくある運用コマンドまとめ
-------------------------
- .env を作る（対話式）:
  python -m kabusys.config_setup
- 設定を検証:
  python -m kabusys.validate_config
- 監視プロセス起動:
  python -m kabusys.run_monitoring
- 実行エンジン起動:
  python -m kabusys.run_execution
- Paper Trading レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス / 貢献
-----------------
この README はコードベースから生成されています。実運用する際は必ず .env.example を参照の上、必要な資格情報や API キーを適切に管理してください。

必要であれば README に含める動作図、構成例（systemd / cron / supervisor 用のサンプル unit）、あるいは requirements.txt の具体的な内容など追記できます。要望があれば教えてください。