KabuSys — 日本株自動売買システム
=================================

このリポジトリは日本株の自動売買に関連するモジュール群を含むライブラリ／実行スクリプト集です。
ここではコードベースの主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめます。

プロジェクト概要
----------------
KabuSys は次のような関心事を分離したコンポーネント群で構成されています。

- 実行エンジン（ExecutionEngine）: 発注・リスク管理・オーダー管理を行う（run_execution.py から起動）
- 監視（Monitoring）: システム状態・注文ログ・リスクを定期監視しアラートや Kill Switch を管理（run_monitoring.py / monitoring パッケージ）
- ポートフォリオ構築: 候補選定・重み計算・ポジションサイズ決定（portfolio パッケージ）
- 研究用モジュール: ファクター計算・特徴量探索（research パッケージ）
- AI 関連: ニュースの NLP スコアリング / レジーム判定（ai パッケージ、OpenAI API を利用）
- ユーティリティ: 設定管理、ログ設定、プロセス優先度設定など（utils）
- 管理ツール: .env ウィザード、設定検証、ペーパートレード検証レポート（config_setup, validate_config, tools）

主要機能一覧
-------------
- 環境・設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 対話式ウィザードで .env を生成・更新（kabusys.config_setup）
  - 設定チェック CLI（kabusys.validate_config）
- 実行 / 監視
  - ExecutionEngine 起動スクリプト（run_execution.py）
    - KABUSYS_ENV=paper_trading の場合は MockBroker を利用して paper_trading 専用 DB を使用（本番 DB と完全分離）
  - Monitoring 起動スクリプト（run_monitoring.py）
    - 定期ポーリング、システム状態の永続化、Kill Switch の判定
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
- ポートフォリオ構築
  - 候補選定（スコア降順）、等金額／スコア加重の重み計算
  - セクター集中制限、レジームによる乗数
  - ポジションサイズ計算（単元株丸め、risk_based / equal / score）
- リサーチ機能
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を使用）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI 機能（OpenAI）
  - ニュースを LLM でスコアリングし ai_scores に書き込み（kabusys.ai.news_nlp）
  - マクロニュース + ETF MA を用いた市場レジーム判定（kabusys.ai.regime_detector）
  - API 呼び出しは指数バックオフ・バリデーションを備えフェイルセーフ設計
- 管理ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提:
- Python 3.9+（型注釈等を利用）
- SQLite は標準ライブラリで利用可能
- 必要な外部パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行いたい場合）
推奨インストール（pip）:
  pip install duckdb psutil openai PyYAML

1) リポジトリをクローン / 配置
   - この README の想定はパッケージルートに src ディレクトリが存在する構成です。

2) ディレクトリの作成
   - デフォルトでは data/ と logs/ を使用します。自動で作成されますが、手動で作る場合:
     mkdir -p data logs

3) .env の作成（推奨: 対話式ウィザード）
   - ウィザードを実行して初期 .env を作成:
     python -m kabusys.config_setup
   - もしくは .env.example（存在する場合）を参考に環境変数を設定する。

4) 設定検証
   - 作成後に設定検証を実行:
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗として exit(1) になります:
     python -m kabusys.validate_config --strict

5) 必要な DB の準備
   - DuckDB（分析用）のパスはデフォルト data/kabusys.duckdb（Settings.duckdb_path）
   - SQLite（監視用）のパスはデフォルト data/monitoring.db（Settings.sqlite_path）
   - Paper Trading を使う場合のデフォルト SQLite: data/paper_trading.db（Settings.paper_sqlite_path）
   - monitoring 起動時に monitoring DB の初期テーブルは自動作成されます（init_monitoring_db が実行される）

依存関係のメモ
- PyYAML: config/*.yaml の内容検証に使用。未インストールでも動作します（警告が出ます）。
- OpenAI SDK: ai モジュールを実行する場合に必要。環境変数 OPENAI_API_KEY を設定してください。
- psutil: プロセス優先度 / CPU 使用率などを取得するために必要。

使い方
-------

一般的な実行例
- ExecutionEngine を起動（本番/ペーパー切り替えは KABUSYS_ENV）
  - 本番（注意: 実際に発注されます）:
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
  - ペーパートレード（発注はモック、DB は data/paper_trading.db）:
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution

- Monitoring を起動（定期ポーリング）
  - ポーリング間隔を変更する:
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path に接続し、環境にかかわらず「本番の sqlite_path」を使用する点に注意

- 停止／Kill フラグ
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループが検知して停止します（stop_requested.flag はプロジェクトルート/data/）
  - Kill Switch（監視が検出したリスク時）は data/kill.flag に理由を書き込み、ExecutionEngine の停止をトリガーする設計です
  - 設定 KILL_FLAG_CLEAR_ON_START=1 の場合、起動時に kill.flag を自動クリアします（本番では 0 推奨）

- Paper Trading 検証レポート
  - デフォルトの paper DB を使ってレポートを生成:
    python -m kabusys.tools.paper_verification_report
  - 期間を指定:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示的に指定:
    python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI 機能の実行（例: ニューススコアリング）
  - DuckDB 接続を作り、関数を呼び出す例（簡易）:
    python -c "import duckdb, datetime, os; from kabusys.ai.news_nlp import score_news; conn=duckdb.connect('data/kabusys.duckdb'); print(score_news(conn, datetime.date(2026,4,1), api_key=os.environ.get('OPENAI_API_KEY')))"

  - 注意: OpenAI API キーが必要です。OPENAI_API_KEY 環境変数または関数引数で提供してください。

ログ
- ログはデフォルトで logs/ に保存されます（app_name に応じて <app_name>.log、例: execution.log, monitoring.log）
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一管理されます
- LOG_DIR 環境変数でログディレクトリを上書き可能

主要設定（環境変数）
---------------------
（config.Settings で参照されている主要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (AI 機能に必要)
- LINE_CHANNEL_ACCESS_TOKEN (任意, アラート通知)
- LINE_USER_ID (任意)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト INFO
- PAPER_FILL_MODE (instant | partial | never | reject) — Paper Trading のモック約定挙動
- KILL_FLAG_PATH (デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (0/1)
- MONITOR_POLL_INTERVAL（監視ポーリング、run_monitoring の際に使用可能。デフォルト 60）

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイルとディレクトリ）

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                — 環境変数 / Settings の実装（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading の検証レポート生成ツール
  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（MA + LLM）
    - __init__.py
  - research/
    - factor_research.py      — Momentum / Volatility / Value 等のファクター
    - feature_exploration.py  — 将来リターン・IC 等
    - __init__.py
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・スケーリング
    - risk_adjustment.py      — セクター制限・レジーム乗数
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続化層（テーブル初期化・CRUD）
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — （取引ログ監視）※詳細実装あり
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の管理
    - monitoring_engine.py    — 各 Monitor を束ねるエンジン
    - alert_manager.py        — （通知 / アラート送信）※詳細実装あり
  - utils/
    - logging_setup.py       — ログハンドラの統一設定
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py
  - execution/                — Execution ロジック一式（Engine, OrderManager, BrokerFactory 等）
  - data/                     — （データファイル保管場所: デフォルト data/）

注意事項・運用上のヒント
-----------------------
- 本番運用時は KABUSYS_ENV=live とし、LINE 通知等の設定を必ず確認してください（validate_config は live 時の追加警告を出します）。
- run_monitoring は設定にかかわらず Settings.sqlite_path（本番監視 DB）へ書き込みます。テスト目的で監視 DB を分離したい場合は環境変数で SQLITE_PATH を上書きしてください。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（デフォルト data/paper_trading.db）を利用します。本番 DB とペーパー DB は混ざらないよう設計されています。
- kill.flag / stop_requested.flag / execution.pid などのファイルはプロジェクトルート/data に作成されます。これらを確認することでプロセスの停止指示や PID 管理が可能です。
- OpenAI 利用部分は API 呼び出しに失敗してもゼロやスキップでフォールバックするよう実装されていますが、API キーやコスト・レート制限には注意してください。

トラブルシューティング（よくある問題）
-------------------------------------
- DuckDB が無い / import error: pip install duckdb
- psutil が無い: pip install psutil
- OpenAI が無い（AI 機能エラー）: pip install openai
- YAML 検証をしたいが PyYAML が無い場合、validate_config は YAML の内容検証をスキップして警告を出します。PyYAML を入れると詳細検証が可能です。
- ログファイルが書けない場合、LOG_DIR 環境変数で書き込み可能なディレクトリを指定するか、ログディレクトリの所有権・権限を確認してください。

開発者向け補足
---------------
- ほとんどのモジュールは純粋関数または DB 接続を受け取る形で設計されており、単体テストが書きやすい構造です。
- AI 呼び出し等、外部 I/O を行う関数は内部で呼出しラッパー（_call_openai_api 等）を分離しており、テスト時に patch/モックしやすくなっています。
- 設定自動ロードはプロジェクトルート（.git または pyproject.toml による検出）を基準に行われます。テスト時に自動ロードを抑制するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / コントリビューション
---------------------------------
- 本リポジトリに付随するライセンス情報がある場合はそちらに従ってください（README には記載無し）。

以上がこのコードベースの概要・導入・使い方のまとめです。個別のコマンド例や挙動の詳細（ExecutionEngine の設定や OrderManager の仕様等）について追加ドキュメントが必要であれば、対象モジュールを指定していただければ詳細な README セクションを作成します。