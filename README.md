# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）。

このドキュメントはリポジトリ内の主要スクリプト・設定フロー・ディレクトリ構成と、開発・運用時の基本的な使い方をまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動 / 実行コマンド）
- 主要環境変数（例）
- 運用上の注意点（Kill Switch / Stop フラグ等）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株向けの自動売買フレームワーク（分析 → シグナル生成 → 発注 → 監視）です。
- DuckDB を用いた研究・ファクター計算、SQLite を用いた監視・発注ログ保存、OpenAI を用いたニュース NLP／レジーム判定など複数コンポーネントで構成されます。
- 設定は .env（および .env.local）を使い分け、KABUSYS_ENV によって動作モード（development / paper_trading / live）を切り替えます。

機能一覧
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（実際の発注処理／ペーパートレード対応）
- Monitoring（各種モニタ / Kill Switch / アラート呼び出し）
- Portfolio construction（候補選定、重み付け、ポジションサイジング、セクター制約）
- Research（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI モジュール（ニュースのセンチメントスコアリング、レジーム判定） — OpenAI API を使用
- 運用ツール：Paper Trading 検証レポート生成スクリプト

セットアップ手順（概略）
1. リポジトリをクローンし、Python 仮想環境を作成して有効化する
   - python -m venv .venv
   - source .venv/bin/activate  (Windows は .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt が無い場合は下記を目安にインストールしてください。
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で YAML 検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env を作成する（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - あるいは .env.example を参考に手動作成
   - ウィザード実行後、python -m kabusys.validate_config で検証を行うことを推奨

4. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / ログ保存先は data/ および logs/（各種モジュールの設定で変更可）
   - 例: mkdir -p data logs

主要なファイル・データベース
- DuckDB（分析用）: デフォルト data/kabusys.duckdb（環境変数 DUCKDB_PATH）
- SQLite（監視 DB）: デフォルト data/monitoring.db（環境変数 SQLITE_PATH）
- Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時はこちらが使用される。環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）
- ログ: logs/<app_name>.log（setup_logging により日次ローテーション）

使い方（主要コマンド例）

1) 設定ウィザード
- .env の初期作成・更新:
  - python -m kabusys.config_setup

2) 設定検証
- .env と config/*.yaml（存在する場合）を検証:
  - python -m kabusys.validate_config
- --strict を付けると警告も失敗扱いにします。

3) ExecutionEngine（発注エンジン）起動
- 実行:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（data/paper_trading.db）に記録します。本番 DB と分離されます。
  - 起動時に data/stop_requested.flag の存在をチェックし、存在する場合は起動を行いません。
  - 実行中は data/execution.pid に PID が書き込まれます（設定によりパス変更可）。
  - 停止は stop フラグを書き込むことで制御できます（下記参照）。

4) Monitoring（監視ループ）起動
- 実行:
  - python -m kabusys.run_monitoring
- 特記事項:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。無効な値（<=0）を与えるとデフォルトにフォールバックします。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（SQLITE_PATH）を使用する設計です（監視ログは常に指定 DB に書く想定）。
  - 監視中に data/stop_requested.flag が存在するとループを抜けて終了します。

5) Paper Trading 検証レポート（ツール）
- 実行:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

主要環境変数（代表例）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — 動作環境: development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant | partial | never | reject）
- KILL_FLAG_CLEAR_ON_START — 本番環境での Kill Flag 自動クリア（1 でクリア。通常は 0 を推奨）
- KILL_FLAG_PATH — kill.flag の格納先（デフォルト: data/kill.flag）

運用上の注意点（Kill Switch / Stop フラグ等）
- Kill Switch:
  - RiskMonitor 等が閾値（ドローダウン、ポジション上限等）を検出すると、KillSwitch が data/kill.flag を書き込み ExecutionEngine 停止を指示します。
  - 本番環境（KABUSYS_ENV=live）では Kill Switch の扱いに注意してください。validate_config で本番向けの警告チェックを行えます。
- Stop フラグ:
  - data/stop_requested.flag：run_execution / run_monitoring のループを停止させるために使われます。存在すると起動を行わない、またはループ中に検知して停止します。
- PID ファイル:
  - data/execution.pid に ExecutionEngine の PID が書かれます（設定可能）。
- ロギング:
  - 共通ユーティリティ setup_logging により stdout と logs/<app_name>.log への日次ローテーション出力が設定されます。
  - ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード機能含む）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — 共通ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ
  - execution/ — 発注関連（Engine, OrderManager, BrokerFactory 等）：実行・発注ロジック（ライブラリ内）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続化層
    - system_monitor.py, trade_monitor.py, risk_monitor.py, monitoring_engine.py, kill_switch.py, alert_manager.py（監視関連）
  - portfolio/ — 銘柄選定・重み付け・ポジションサイジング（純粋関数群）
  - research/ — ファクター計算・特徴量探索（DuckDB を使用）
  - ai/
    - news_nlp.py — ニューステキストを OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py — マクロ＋MA による市場レジーム判定（OpenAI 併用）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力ツール

補足（実装のポイント・設計の意図）
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込みます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして自動ロードを無効化できます。
- ExecutionEngine は paper_trading モードだと MockBrokerClient を用いて実施し、紙上注文は paper_trading DB に記録されます。本番 DB と完全に分離される設計です。
- Monitoring は監視ログを記録し、リスク条件検出時に Kill Switch を書き込み ExecutionEngine を停止させるワークフローを提供します。
- AI モジュールは OpenAI を使用します（OPENAI_API_KEY が必要）。API の失敗はフェイルセーフでフォールバックを行う設計です（例: マクロセンチメント失敗時は 0.0）。

よくある操作例（ワークフロー）
1. 初期設定
   - python -m kabusys.config_setup
   - python -m kabusys.validate_config

2. データ投入・DuckDB 準備（別スクリプトや ETL を用意）
   - prices_daily / raw_financials / raw_news などのテーブル準備

3. デイリー運用
   - python -m kabusys.run_execution   （発注エンジンを起動）
   - python -m kabusys.run_monitoring  （別プロセスで監視を起動）

4. ペーパートレード検証
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

問題や不明点
- データベーススキーマや外部接続（kabuステーション / J-Quants / OpenAI）のセットアップ手順が必要な場合は、使用する環境に合わせた追加ドキュメントを作成してください。
- ローカルでの動作確認用にモック実装（MockBrokerClient）を活用することを推奨します（paper_trading モード）。

---

最後に
- 本 README はソースコード（src/kabusys 以下）を参照して作成しています。新しい機能追加やファイル移動があった場合は README を更新してください。