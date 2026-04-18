README
=====

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージです。本リポジトリは以下の主要機能群を提供します:
- 発注実行エンジン（ExecutionEngine）とそれを保護するリスク管理
- システム稼働監視（SystemMonitor / MonitoringEngine）と Kill Switch
- Paper Trading 用の分離された DB と検証ツール
- ファクター計算・特徴量解析（Research）
- ニュース NLU を用いたセンチメント評価（OpenAI を利用）
- ポートフォリオ構築・ポジションサイズ計算の純粋関数群
- 環境設定ウィザード・設定検証 CLI、ログ設定ユーティリティ 等

重要な設計方針（抜粋）
- 本番稼働時と Paper Trading（模擬取引）を明確に分離（DB/振る舞い）
- ルックアヘッドバイアスを避ける設計（日時参照を直接使わない等）
- OpenAI 呼び出しはリトライ・バリデーションを行いフェイルセーフ化
- ログ・DB はデータディレクトリ下に保存（デフォルト: data/, logs/）

主な機能一覧
----------------
- 実行系
  - run_execution.py: ExecutionEngine の起動（KABUSYS_ENV に応じて MockBroker を利用）
  - ブローカーファクトリ、OrderManager、RiskManager、Reconciler などの組み立て
- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔を調整可）
  - monitoring_engine: System/Trade/Risk 各モニタの束ね動作、Kill Switch 評価、Alert 発行
  - monitoring_db: SQLite を用いた永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - risk_monitor, trade_monitor, system_monitor, kill_switch
- 研究 / 分析
  - research.factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - research.feature_exploration: 将来リターン計算、IC（Spearman）等
- AI（OpenAI）
  - ai.news_nlp: ニュース記事を LLM で評価し ai_scores テーブルへ書き込む
  - ai.regime_detector: ETF / マクロニュースを統合して市場レジーム判定を行い market_regime テーブルへ書込
- ポートフォリオ構築
  - portfolio.portfolio_builder: 候補選定・重み付け（等金額/スコア加重）
  - portfolio.position_sizing: 単元丸め・リスクベース/等配分の株数算出
  - portfolio.risk_adjustment: セクター上限・レジーム乗数
- ユーティリティ
  - config_setup.py: .env を対話で生成・更新するウィザード
  - validate_config.py: 起動前の設定検証 CLI（.env + config/*.yaml の存在/妥当性チェック）
  - utils.logging_setup: stdout + 日次ローテートファイルハンドラ設定
  - utils.process_priority: プラットフォーム差を吸収したプロセス優先度設定

セットアップ手順
----------------
前提:
- Python 3.9 以上（コードは型ヒント / 一部機能で新しめの Python を想定）
- SQLite（stdlib）、DuckDB、psutil、openai（AI 機能利用時）、PyYAML（設定検証で YAML をチェックする場合）

推奨的な依存パッケージ（一例）
- duckdb
- psutil
- openai
- pyyaml

インストール例（仮に requirements.txt がない場合）:
- 仮想環境作成:
  - python -m venv .venv
  - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
- pip インストール:
  - pip install duckdb psutil openai pyyaml

ディレクトリと初期ディレクトリ作成:
- プロジェクトルートで以下を作成しておくと便利:
  - mkdir -p data logs

環境変数設定:
- .env を用意（config_setup ウィザード推奨）
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- OpenAI 機能を使う場合:
  - OPENAI_API_KEY
- 代表的なその他変数（デフォルトがあるため必須ではない）:
  - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
  - LOG_LEVEL, LOG_DIR, PID_FILE_PATH, KILL_FLAG_CLEAR_ON_START など

.env 作成支援:
- 対話式ウィザード:
  - python -m kabusys.config_setup
- 手動例 (.env):
  - JQUANTS_REFRESH_TOKEN=your_token_here
  - KABU_API_PASSWORD=your_password_here
  - KABUSYS_ENV=development
  - OPENAI_API_KEY=sk-...
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db

設定検証:
- python -m kabusys.validate_config
- --strict を付けると警告もエラー扱い: python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------
起動スクリプトは module として起動するのが推奨です（プロジェクトルートにて実行）。

1) ExecutionEngine を起動（実際の発注 / Paper Trading を切り替え）
- 本番または development/paper_trading の挙動は KABUSYS_ENV による:
  - KABUSYS_ENV=paper_trading のとき、MockBrokerClient を使用し paper DB に記録
- 起動:
  - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag が作成されると安全に停止します
  - 実行時は data/execution.pid（デフォルト）に PID ファイルを作成します

2) 監視ループを起動
- MONITOR_POLL_INTERVAL でポーリング間隔を秒指定（デフォルト 60 秒）
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は常に本番 sqlite_path を使う（Settings により決定）
- 監視スレッドは data/stop_requested.flag の存在で停止します

3) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

4) AI（ニューススコア / レジーム判定）
- ai.score_news / ai.score_regime は DuckDB 接続と日付を受け取り DB に書き込む関数 API です
- CLI ラッパーは用意していませんが、スクリプトから呼ぶ際は OPENAI_API_KEY を環境変数に設定してください
- 例（Python スクリプト内）:
  - from openai import OpenAI
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, target_date=date(2026,4,10), api_key=os.environ["OPENAI_API_KEY"])

5) .env の自動読み込み
- デフォルトでプロジェクトルートの .env と .env.local を自動読み込みします（OS 環境変数を優先）
- 自動ロードを無効化するには:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

注意: kill.flag / stop flag
- 実行停止操作（Kill Switch）
  - Kill Switch（監視がトリガーした場合）: Settings.kill_flag_path（デフォルト data/kill.flag） に理由文字列が書き込まれる
  - ExecutionEngine は起動時に kill flag を検査し、起動中は kill.flag の存在で停止判定する（kill_flag_clear_on_start による挙動に注意）
- 手動停止要求:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring のループが検知して安全に停止します

ログ
----
- ログの初期化は kabusys.utils.logging_setup.setup_logging を使用
- stdout と logs/<app_name>.log（日次ローテート、30日保持）に出力
- LOG_DIR 環境変数または setup_logging の引数で変更可能

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 配下の主な構成です（抜粋）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動ロード）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py            — ニュースの LLM スコアリング / DB 書き込み
    - regime_detector.py     — 市場レジーム判定
  - monitoring/
    - monitoring_db.py       — monitoring 用 SQLite 永続層
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - system_monitor.py      — システム監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - (trade_monitor 等)
  - execution/                — Execution 関連のコンポーネント（BrokerFactory, Engine 等）
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

補足 / 運用メモ
--------------
- Paper Trading（KABUSYS_ENV=paper_trading）は発注をモック化し DB を data/paper_trading.db に保存します。本番 DB（monitoring.db 等）と分離されます。
- run_monitoring は環境にかかわらず「本番 sqlite_path」を監視用に開きます（監視ログは共通 DB）。
- MONITOR_POLL_INTERVAL は正の整数を秒で指定。無効値はデフォルト 60 秒にフォールバックします。
- process_priority.set_process_priority("high") を起動直後に呼んでプロセス優先度を上げます（失敗しても警告ログで継続）。
- DuckDB の接続は research / ai / regime などで積極的に使用します。DuckDB ファイルパスは DUCKDB_PATH で設定可能。

ライセンス / 貢献
-----------------
- 本 README ではライセンス情報は含めていません。実プロジェクトでは LICENSE ファイルをリポジトリルートに置いてください。
- 貢献方法やコーディング規約、テスト方法などは別ドキュメントにまとめることを推奨します。

以上。README の補足や特定モジュールの詳細ドキュメント化（API 仕様、設定項目一覧の自動生成など）を希望する場合はその旨を教えてください。