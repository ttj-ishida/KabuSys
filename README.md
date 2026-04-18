README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。本リポジトリは以下の主要機能を持つモジュール群で構成されています:

- 発注実行エンジン（ExecutionEngine）とその起動スクリプト
- システム / 注文 / リスクの監視機能（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算などの純粋関数群（portfolio）
- ファクター計算・特徴量探索などのリサーチ機能（research）
- ニュース NLP / レジーム判定（OpenAI を利用する AI モジュール）
- 環境設定ウィザード・設定検証ツール
- ペーパートレード検証レポート生成ツール

主要設計方針の要点：
- 設定は .env（および .env.local）または環境変数で管理。Settings クラスで集約。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された専用 SQLite（data/paper_trading.db）を使用。
- 監視・ログは SQLite / DuckDB を利用し、ログはコンソール + 日次ローテートファイルに出力。
- OpenAI を利用する機能は API キーが必要（安全に環境変数で指定）。

機能一覧
--------
主な機能（抜粋）:

- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV によって本番/ペーパートレードを切り替え。
  - paper_trading モードでは MockBrokerClient を使用し、paper_trading 用 DB に記録。
  - 起動時にプロセス優先度を high に設定し、停止は data/stop_requested.flag で指示可能。

- run_monitoring.py
  - SystemMonitor のポーリングループを実行。監視間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視ではシステムリソース・データ鮮度・Execution プロセスの生存などを記録。

- monitoring/* モジュール
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine などの監視ロジック。
  - MonitoringDB: SQLite に対する永続化層（テーブル作成・マイグレーション含む）。

- portfolio/*
  - 候補選定、重み計算、セクター上限適用、ポジションサイズ計算等の純粋関数群。

- research/*
  - ファクター計算（momentum / value / volatility）、将来リターン、IC（スピアマン）等の分析用関数。DuckDB に直接クエリ。

- ai/*
  - news_nlp.score_news: raw_news を OpenAI でスコアリングして ai_scores に書き込む。
  - regime_detector.score_regime: ma200 とマクロニュースからレジーム（bull/neutral/bear）を判定し DB に書き込む。

- tools/paper_verification_report.py
  - ペーパートレード DB（data/paper_trading.db）から期間指定で検証レポートを生成。稼働率・注文成功率・レイテンシ等を評価。

セットアップ手順
----------------

1. リポジトリをクローン（既にコードがある場合は不要）:
   git clone <repo-url>

2. Python と依存パッケージのインストール
   - 推奨: Python 3.9+
   - 必要な主なパッケージ（機能により任意）
     - duckdb
     - psutil
     - openai (AI 機能を使用する場合)
     - PyYAML (config 検証で YAML 検査を行う場合)
   例:
     python -m pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれに従ってください（本リポジトリには未提供の想定）。

3. .env の作成（対話式ウィザード推奨）
   - ウィザードで初期 .env を生成:
       python -m kabusys.config_setup
   - 生成後、内容を確認・編集してください（.env は決して Git にコミットしないこと）。

4. 設定の検証
     python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリを作成（必要なら）
   - デフォルトでは data/ 配下に SQLite・PID・フラグファイル等が置かれます：
     mkdir -p data logs

主な環境変数（抜粋）
-------------------
Settings および config_setup の内容に基づく主な環境変数:

- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD: kabuステーション API パスワード

- 任意 / デフォルト:
  - KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
  - OPENAI_API_KEY: OpenAI を使う場合の API キー
  - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant / partial / never / reject）
  - KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

自動 .env ロード:
- デフォルトでプロジェクトルートの .env と .env.local を自動的に読み込みます（OS 環境変数優先）。
- 自動ロードを無効化する場合:
    export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方
------

1) 環境作成・検証（推奨）

- .env をウィザードで生成:
    python -m kabusys.config_setup

- 設定を検証:
    python -m kabusys.validate_config
  （--strict オプションで警告も失敗にできます）

2) ExecutionEngine の起動 / 停止

- 本番/開発/ペーパーは KABUSYS_ENV で制御。ペーパートレードは専用 DB に記録され、本番 DB と分離されます。

- ペーパートレードを使う例:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 標準（KABUSYS_ENV を .env に設定している場合はその値で起動）:
    python -m kabusys.run_execution

- 停止方法:
  - 実行中のエンジンはプロセス内で stop を監視する他、外部から停止指示するにはプロジェクトルートの data/stop_requested.flag を作成してください。run_execution は起動時およびループ中にこのフラグを検出して優雅に停止します。

- 実行時の PID ファイル:
  - 実行時に data/execution.pid（デフォルト）へ PID を書き込みます（設定で変更可能）。

3) 監視ループ起動

- SystemMonitor のポーリングループを起動:
    python -m kabusys.run_monitoring

- ポーリング間隔を秒で上書き:
    export MONITOR_POLL_INTERVAL=30
    python -m kabusys.run_monitoring

- 監視ループの停止:
  - プロジェクトルートの data/stop_requested.flag を作成するとループは検出して終了します。

注意:
- run_monitoring は Monitoring 用 DB として Settings.sqlite_path（監視用 DB）を環境に関係なく使用します（監視ログは本番 DB を参照する想定）。

4) ペーパートレード検証レポート

- SQLite（デフォルト data/paper_trading.db）から期間指定でレポートを出力:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- デフォルト DB パスを上書きするには --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH を指定します。

5) AI モジュールの利用（OpenAI）

- news_nlp.score_news と regime_detector.score_regime はプログラムから呼び出す関数です。OpenAI API キーは環境変数 OPENAI_API_KEY に設定するか、関数引数で渡します。
- 例（簡易的なスクリプト）:
    python - <<'PY'
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    cnt = score_news(conn, target_date=date(2026,4,11), api_key="sk-...")
    print("written:", cnt)
    PY`
- OpenAI 呼び出しはレート制限やエラーに対してリトライやフォールバックで耐性を持つ実装になっていますが、API コストに注意してください。

6) ログ
- ログは stdout と logs/<app_name>.log（日次ローテーション）に出力されます。ログディレクトリは LOG_DIR 環境変数かデフォルト logs/ を使用します。

停止フラグ / キルスイッチ
-----------------------
- run_execution / run_monitoring の外部制御:
  - data/stop_requested.flag: スクリプトのループを終了させる汎用停止フラグ（両スクリプトで使用）。
  - KillSwitch（監視側）: 条件を満たすと data/kill.flag を作成して ExecutionEngine に停止を促す仕組み。kill.flag は ExecutionEngine 起動時に設定に応じてクリアすることも可能（KILL_FLAG_CLEAR_ON_START=1。ただし本番では推奨されません）。

ディレクトリ構成
----------------
パッケージは src/kabusys 以下に実装されています。主要ファイルと役割は以下の通り:

- src/kabusys/
  - __init__.py                — パッケージ定義
  - config.py                  — Settings クラス（環境変数/.env の読み込み・検証）
  - config_setup.py            — .env を対話式で生成するウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

- src/kabusys/utils/
  - logging_setup.py           — ログ設定ユーティリティ
  - process_priority.py        — プロセス優先度 / CPU affinity 設定ユーティリティ

- src/kabusys/monitoring/
  - monitoring_db.py           — SQLite 永続化層（テーブル作成 / CRUD）
  - system_monitor.py          — システム状態・データ鮮度チェック
  - trade_monitor.py           — 注文ログ監視（滞留・異常価格検出など）※該当実装ファイル参照
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag の生成 / 管理
  - alert_manager.py           — アラート管理（LINE 等への通知、実装参照）
  - monitoring_engine.py       — 複数 Monitor を束ねる実行エンジン

- src/kabusys/portfolio/
  - portfolio_builder.py       — 候補選定・重み
  - position_sizing.py         — 株数計算・スケールダウン・丸め処理
  - risk_adjustment.py         — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py         — momentum/value/volatility 等の計算
  - feature_exploration.py     — 将来リターン / IC / 統計サマリ
  - __init__.py                — 公開 API

- src/kabusys/ai/
  - news_nlp.py                — ニュースを LLM でスコア化して ai_scores に保存
  - regime_detector.py         — ma200 とマクロニュースでレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- その他
  - data/                      — デフォルトの DB / PID / フラグファイル置き場（実行時に自動生成）
  - logs/                      — ログファイル出力先（デフォルト）

開発上の注意点 / FAQ
--------------------
- .env は機密情報を含むため Git にコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START=0 を強く推奨します（自動クリアは危険）。
- AI 機能を使う場合は OPENAI_API_KEY をセットしてください。API 呼び出しは料金が発生します。
- DuckDB / SQLite のパスは Settings で変更可能です。monitoring は Monitoring DB（sqlite_path）を使う点に注意してください。
- 依存ライブラリのバージョンはプロジェクトポリシーに合わせて固定してください（requirements.txt / poetry 等で管理を推奨）。

貢献・拡張
----------
- strategy / execution の各コンポーネントは分離設計なので、ブローカークライアントや戦略モデルは容易に差し替え可能です。
- research モジュールは DuckDB 上のテーブル定義（prices_daily / raw_financials）に依存しています。データ供給パイプラインを整備してデータを投入してください。

ライセンス
----------
- （ここにプロジェクトのライセンス情報を記載してください）

以上。README に不足している点や、特定の機能のドキュメント化（例: ExecutionEngine の引数や OrderManager の仕様など）を希望される場合は、その対象を指定してください。