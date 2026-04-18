# KabuSys

日本株自動売買システムのリポジトリ（ライブラリ＋起動スクリプト群）。

この README はコードベースの説明、セットアップ手順、主要スクリプトの使い方、ディレクトリ構成をまとめたものです。

目次
- プロジェクト概要
- 主な機能
- 環境変数（主なもの）
- セットアップ手順
- 実行方法（代表的なコマンド）
- 運用・停止方法（フラグファイル）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買（ExecutionEngine）とそれを監視・運用するためのコンポーネント群を提供します。
- 主要機能は発注エンジン、監視（System / Trade / Risk）、ポートフォリオ構築（選定・重み付け・株数計算）、リサーチ（ファクター計算・特徴量解析）、AI を使ったニュースセンチメント評価、ペーパートレード検証レポート生成などです。
- 設定は .env ファイルおよび環境変数で行います。自動でプロジェクトルートの .env を読み込みます（無効化可）。

主な機能一覧
- ExecutionEngine 起動 / 発注フロー（本番 / ペーパートレード切替）
- Monitoring（SystemMonitor / TradeMonitor / RiskMonitor）および Kill Switch による自動停止
- ポートフォリオ構築モジュール（候補選定・重み計算・ポジションサイズ算出）
- Research（ファクター計算：Momentum / Volatility / Value、Forward returns、IC など）
- AI モジュール（ニュースを OpenAI でスコアリング、レジーム判定）
- ペーパートレード検証レポート生成スクリプト
- 設定ウィザード（.env 作成補助）と設定検証 CLI

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境。development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使用し paper_trading 用 DB に分離して動作
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の fill 動作（instant|partial|never|reject, デフォルト: instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: logs/）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill Switch が書き込む flag（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト: 60）
- OPENAI_API_KEY: OpenAI を使う機能で必要

（注）.env.example が参照される点に注意。必須の環境変数が未設定だと validate でエラーになります。

セットアップ手順（開発環境想定）
1. リポジトリをチェックアウト
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - （requirements.txt が無い場合は最低限以下をインストール）
     - duckdb, psutil, openai, PyYAML（config 検証で任意）、その他プロジェクトで使用するパッケージ
4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - または手動で .env を作成（.env.example を参考に）
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict
6. 必要に応じてデータディレクトリを作成
   - mkdir -p data logs

起動・使い方（代表的コマンド）

- ExecutionEngine を起動（通常はプロダクションの起動スクリプト）
  - python -m kabusys.run_execution
  - 動作:
    - KABUSYS_ENV が paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と分離）
    - PID ファイルを書き込み、data/stop_requested.flag を監視して停止
    - 起動前に kill.flag の自動クリア設定（KILL_FLAG_CLEAR_ON_START）を尊重する実装箇所あり

- Monitoring（プロセス・データ鮮度・トレード・リスク監視）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒, デフォルト 60）
  - 監視は本番 sqlite_path を使用（環境にかかわらず）

- 設定ウィザード（.env 作成/更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

- AI 系のバッチ処理（ライブラリ関数）
  - ニュースのスコアリング:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=...)

運用・停止方法（フラグファイル）
- 起動中プロセスの停止はフラグファイルで制御します。
  - 停止要求（run_monitoring/run_execution が監視する）:
    - data/stop_requested.flag を作成すると、run_execution や run_monitoring のループは検知して終了します。
    - 例: touch data/stop_requested.flag
  - Kill Switch:
    - リスク（ドローダウン超過など）検出時、KillSwitch が settings.kill_flag_path（デフォルト data/kill.flag）に理由を書いて ExecutionEngine に停止シグナルを送ります。
    - ExecutionEngine 側は kill.flag を検出して安全に停止します（設定により起動時に自動クリアするか制御可能）。
  - Kill flag を手動で消す:
    - rm data/kill.flag

ログ
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...") を各起動スクリプトで呼び出しています。
- ログは stdout と logs/<app_name>.log（日次ローテート）へ出力されます。ログディレクトリは LOG_DIR またはデフォルト logs/。

注意点・設計上のポイント
- .env の自動読み込み:
  - プロジェクトルート（.git や pyproject.toml がある場所）を基準に .env / .env.local を自動読み込みします。
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
- 環境による DB 分離:
  - paper_trading 環境では paper_trading 用の SQLite を使用して本番データと分離します。
- OpenAI を使う機能:
  - OPENAI_API_KEY が必要です。AI 呼び出しではリトライやフェイルセーフ（失敗時スコア 0 とする等）が組み込まれています。
- プロセス優先度や CPU affinity:
  - 起動スクリプトは set_process_priority("high") を呼びます（psutil を利用）。権限や OS により設定できない場合は警告をログに出します。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/               — 発注エンジン関連（Engine, OrderManager, BrokerFactory 等）
  - monitoring/
    - monitoring_db.py       — SQLite の永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                   — データ / DB ファイル / フラグファイル（リポジトリには存在しないことが一般的）
  - config/                 — YAML ベースの構成ファイル群（system_config.yaml など、生成スクリプトあり）

（注）上の構成はリポジトリ内で主要なモジュールファイルを抜粋したものです。詳細はソースを参照してください。

トラブルシューティング / よくある質問
- 「必須環境変数が未設定です」と出る:
  - .env を作成し必須値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を設定してください。python -m kabusys.config_setup で対話的に作れます。
- OpenAI 関連が動作しない:
  - OPENAI_API_KEY の設定を確認してください。API 呼び出しはリトライ実装がありますが、キー未設定の場合は例外になります。
- ログファイルが作れない警告:
  - LOG_DIR の作成権限を確認してください。権限がない場合はコンソール出力のみになります。

ライセンス / 貢献
- （ここにライセンス情報や貢献手順を記載してください）

以上。リポジトリ内の各モジュールはドキュメント文字列が比較的詳細なので、実装や挙動の確認はソース内 docstring を参照してください。必要があれば README を拡張して詳しい運用手順や設定例（.env のテンプレート、systemd / cron のサンプルなど）を追加できます。