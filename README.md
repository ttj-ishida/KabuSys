KabuSys — 日本株自動売買システム（簡易リポジトリ説明書）
=================================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤のコード群です。本リポジトリは以下の主要機能を持ち、実運用と開発（ペーパートレード）両方に対応するよう設計されています。

- 発注エンジン（ExecutionEngine）
- 監視ツール群（System / Trade / Risk モニタ）
- ポートフォリオ構築（銘柄選定・重み付け・株数決定）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP によるセンチメント、レジーム判定）
- 環境設定ウィザード・設定検証ツール
- ペーパートレード検証レポート生成スクリプト

特徴
----
- 環境変数（.env）での設定管理、自動読み込み機構（config.py）
- 本番 DB とペーパートレード DB の分離（PAPER_TRADING 時は data/paper_trading.db を使用）
- DuckDB を使ったリサーチ用データアクセス（prices_daily / raw_financials 等）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント・レジーム判定（API キー必須）
- ロギングは統一された setup_logging でコンソール + 日次ローテートファイル出力
- kill.flag / stop_requested.flag / pid ファイルを用いたプロセス制御（冪等性に配慮）

セットアップ手順
----------------

1. リポジトリをクローンして Python 仮想環境を作成・有効化

   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要なパッケージをインストール

   - requirements.txt 等がある想定ですが、主要依存は以下（プロジェクトにより変更あり）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定検証で config/*.yaml をパースする場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

3. .env を用意（対話式ウィザード推奨）

   - ウィザードを使う:
     - python -m kabusys.config_setup
   - 主要な環境変数（抜粋）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB。デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能利用時に必須）
     - LOG_LEVEL（例: INFO）
     - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant | partial | never | reject）
     - KILL_FLAG_CLEAR_ON_START（起動時に kill.flag をクリアするか: 0/1）

   - 自動環境読み込み:
     - config.py はプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動ロードします。
     - テスト等で自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. データディレクトリ作成
   - デフォルトでは data/ や logs/ にファイルを書きます。実行前に権限とディレクトリを確認してください。

使い方（主要スクリプト・API）
----------------------------

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit(1)

- ExecutionEngine（発注実行）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が既に存在する場合は起動しません。
  - 停止は data/stop_requested.flag を書くか、kill.flag を利用（監視コンポーネント経由で作成されます）。

- Monitoring（監視ループ）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60）。
  - Monitoring 側は KABUSYS_ENV にかかわらず settings.sqlite_path（つまり本番 sqlite_path）を使用して監視データを保存します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db
  - レポートは稼働率・注文成功率・送信率・レイテンシ等を算出し PASS/FAIL を出します（閾値はスクリプト内で定義）。

- AI 関連（ニュース NLP / レジーム判定）
  - 関数経由で利用:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OPENAI_API_KEY（または関数引数で api_key）を必ず設定してください。
  - news_nlp モジュールは raw_news / news_symbols / ai_scores テーブルを使用します。
  - regime_detector は prices_daily・raw_news を参照して market_regime に書き込みます。

- ライブラリ利用例
  - ポートフォリオ構築ユーティリティ:
    - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes 等
  - リサーチ:
    - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

重要ファイル・フラグ
-------------------
- data/stop_requested.flag
  - 起動スクリプト（run_execution/run_monitoring）はこのファイルの存在を検出して停止します。

- data/kill.flag
  - KillSwitch（監視側）が条件到達時に書き込むファイル。ExecutionEngine の停止トリガとして利用。

- data/execution.pid
  - 実行中の ExecutionEngine が PID を書き込むファイル（設定により別パス可）。

- logs/<app_name>.log
  - setup_logging() により生成される日次ローテートログファイル（デフォルト logs/ ディレクトリ）。

ディレクトリ構成
----------------
（src/kabusys 以下をルートにした主要な構成）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 読み込みと Settings クラス
  - config_setup.py           — 対話式 .env ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py      — マクロ + MA による市場レジーム判定
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数決定・キャップ・丸めロジック
    - risk_adjustment.py      — セクターキャップ・レジーム乗数など
    - __init__.py
  - research/
    - factor_research.py      — Momentum/Value/Volatility の計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite の監視 DB レイヤ（テーブル初期化・CRUD）
    - system_monitor.py       — システム状態・データ鮮度チェック
    - trade_monitor.py        — （存在）注文滞留・約定異常検出（実装ファイルあり）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag の作成・管理
    - monitoring_engine.py    — 各モニタの束ね
  - execution/                — Execution 関連（broker factory, engine, order_manager 等）
  - utils/
    - logging_setup.py        — ログの統一設定
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

運用上の注意
------------
- 本番（KABUSYS_ENV=live）では設定を十分に確認してから起動してください。validate_config にて live モードのガードチェックがあります（LINE 通知設定等の警告）。
- Monitoring は本番 sqlite_path を使用して監視データを記録します（KABUSYS_ENV に依存せず）。
- OpenAI を利用する機能は API のコストとレイテンシを考慮して運用してください。失敗時にはフェイルセーフ（スコア 0、あるいはスキップ）する設計ですが、API キー漏洩には注意してください。
- データベースやログディレクトリのパーミッションに注意。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します。
- 単体テストや CI 実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動 .env 読み込みを無効化することを推奨します。

FAQ（よくある質問）
-----------------
Q: ペーパートレードと本番の DB は分離されていますか？
A: はい。Execution は settings.is_paper に応じて paper_sqlite_path（デフォルト data/paper_trading.db）を使用します。Monitoring は常に sqlite_path（監視 DB）を使用します。

Q: ログレベルはどう設定しますか？
A: .env の LOG_LEVEL で設定できます。また setup_logging() の引数から上書き可能です。

Q: .env の自動読み込みを無効化できますか？
A: はい。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードをスキップします。

追加情報・参照
--------------
- 各スクリプト冒頭に使い方（docstring）や実行例を記載しています。まずは python -m kabusys.config_setup → python -m kabusys.validate_config の順で設定を整えることを推奨します。
- ロジック詳細（ポートフォリオ設計、リスク制御、AI プロンプト等）は各モジュールのドキュメント文字列とコードコメントを参照してください。

お問い合わせ
------------
リポジトリ内のコードを参照の上、不明点があれば該当モジュール（例: config.py / monitoring_db.py / ai/news_nlp.py）を確認してください。必要であれば実行ログ（logs/<app>.log）を添えて質問してください。

--- End of README ---