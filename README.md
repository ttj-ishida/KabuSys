KabuSys — 日本株自動売買システム
=================================

バージョン: 0.1.0

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための小規模なシステム群です。本リポジトリは以下の主要コンポーネントを含みます。

- ExecutionEngine: 発注・注文管理・リスク管理の実行エンジン（本番 / ペーパートレード対応）
- Monitoring: システム稼働・注文・リスクをポーリングしてログ／アラート／Kill Switch を管理
- Research: DuckDB を使ったファクター計算・特徴量探索機能
- Portfolio: 候補選定・ウェイト算出・ポジションサイズ計算などの純粋関数群
- AI 支援: OpenAI（gpt-4o-mini を想定）を使ったニュースセンチメントやレジーム判定
- ユーティリティ: .env ウィザード、設定検証、ログ設定など

主な機能
--------
- 実取引 / ペーパートレードの分離（ペーパー時は専用 SQLite DB に記録）
- モニタリング（CPU/メモリ/ディスク、データ鮮度、滞留注文、ドローダウン等）
- Kill Switch（閾値超過時に data/kill.flag を書き込み ExecutionEngine を停止）
- ポートフォリオ構築（候補選定、等金額/スコア加重、リスク制約・セクター制限）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および IC/統計解析
- ニュース NLP による銘柄センチメント評価（OpenAI API 経由）
- ペーパートレード検証レポート生成ツール

動作環境・前提
--------------
- Python 3.9+
- 必須パッケージ（例）:
  - duckdb
  - psutil
  - openai
- オプション／推奨:
  - PyYAML（config/*.yaml の検証に使用）
- DB:
  - DuckDB（分析用、デフォルト data/kabusys.duckdb）
  - SQLite（監視・ペーパートレード DB、デフォルト data/monitoring.db / data/paper_trading.db）
- .env に外部 API キーやパスワードを設定すること（JQUANTS, KABU API, OPENAI 等）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （設定検証で PyYAML を使う場合）pip install pyyaml

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを入力します。
   - 生成された .env は絶対に Git にコミットしないでください。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

使い方（実行コマンド例）
-----------------------
- ExecutionEngine を起動（本番またはペーパーは KABUSYS_ENV により切替）
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag または data/kill.flag が存在すると起動を抑止／停止します
    - 実行中は data/execution.pid が使用されます（Settings.pid_file_path 参照）

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - Monitoring は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path（data/monitoring.db など）を使用します

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証 CLI
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH または --db で変更可能）

- AI 関連（プログラム経由で呼ぶ）
  - ニューススコア付与:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)
  - 注意: OPENAI_API_KEY が必要（関数引数で上書き可）。API 呼び出しはリトライ等のフェイルセーフを備えていますが、キー未設定時は例外になります。

主な環境変数（抜粋）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 運用関連:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject、デフォルト instant）
  - KILL_FLAG_CLEAR_ON_START: 起動時に Kill Flag を自動クリアするか（"1" で有効。production では "0" 推奨）
- モニタリング:
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト 60）

運用ノート
---------
- ログ:
  - ログは logs/<app_name>.log に日次ローテーションで出力（logs/ ディレクトリは自動作成）
  - setup_logging を各起動スクリプトで呼び出して統一的に管理しています
- Kill Switch:
  - RiskMonitor 等が致命的閾値を検出した場合、KillSwitch が data/kill.flag を作成し ExecutionEngine に停止シグナルを送ります
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動で kill.flag をクリアします（本番環境では推奨されません）
- 停止制御:
  - data/stop_requested.flag が作られると run_monitoring / run_execution はループを終了します（運用上の手動停止用）
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は起動時にテーブルを冪等に作成し、既往の DB に対する簡単なマイグレーション（カラム追加）を行います

ディレクトリ構成（主要ファイル）
------------------------------
- src/kabusys/
  - __init__.py            — パッケージ定義（バージョン情報）
  - config.py              — 環境変数 / Settings 管理（自動 .env ロード機能含む）
  - config_setup.py        — .env 対話式ウィザード
  - validate_config.py     — 起動前設定検証 CLI
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - ai/
    - news_nlp.py          — ニュースの NLP スコアリング（OpenAI）
    - regime_detector.py   — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py     — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py    — システム状態 / データ鮮度チェック
    - trade_monitor.py     — （注文）監視ロジック
    - risk_monitor.py      — ドローダウン / ポジション上限監視
    - kill_switch.py       — Kill Switch 制御
    - monitoring_engine.py — Monitor を束ねるエンジン
    - alert_manager.py     — アラート送信（LINE 等：実装に依存）
  - execution/             — 発注エンジン関連（OrderManager, RiskManager, Reconciler, BrokerFactory 等）
  - portfolio/             — ポートフォリオ構築（builder, position_sizing, risk_adjustment）
  - research/              — ファクター計算・特徴量解析（DuckDB ベース）
  - utils/
    - logging_setup.py     — 共通ログ設定
    - process_priority.py  — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (実行時に生成される想定)
    - monitoring.db        — 監視 DB（SQLite）
    - paper_trading.db     — ペーパートレード DB（SQLite）
    - kill.flag / stop_requested.flag / execution.pid など

開発者向けメモ
---------------
- 多くのモジュールは DuckDB 接続や sqlite3.Connection を引数で受け取り、テストしやすい純粋関数設計を心がけています。
- AI 関連処理は外部 API に依存するため、テスト時は内部の API 呼出し関数をモックする設計になっています（_call_openai_api を patch 等）。
- process_priority.set_process_priority() で起動時にプロセス優先度を上げています（プラットフォーム差分吸収済み）。
- production での運用時は KABUSYS_ENV=live に設定し、LINE 等の通知設定を必ず行ってください。

ライセンス
---------
（リポジトリに別途 LICENSE ファイルがあればその内容に従ってください。本 README には明示的なライセンス情報を含めていません。）

以上がこのコードベースの概要と基本的な使い方です。必要があれば個別モジュール（ExecutionEngine の起動パラメータ例、AI 用の呼び出しサンプルスクリプト、監視アラートの設定方法など）について詳細ドキュメントを追加します。どの部分の詳細が欲しいか教えてください。