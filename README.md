# KabuSys — README

この README はコードベース (src/kabusys) の簡易ドキュメントです。  
日本株自動売買システムのコンポーネント（実行エンジン、監視、研究、ポートフォリオ構築、AI 補助等）を含みます。

注意: 本リポジトリはパッケージ化された Python モジュール構成です。実行はモジュールとして行うことを想定しています（例: python -m kabusys.run_execution）。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（コマンド例）
- 環境変数 / 主要設定
- 停止・Kill スイッチの仕組み
- ディレクトリ構成（概略）
- 補足・運用上の注意

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システムのコンポーネント群です。
- 主要機能：
  - ExecutionEngine: 発注・オーダー管理・リスク管理を担う実行エンジン（paper_trading をサポート）
  - Monitoring: システム稼働状況、注文ログ、リスク（ドローダウン／ポジション上限）を監視し、通知や Kill Switch を制御
  - Research/Portfolio: ファクター計算、特徴量探索、銘柄選定・配分・ポジションサイズ算定
  - AI モジュール: ニュースの NLP によるセンチメント評価、レジーム判定（OpenAI を利用）
  - ツール: ペーパートレード検証レポート生成 など

主な機能一覧
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、本番 DB と分離された DB (data/paper_trading.db) に記録
  - PID ファイル (data/execution.pid) を利用
- 監視ループ起動スクリプト: run_monitoring.py
  - システム監視（CPU/メモリ/ディスク/プロセス生存）とモニタリング DB の更新
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は環境に関わらず本番用 sqlite_path を参照（設計上の仕様）
- 設定ウィザード: config_setup.py（.env の対話式生成）
- 設定検証: validate_config.py（.env と config/*.yaml の存在・基本整合性をチェック）
- Paper Trading 検証レポート: tools/paper_verification_report.py
- ポートフォリオ構築: portfolio/*（候補選定・重み算出・リスク調整・ポジションサイズ決定）
- 研究系: research/*（ファクター計算、将来リターン、IC、統計要約）
- AI 系: ai/news_nlp.py / ai/regime_detector.py（OpenAI API を利用）

セットアップ手順（ローカル開発）
1. 推奨 Python
   - Python 3.10 以上（型注釈の union 表記などを使用）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージのインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - 推奨／オプション:
     - PyYAML（validate_config の YAML 検査で使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください）

4. .env の準備
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルート）  
     必須環境変数:
       - JQUANTS_REFRESH_TOKEN
       - KABU_API_PASSWORD
     主要なデフォルト:
       - KABUSYS_ENV=development  # development | paper_trading | live
       - DUCKDB_PATH=data/kabusys.duckdb
       - SQLITE_PATH=data/monitoring.db
       - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
       - LOG_LEVEL=INFO
   - Settings モジュールは .env/.env.local を自動読込（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）

5. ディレクトリ（data, logs）作成
   - ログ: logs/（setup_logging が自動作成を試みますが、権限等で失敗する場合は手動作成）
   - DB 保存先: data/（SQLite や PID/flag を置く）

使い方（実行例）
- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 環境設定ウィザード（.env の作成/更新）
  - python -m kabusys.config_setup

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading のときは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録され、本番 DB と分離
    - 起動前に data/stop_requested.flag が存在する場合は起動せず終了

- 監視サービス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用する

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを上書き可能（環境変数 PAPER_TRADING_SQLITE_PATH 優先）

AI 機能（OpenAI）
- ニュース NLP / レジーム判定は OpenAI API を利用します。API キーは OPENAI_API_KEY 環境変数で指定してください。
- score_news(), score_regime() は呼び出し時に api_key 引数を渡すことも可能です。
- リトライ／バックオフなどのフォールトトレラントな実装が含まれますが、API レスポンスの検証などに注意してください。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- OPENAI_API_KEY（AI 機能利用時）
- MONITOR_POLL_INTERVAL（監視ポーリング秒数、デフォルト 60）
- PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START（起動時 kill.flag をクリアするか 0/1、production では 0 推奨）

停止・Kill スイッチの仕組み
- run_execution / run_monitoring は stop フラグ（data/stop_requested.flag）を監視しているため、このファイルを作成するとループを抜けて終了します（優雅にシャットダウン）。
- KillSwitch（監視側）の仕組み:
  - 監視コンポーネント（RiskMonitor 等）でしきい値超過が検出されると data/kill.flag が書き込まれます
  - ExecutionEngine は起動時やループ中に kill.flag の存在を確認して停止します（冗長停止手段）
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では危険なので 0 推奨）

ディレクトリ構成（主要ファイルのみ・簡略化）
- src/kabusys/
  - __init__.py
  - config.py                # Settings / 自動 .env 読込
  - config_setup.py          # .env 対話ウィザード
  - validate_config.py       # 起動前設定チェック CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py  (存在を仮定)
  - execution/                # Execution 関連（Engine, OrderManager 等）
    - execution_engine.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/  (既定の保存先。実行時に作成されることが多い)
  - logs/  (ログ出力先。setup_logging により作成されることがある)

補足・運用上の注意
- Settings は .env/.env.local をプロジェクトルートから自動ロードします（CWD に依存せずプロジェクトルート判定を行う）。
- run_monitoring は監視用 DB（Settings.sqlite_path）に常に本番パスを使う実装になっています（環境に依存しない仕様）。
- Paper Trading は本番 DB と分離するよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- ログは stdout とファイル（日次ローテーション）へ出力されます。logs/ ディレクトリの作成に失敗した場合はコンソール出力のみになります。
- OpenAI を利用する機能は API 負荷・コストに留意してください（バッチ化・リトライロジックあり）。

サンプル .env（最低限）
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

最後に
- まずは python -m kabusys.config_setup で .env を作成し、python -m kabusys.validate_config でチェックしてください。
- paper_trading でのローカル検証 → 実運用（KABUSYS_ENV=live）へ移行する際は、LINE 通知設定や Kill Switch 等の本番ガードを十分に確認してください。

必要であれば、この README を元に運用手順書（デプロイ手順、systemd/cron/tmux/supervisor での起動方法、モニタリング一覧）を追記します。どの情報を優先して拡張しますか？