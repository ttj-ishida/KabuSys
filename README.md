README
======

概要
----
KabuSys は日本株向けの自動売買・研究プラットフォームのコアライブラリ群です。
このリポジトリには、実行用エンジン起動スクリプト、モニタリング、ポートフォリオ構築のユーティリティ、研究用ファクター計算、AI を使ったニューススコアリングなどの主要コンポーネントが含まれます。

注記: 本ドキュメントはリポジトリ内のソースコード（src/kabusys 以下）から機能や設定を抜粋してまとめています。

主な機能
--------
- ExecutionEngine 起動スクリプト（実際の注文処理／ペーパートレードを実行）
- Monitoring（システム状態、注文ログ、リスク監視、Kill Switch）
- 設定ウィザード（.env を対話的に作成）
- 設定検証ツール（.env と config/*.yaml の検証）
- Paper Trading 検証レポート生成ツール
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算）
- 研究モジュール（ファクター計算、将来リターン、IC、統計サマリー）
- AI モジュール（OpenAI を使ったニュースセンチメント評価、市場レジーム判定）
- 共通ユーティリティ：ログ設定、プロセス優先度／CPU affinity 設定など

前提 / 依存関係
---------------
推奨: Python 3.10 以上（PEP 604 の型記法などを使用）
主要依存パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config の YAML 検証に必要、なくても動作はする）
インストール例:
    python -m venv .venv
    . .venv/bin/activate
    pip install duckdb psutil openai PyYAML

（実際の requirements.txt がある場合はそれを使用してください）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリを src 配下に合わせる
   - 本リポジトリはパッケージ名 kabusys を想定しており、import 時に src が PYTHONPATH に含まれていることを想定します。
   - 開発時はプロジェクトルートで `python -m` でモジュールを起動できます。

2. 仮想環境を作成し依存をインストール
   - 上記の通り venv を作成し pip でパッケージを入れてください。

3. .env の作成（対話ウィザード）
   - 対話形式で最小限の環境変数を作成できます:
     python -m kabusys.config_setup
   - ウィザードは .env の既存値を読み取り、入力を促します。

4. 設定の検証
   - 作成した .env と config/*.yaml をチェックします:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗 (exit 1) 扱いになります:
     python -m kabusys.validate_config --strict

5. data/ ディレクトリやログディレクトリを作成（必要なら）
   - デフォルトのデータパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading sqlite: data/paper_trading.db
   - ログディレクトリのデフォルト: logs/
   - 起動スクリプト実行時に自動作成される場合もありますが、権限に注意してください。

環境変数（主なもの）
-------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABUSYS_ENV (default: development)
  - 値: development | paper_trading | live
  - paper_trading の場合は MockBrokerClient を使用し paper_db に記録
  - live は実際に発注する本番モード（注意して設定）
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (default: "instant") — ペーパートレードの fill モード (instant|partial|never|reject)
- OPENAI_API_KEY — AI モジュールで使用（news_nlp / regime_detector）
- LOG_LEVEL (default: INFO)
- LOG_DIR (default: logs/)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番アラート用（任意）
- KILL_FLAG_CLEAR_ON_START (0/1) — 起動時に kill.flag を自動クリアするか（本番では 0 推奨）
- MONITOR_POLL_INTERVAL — Monitoring ポーリング間隔（秒、default: 60）

自動的な .env ロード
-------------------
- 起動時、プロジェクトルート（.git か pyproject.toml があるディレクトリ）が特定できれば次順で読み込みます:
  1. OS 環境変数（既存優先）
  2. .env（未設定のキーを設定）
  3. .env.local（既存 OS 環境変数を保護しつつ上書き）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Monitoring（デーモン的に定期実行する監視プロセス）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - run_monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを書きます。
  - 停止: プロジェクトルート/data/stop_requested.flag を作成するとポーリングループが検出して終了します。

- ExecutionEngine（注文処理エンジン）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 実行中は data/execution.pid に PID を保存します。stop は stop_requested.flag や kill.flag により検知して停止します。

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB は data/paper_trading.db。--db で指定可能。

プログラム API（ライブラリとして）
--------------------------------
各モジュールはプログラムから直接呼び出せます。例:
- ポートフォリオ関係:
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
- 研究（DuckDB 接続を渡して使用）:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
- AI:
    from kabusys.ai import score_news
    # score_news(conn, target_date, api_key=...) — ai_scores テーブルへ書き込む

監視・Kill Switch の仕組み
-------------------------
- RiskMonitor / SystemMonitor / TradeMonitor がそれぞれチェックを行い、MonitoringEngine がまとめて実行します。
- KillSwitch はリスクやドローダウン等の条件を満たすと data/kill.flag を書き込み、ExecutionEngine 側で検出して安全に停止します。
- kill.flag の自動クリアは設定次第（KILL_FLAG_CLEAR_ON_START）。

ログ
----
- 共通ユーティリティ kabusys.utils.logging_setup.setup_logging を使用してログを統一管理します。
- デフォルト: stdout（コンソール）と logs/<app_name>.log（日次ローテーション、30 日保管）
- ログレベルは LOG_LEVEL で制御できます。

停止方法 / フラグファイル
------------------------
- プロセスを外部から優しく停止する仕組み:
  - data/stop_requested.flag: run_monitoring / run_execution のループが検出して終了
  - data/kill.flag: KillSwitch が書き込む（ExecutionEngine 側で検出して停止）
- kill.flag を明示的にクリアするツールや自動クリアオプション（KILL_FLAG_CLEAR_ON_START）がありますが、本番では自動クリアは推奨されません。

ディレクトリ構成（概要）
----------------------
src/kabusys/
- __init__.py
- config.py                 — 環境変数・設定管理
- config_setup.py           — .env 対話ウィザード
- validate_config.py        — 設定検証スクリプト
- run_monitoring.py         — Monitoring ポーリングループ起動スクリプト
- run_execution.py          — ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py        — ロギング設定ユーティリティ
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
- monitoring/
  - monitoring_db.py        — SQLite 監視 DB 永続化層
  - system_monitor.py       — システム・データ鮮度監視
  - trade_monitor.py        — 注文・約定監視（存在）
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py        — 通知管理（存在）
- execution/                — ExecutionEngine 関連（Engine, BrokerFactory, OrderManager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- ai/
  - news_nlp.py             — ニュース NLP（OpenAI）
  - regime_detector.py      — 市場レジーム判定（OpenAI）
- tools/
  - paper_verification_report.py
- monitoring/ (DB まわり)
- その他: data/ や logs/ は実行時に使用

（上は主要ファイルの抜粋。細かい実装ファイルはソースツリーを参照してください）

トラブルシューティング / 補足
-----------------------------
- sqlite / duckdb のパスに指定した親ディレクトリが存在しない場合、validate_config は警告を出しますが実行スクリプトは起動時にディレクトリを作成することがあります（権限に注意）。
- OpenAI API を使う機能は api_key が必須です。環境変数 OPENAI_API_KEY を設定するか、関数の引数で明示的に渡してください。
- psutil によるプロセス優先度設定や CPU affinity は権限不足で失敗することがあります（警告に留まり継続します）。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、ai/news_nlp 等の実装は空リストチェックを行っています。

ライセンス / バージョン
-----------------------
パッケージのバージョンは src/kabusys/__init__.py の __version__ を参照してください（現時点: 0.1.0）。

貢献 / 開発
-----------
- コードを編集する際は、まず config_setup / validate_config を使ってローカル環境を整え、ユニットテストや簡易スクリプトで動作確認してください。
- AI モジュールや外部 API を使う部分はモックや環境変数の切り替えでテストを行うことを推奨します（外部呼び出しはリトライ処理を含みますがコストがかかります）。

以上がこのコードベースの概要と基本的な使い方です。リポジトリ内のソースを参照すると、各関数・クラスに詳細なドキュメント文字列（docstring）が付与されていますので、実装を深掘りする際は該当ファイルを参照してください。