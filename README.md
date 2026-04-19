# KabuSys

日本株自動売買システムのサブモジュール群を含むリポジトリ。  
この README はコードベース（src/kabusys 以下）から主要な使い方・設定手順をまとめたものです。

概要
----
KabuSys は日本株の自動売買向けに設計されたモジュール群です。  
本リポジトリには以下の主要機能が含まれます（監視・発注・ポートフォリオ構築・リサーチ・AI 補助など）。  
設計方針としては「テスト容易性」「ルックアヘッドバイアス回避」「フェイルセーフ」を重視しています。

主な機能
--------
- ExecutionEngine 起動 / 発注ロジック（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し、paper_trading 用 DB に記録
- Monitoring（監視）ループ（run_monitoring.py）
  - システムリソース、データ鮮度、発注状況、リスク指標の定期チェック
  - Kill Switch（一定条件で Execution の停止フラグを書き込む）
- 監視 DB ラッパー（SQLite）: monitoring_db.py
- リスク監視（ドローダウン・ポジション上限）: risk_monitor.py
- アラート通報基盤（LINE などと連携するためのフック）
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクター制限
- リサーチ: ファクター計算（モメンタム/バリュー/ボラティリティ）、将来リターン・IC 計算
- AI サービス:
  - ニュースのセンチメント評価（OpenAI を利用した ai スコア生成）
  - 市場レジーム判定（MA と LLM センチメントの合成）
- ユーティリティ:
  - .env 対話式ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - ペーパートレード検証レポート生成ツール（tools/paper_verification_report.py）
  - ログ設定ユーティリティ、プロセス優先度設定等

動作要件（推奨）
----------------
- Python 3.10+
- 必要パッケージ（主要）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml のパース検証を行う場合に必要）
  - 標準ライブラリ: sqlite3 等
- （任意）仮想環境の利用を推奨（venv, pipenv, poetry 等）

セットアップ手順
----------------
1. リポジトリをクローンし、作業ディレクトリへ移動
   - git clone ... ; cd your-repo

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - 対話に従って J-Quants トークン、kabu API パスワード、DB パス、KABUSYS_ENV などを設定してください。
   - 生成された .env は絶対にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います: python -m kabusys.validate_config --strict

6. DB 初期化・ログディレクトリ等
   - デフォルトの SQLite / DuckDB ファイルは data/ 以下に作成されます（必要に応じて .env でパスを変更）
   - ログは logs/ に日次ローテートで保存されます（LOG_DIR 環境変数で変更可能）

環境変数（主要）
----------------
（.env で設定／config_setup で対話入力される項目の抜粋）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp, regime_detector）で必須

自動 .env ロード
----------------
- config.py はプロジェクトルート（.git または pyproject.toml を検出）を基準に .env と .env.local を自動読み込みします。
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（主要スクリプト）
-----------------------

- 監視ループを起動（本番想定）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能（デフォルト 60 秒）。
  - 監視は常に settings.sqlite_path（本番）を使用します。

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に書き込みます。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - エンジンは data/execution.pid を管理します。停止は data/stop_requested.flag 生成で行います。

- 設定ウィザード（.env 生成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB は PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ライブラリ API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...).cursor/connection）を受け取ります。OPENAI_API_KEY を環境変数で設定しておくか、api_key 引数で渡してください。

停止・Kill Switch
-----------------
- Execution 停止（外部から）:
  - Kill Switch: monitoring モジュールが条件を満たすと data/kill.flag を書き込みます（ExecutionEngine はこれを参照して停止）。
  - 手動停止: data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して終了します。
- kill.flag の動作は Settings.kill_flag_path で指定できます。clear（削除）は KillSwitch.clear() を呼ぶか手動でファイルを削除してください。

ロギング
--------
- 共通のログセットアップ関数: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  - 標準出力（stdout）とファイル（logs/<app_name>.log 日次ローテーション）を設定します。
  - LOG_LEVEL / LOG_DIR 環境変数で挙動を制御できます。

ディレクトリ構成（抜粋）
----------------------
プロジェクトの主要ファイル / モジュールの構成（src/kabusys 配下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env 対話ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_monitoring.py              — 監視ループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                      — 発注関連モジュール（Engine, OrderManager 等）
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

（上記は抜粋です。細かい実装ファイルがさらに含まれます）

開発上の注意
-------------
- ルックアヘッドバイアス防止: 多くのリサーチ / AI モジュールは内部で date/target_date を明示的に受け取り、datetime.today() 等に依存しない実装になっています。
- DB 書き込み時に冪等性を意識した実装（DELETE→INSERT ではなく upsert/ON CONFLICT を利用する等）が施されています。
- OpenAI 呼び出しはリトライ・バックオフやレスポンス検証を実装しており、API 失敗時は安全にフォールバックする設計です。
- .env は機密情報を含むため絶対に Git にコミットしないでください。

トラブルシューティング
-----------------------
- .env が自動読み込みされない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないことを確認する（自動ロードを無効化している場合は手動で .env を読み込んでください）。
- 依存ライブラリが不足する場合:
  - PyYAML がないと validate_config は YAML 検証をスキップします（警告）。必要なら pip install PyYAML。
- OpenAI 関連が動作しない場合:
  - OPENAI_API_KEY がセットされているか確認してください。API 呼び出しに失敗すると関数は安全にフォールバックしますが、AI 機能の結果は取得されません。

付録: よく使うコマンド例
-----------------------
- .env 作成（対話式）:
  - python -m kabusys.config_setup
- 設定検証（非厳格）:
  - python -m kabusys.validate_config
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Execution 起動（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。必要に応じて README を拡張（詳しい設定例、運用手順、DB スキーマやログの読み方、デプロイ手順等）できますので、追加で記載したい項目があれば指示してください。