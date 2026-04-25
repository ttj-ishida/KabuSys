README
=====

概要
----
KabuSys は日本株自動売買・リサーチ・監視を目的とした Python ベースの小規模フレームワークです。
本リポジトリは以下の責務を持つモジュール群を含みます。

- 自動発注実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor）および Kill Switch
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- リサーチ（ファクター計算・IC/統計解析）
- ニュース NLP（OpenAI を使ったセンチメント評価）
- ペーパートレード検証レポート生成ツール

主要設計方針として、
- 本番 DB / ペーパートレード DB を分離
- ルックアヘッドバイアスを避ける（datetime.today() を直接参照しない実装）
- フェイルセーフ（外部 API 失敗時でも安全に継続）を重視
が採用されています。

機能一覧
--------
- 環境設定ウィザード: .env の対話的作成・更新（kabusys.config_setup）
- 設定検証: .env や config/*.yaml の基本チェック（kabusys.validate_config）
- 実行エンジン起動スクリプト: run_execution.py（本番 / paper_trading を考慮）
- 監視ループ起動スクリプト: run_monitoring.py（システム監視・アラート・Kill Switch）
- 監視 DB 層: SQLite に監視ログを永続化（monitoring_db）
- リスク監視: ドローダウン・ポジション上限の検出（risk_monitor）
- ニュース NLP: OpenAI を用いた銘柄別センチメントスコアリング（ai.news_nlp）
- 市場レジーム判定: ma200 とマクロニュースの合成（ai.regime_detector）
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ計算（portfolio/*）
- リサーチ: ファクター計算・将来リターン・IC 計算等（research/*）
- ペーパートレード検証レポート: tools/paper_verification_report.py により指標出力

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone … && cd <repo>

2. Python 環境（推奨: venv）を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須ライブラリ（例）
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML の検証に任意で使用）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt はリポジトリに含まれていないため、必要に応じて上記をプロジェクトに合わせて固定してください。）

4. 環境変数 (.env) の準備
   - 対話式に作る（推奨）:
     - python -m kabusys.config_setup
     - オプション: --env-file <path>
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 本機能を使う場合に必要な変数
     - OPENAI_API_KEY : ニュース NLP / レジーム判定で必須
     - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
     - PAPER_TRADING_SQLITE_PATH : paper_trading 用 DB（paper_trading 時）
     - PAPER_FILL_MODE : paper_trading の約定挙動（instant|partial|never|reject）
     - DUCKDB_PATH / SQLITE_PATH : DB ファイルパス（デフォルトは data/ 以下）
     - LOG_LEVEL / LOG_DIR : ログ設定
   - 自動読み込み:
     - プロジェクトルートに .env/.env.local がある場合、kabusys.config が起動時に自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - サンプルは config_setup により生成されます。

5. DB ディレクトリの作成
   - data ディレクトリ（および logs）を作る:
     - mkdir -p data logs

使い方
------
※ 実行はパッケージルート（pyproject.toml/.git が存在するディレクトリ）で行ってください。モジュールはパッケージ実行（-m）を想定しています。

1. 設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - オプション: --env-file path/to/.env

2. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにする: python -m kabusys.validate_config --strict

3. 実行エンジン起動（ExecutionEngine）
   - 本番/開発/ペーパートレードは KABUSYS_ENV に依存
   - 起動:
     - python -m kabusys.run_execution
   - 挙動:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録して本番 DB と分離します。
     - 起動前に data/stop_requested.flag が存在する場合は起動せず終了します。
     - 実行中は data/execution.pid に PID を書きます。
     - 停止は data/stop_requested.flag を作成することで通知できます（監視側や手動で）。

4. 監視ループ起動（Monitoring）
   - python -m kabusys.run_monitoring
   - 特記事項:
     - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）。1 未満の値は無効でデフォルトにフォールバックします。
     - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して監視ログを書きます（monitoring 用の単一 DB）。
     - 停止フラグ: data/stop_requested.flag を検知してループを終了します。

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - --from YYYY-MM-DD --to YYYY-MM-DD
   - DB 指定:
     - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可能

6. ニュース NLP / レジーム判定（ライブラリ関数として利用）
   - ai.news_nlp.score_news(conn, target_date, api_key=None)
     - DuckDB 接続を渡して指定日のニューススコアを ai_scores テーブルへ書き込みます。
     - api_key を省略すると環境変数 OPENAI_API_KEY を参照します（未設定時は ValueError）。
   - ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - market_regime テーブルへ書き込みます。OPENAI_API_KEY が必要（記事が存在しない場合は LLM 呼び出しをスキップして中立扱い）。

主要ファイル / 実行ポイント
-------------------------
- スクリプト
  - src/kabusys/run_execution.py — ExecutionEngine 起動
  - src/kabusys/run_monitoring.py — SystemMonitor ポーリングループ起動
  - src/kabusys/config_setup.py — .env 対話式ウィザード
  - src/kabusys/validate_config.py — 設定検証 CLI
  - src/kabusys/tools/paper_verification_report.py — ペーパートレード検証レポート

- 設定・ユーティリティ
  - src/kabusys/config.py — 環境変数 / Settings クラス（.env 自動ロードロジック含む）
  - src/kabusys/utils/logging_setup.py — 統一ログ設定
  - src/kabusys/utils/process_priority.py — プロセス優先度 / CPU affinity 設定

- 監視
  - src/kabusys/monitoring/monitoring_db.py — SQLite テーブル初期化・読み書き
  - src/kabusys/monitoring/system_monitor.py — システム・データ鮮度監視
  - src/kabusys/monitoring/trade_monitor.py — （発注ログ監視）*（詳細実装はリポジトリに依存）*
  - src/kabusys/monitoring/risk_monitor.py — ドローダウン・ポジション上限監視
  - src/kabusys/monitoring/kill_switch.py — kill.flag 制御
  - src/kabusys/monitoring/monitoring_engine.py — 各 Monitor を束ねるループ

- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py
  - src/kabusys/portfolio/position_sizing.py
  - src/kabusys/portfolio/risk_adjustment.py

- リサーチ / AI
  - src/kabusys/research/factor_research.py
  - src/kabusys/research/feature_exploration.py
  - src/kabusys/ai/news_nlp.py
  - src/kabusys/ai/regime_detector.py

- その他
  - src/kabusys/__init__.py — パッケージ定義・バージョン

ディレクトリ構成（概略）
---------------------
プロジェクトルート
- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - risk_monitor.py
      - trade_monitor.py
      - monitoring_engine.py
      - kill_switch.py
    - execution/           # ExecutionEngine 関連（エンジン・注文管理等）
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
- data/                   # DB・フラグファイル等（実行時に使用）
  - monitoring.db (デフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/                   # ログ（logging_setup が書き込む）

重要な動作注意点
----------------
- 環境ごとの DB 分離:
  - Monitoring は常に settings.sqlite_path（デフォルト data/monitoring.db）を使用します。
  - ExecutionEngine は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（PAPER_TRADING_SQLITE_PATH）を使用します（本番 DB と完全分離）。

- Kill Switch / stop フラグ:
  - run_execution/run_monitoring は data/stop_requested.flag を監視し、検出時に安全にシャットダウンします。
  - kill_switch は data/kill.flag を書き込むことで ExecutionEngine の強制停止を促す仕組みです。KILL_FLAG_CLEAR_ON_START の設定に注意（本番では 0 推奨）。

- ロギング:
  - setup_logging() はコンソール（stdout）と日次ローテートファイル出力（logs/<app_name>.log）を設定します。
  - LOG_DIR 環境変数または引数でログ保存先を指定できます。

- 外部 API:
  - OpenAI を利用する機能は OPENAI_API_KEY を必要とします。API 呼び出しはリトライ＆バックオフ処理を含みますが、最終的に失敗した場合は安全にフォールバック（0.0 など）します。
  - PyYAML がない場合は config/*.yaml の内容検証をスキップします（validate_config が警告を出します）。

よくあるトラブルシューティング
------------------------------
- .env が読み込まれない:
  - プロジェクトルート判定は .git または pyproject.toml を基準とします。これらが存在しない場所で実行していると .env 自動ロードがスキップされます。手動で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するか、明示的に環境変数を設定してください。

- psutil / duckdb が見つからない:
  - 事前に pip install psutil duckdb を実行してください。プロセス優先度（set_process_priority）や CPU affinity は OS に依存し、権限不足で警告が出ますが起動は続行します。

- OpenAI 呼び出しでレート制限やタイムアウト:
  - 内部で指数バックオフと再試行を実装しています。長時間失敗する場合は API キー・ネットワーク・料金制限を確認してください。

付記
----
- 本 README はソースコードに基づいて作成されています。各モジュールの詳細な振る舞いや追加の CLI オプションは、該当ソースファイルの docstring / 関数コメントを参照してください。
- 実運用前に python -m kabusys.validate_config を実行し、設定とファイルパスを必ず検証してください。