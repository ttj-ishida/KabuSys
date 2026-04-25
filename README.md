KabuSys
======

日本株向け自動売買システムの一部コンポーネント群（設定管理、モニタリング、Execution 起動スクリプト、ポートフォリオ計算、リサーチ、AI ニュース処理など）の実装コードベースです。本リポジトリはライブラリ／実行スクリプト群を提供し、実運用・ペーパートレードの両方を想定しています。

主な特徴
--------
- 環境設定ウィザード（.env の対話的生成）
- 起動前設定検証 CLI（必須環境変数や config/*.yaml の存在チェック、--strict モード）
- ExecutionEngine 起動スクリプト（本番／ペーパートレード切替）
- Monitoring 用ポーリングプロセス（System / Trade / Risk の監視）
- Kill Switch による安全停止（data/kill.flag を書き込むことで Execution を停止）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築・リスク調整・ポジションサイジングの純粋関数群
- DuckDB / SQLite を前提としたデータアクセス（Prices/News/Financials など）
- OpenAI を用いたニュース NLP / レジーム検出モジュール（オプション）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の新構文や | ユニオンを使用）
- システムにより psutil 等のネイティブ依存が必要

推奨パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証に使用）
インストール例:
    pip install duckdb psutil openai PyYAML

リポジトリをクローン:
    git clone <repo-url>
    cd <repo-root>

初期 .env の作成（対話ウィザード）:
    python -m kabusys.config_setup
ウィザードは J-Quants トークンや kabuステーション API パスワード等の各種設定値を対話的に作成して .env に保存します。
（生成された .env は Git にコミットしないでください）

設定検証:
    python -m kabusys.validate_config
警告もエラー扱いにする（厳密チェック）:
    python -m kabusys.validate_config --strict

データディレクトリの準備:
- デフォルトの DB / PID / フラグファイル保存先はプロジェクト直下の data/（.env で上書き可能）。
- 必要に応じて data/ や logs/ を作成しますが、起動処理は自動作成も試みます。

主要環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN（必須） — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須） — kabuステーション API パスワード
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE — ペーパートレードの約定挙動: instant / partial / never / reject（デフォルト: instant）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — monitoring ポーリング間隔（秒。デフォルト 60）

主な使い方
----------

1) Execution（エンジン）起動
- 環境に応じて本番／ペーパートレードが切り替わります。
- ペーパートレード時は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

起動:
    python -m kabusys.run_execution

実行挙動:
- 起動時に data/stop_requested.flag が存在すると起動せず終了します。
- 実行中に stop_requested.flag が作成されるとエンジンはシャットダウンを試みます。
- 実行時に PID ファイル（data/execution.pid 等）を作成します。

2) Monitoring 起動
- SystemMonitor / TradeMonitor / RiskMonitor をポーリングして監視・アラート・Kill Switch 評価を行います。
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒。デフォルト 60）。

起動:
    python -m kabusys.run_monitoring

挙動:
- 監視は常に（KABUSYS_ENV にかかわらず）本番用 sqlite_path を使用します（監視データは本番 DB を参照/保存）。
- data/stop_requested.flag を検知するとループを抜けて終了します。

3) Paper Trading 検証レポート
- ペーパートレード DB（デフォルト data/paper_trading.db）から各種指標を集計して標準出力にレポートを出します。

実行例:
    python -m kabusys.tools.paper_verification_report
期間指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
DB 指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

4) 設定ウィザード / 検証
- .env 作成:
    python -m kabusys.config_setup
- 検証:
    python -m kabusys.validate_config
- strict モード:
    python -m kabusys.validate_config --strict

運用上の注意点
--------------
- Kill Switch:
  - KillSwitch（kabusys.monitoring.kill_switch）は条件（ドローダウン超過等）で data/kill.flag を書き込み、Execution 側が検出して安全に停止する仕組みです。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動でクリアしますが、本番では 0（自動クリアしない）が推奨です。
- 停止フラグ:
  - data/stop_requested.flag があると run_* スクリプトは終了します（手動停止用）。
- ロギング:
  - logs/<app_name>.log に日次ローテーションで出力（デフォルト logs/）。LOG_DIR / LOG_LEVEL で上書き可。
- 環境自動ロード:
  - config.Settings はプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DB マイグレーション:
  - monitoring DB は初回起動時に必要テーブル・カラムを作成します（冪等）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                       — 環境変数 / Settings
- config_setup.py                 — .env 対話ウィザード
- validate_config.py              — 設定検証 CLI
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — Monitoring ポーリング起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py                    — ニュース NLP（OpenAI でセンチメント評価）
  - regime_detector.py             — マーケットレジーム判定（MA + マクロ NLP 合成）
- monitoring/
  - monitoring_db.py               — SQLite 永続化レイヤ
  - system_monitor.py              — システム状態・データ鮮度監視
  - trade_monitor.py               — 発注・約定の監視（存在）
  - risk_monitor.py                — ドローダウン・ポジション上限監視
  - monitoring_engine.py           — 各 Monitor を束ねるエンジン
  - kill_switch.py                 — kill.flag 書き込みロジック
  - alert_manager.py               — 通知（LINE 等）管理（存在）
- execution/
  - execution_engine.py            — ExecutionEngine（存在）
  - order_manager.py               — 発注管理
  - order_repository.py            — 発注履歴保存
  - reconciler.py                  — 注文整合処理
  - broker_factory.py              — ブローカークライアント生成（Mock / real）
  - risk_manager.py                — 発注前リスクチェック
- portfolio/
  - portfolio_builder.py           — 候補選定・重み算出
  - position_sizing.py             — 発注株数計算
  - risk_adjustment.py             — セクターキャップ・レジーム乗数
- research/
  - factor_research.py             — Momentum / Volatility / Value 等の計算（DuckDB）
  - feature_exploration.py         — 将来リターン・IC / 統計
- monitoring/                       （前述の監視関連）
- tools/
  - paper_verification_report.py   — Paper Trading 検証レポート生成スクリプト
- utils/
  - logging_setup.py               — ルートロガー設定ユーティリティ
  - process_priority.py            — プロセス優先度 / CPU affinity 設定ユーティリティ
  - その他ユーティリティ

（注）上記はコードベースの一部抜粋です。実際のモジュール群はリポジトリ内を参照してください。

開発 / デバッグ
----------------
- ログレベルを DEBUG にして詳細ログを確認してください（LOG_LEVEL=DEBUG）。
- OpenAI / 外部 API 呼び出し部分はテスト時にモック可能な設計になっています（関数を patch して差し替え）。
- Monitoring / Execution は stop フラグにより安全停止できます。ループ中の強制終了はデータ不整合を招く恐れがあるため、まず stop_requested.flag を作成してください。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンスや貢献方法・連絡先を記載してください）

補足
----
- 本 README はコードベースの docstring と実装から導出した要約です。実運用前に必ず python -m kabusys.validate_config で設定を確認してください。
- 本プロジェクトを本番環境で動かす際は、特に KABUSYS_ENV=live の設定、API キー管理、Kill Switch の振る舞い（KILL_FLAG_CLEAR_ON_START）に注意してください。