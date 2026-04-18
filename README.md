README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤向けのライブラリ兼起動スクリプト群です。本リポジトリは以下の機能を提供します。

- ─ ExecutionEngine：実際の（あるいはペーパー）発注エンジン起動スクリプト
- ─ Monitoring：システム状態・注文リスクの監視と Kill Switch
- ─ Portfolio：銘柄選定、重み付け、発注株数決定などのポートフォリオ構築ユーティリティ
- ─ Research：DuckDB を使ったファクター計算・特徴量解析ユーティリティ
- ─ AI：OpenAI を利用したニュースセンチメント評価・レジーム判定
- ─ Tools：Paper Trading の検証レポート生成などのユーティリティスクリプト
- ─ 設定関連のコマンドラインツール（.env 作成ウィザード / 設定検証）

特徴一覧
---------
- 環境変数ベースの設定（.env 自動読み込み）
- DuckDB / SQLite を併用したデータ管理（分析用 DuckDB、監視/発注ログ用 SQLite）
- Monitoring と Kill Switch による自動停止およびアラート連携（LINE など）
- Paper Trading モードによる本番 DB と完全分離（data/paper_trading.db）
- OpenAI（gpt-4o-mini）を用いたニュース NLP / マクロセンチメント判定（フェイルセーフ設計）
- ポートフォリオ構築、セクター制約、リスクベースの発注量計算用の純粋関数群（テスト容易）

セットアップ手順
----------------

1. リポジトリをクローン／展開する
   - プロジェクトルートに移動してください（pyproject.toml や .git を基準に自動検出が行われます）。

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須（主なもの）:
     - duckdb
     - psutil
     - openai
   - 開発/オプション:
     - PyYAML（config/*.yaml の検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がない場合は上記パッケージを個別にインストールしてください）

4. .env を作成する
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - 手動で作成する場合、.env.example を参考に .env を作成してください（.env は絶対にコミットしないでください）。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があるとエラー/警告が表示されます。--strict を付けると警告も失敗にします。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用トークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV: execution の実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログ保存先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

重要なファイル / フラグ
----------------------
- data/stop_requested.flag: run_monitoring / run_execution が検出するとループを止めるための外部停止フラグ
- data/kill.flag: Kill Switch が発行する停止フラグ（ExecutionEngine が起動を停止する）
- data/execution.pid: ExecutionEngine の PID ファイル（存在は Engine の起動中を示す）

使い方（コマンド・スクリプト）
----------------------------

1. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup
   - 対話的に .env を生成・更新します。

2. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も exit(1) 扱い。

3. ExecutionEngine 起動（本番 / paper_trading を Settings に従って切替）
   - python -m kabusys.run_execution
   - 特徴:
     - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（data/paper_trading.db）に記録します。
     - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します。
     - 実行中、data/stop_requested.flag を作成するとスレッド停止をトリガーします。
     - プロセス優先度は起動時に "high" に設定されます（set_process_priority）。

4. Monitoring 起動
   - python -m kabusys.run_monitoring
   - 特徴:
     - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60 秒）。
     - 監視は本番用 sqlite_path を常に使用（KABUSYS_ENV に依存しない）。
     - stop_requested.flag を検出すると監視ループを終了。

5. Paper Trading 検証レポート生成ツール
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（--db で代替可）
   - 稼働率、注文成功率、レイテンシなどを集計して PASS/FAIL 判定を出力します。

6. AI/Research の利用
   - ニュースセンチメント生成:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key=...)
     - OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key=...)
   - DuckDB 接続を渡して各種ファクター計算:
     - from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

ログ設定
-------
- setup_logging(app_name="execution") などで一貫したログ設定が行われます。
- デフォルトでは stdout（コンソール）と logs/<app_name>.log（日次ローテーション、30日保持）に出力されます。
- LOG_DIR / LOG_LEVEL 環境変数で調整可能。ログディレクトリ作成に失敗するとコンソールのみになります。

監視・Kill Switch の挙動
-----------------------
- Monitoring 系は SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行し、AlertManager 経由で通知可能（LINE 等）。
- RiskMonitor は drawdown（ドローダウン）やポジション上限をチェックし、必要に応じて risk_logs に記録します。
- KillSwitch は条件（例: drawdown 超過）を満たすと data/kill.flag を書き込みます。ExecutionEngine は起動時・実行中にこのフラグをチェックして安全に停止します。

ディレクトリ構成
----------------

（src/kabusys 以下の主要ファイル/ディレクトリを抜粋）

- src/kabusys/
  - __init__.py              — パッケージ定義（__version__ 等）
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 作成・更新の対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
    - position_sizing.py      — 発注株数計算（calc_position_sizes）
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — モメンタム・バリュー・ボラティリティ計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）で ai_scores を生成
    - regime_detector.py     — マクロ + MA で市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py       — 監視ログ用 SQLite ラッパー（テーブル初期化含む）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各モニタの束ね
    - ... （TradeMonitor / AlertManager 等、コードベースに応じて存在）
  - execution/
    - execution_engine.py    — 実行エンジン（EngineConfig 等）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - risk_manager.py
    - reconciler.py
    - ...（発注周り実装）
  - utils/
    - logging_setup.py       — ロギング初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
    - __init__.py

補足（運用上の注意）
-------------------
- .env は機密情報を含むため絶対にリポジトリにコミットしないでください。
- KABUSYS_ENV=live の設定は本番運用を意味します。validate_config によるチェックと LINE アラート設定などの確認を必ず行ってください。
- OpenAI を使う機能は API コストが発生します。利用頻度・バッチサイズ等を考慮して運用してください。
- run_execution / run_monitoring は stop/kill フラグで安全に停止できる設計ですが、データ損失を避けるため停止時のログを確認してください。
- 自動 .env 読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現行: 0.1.0）。

よくあるコマンド一覧（まとめ）
------------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- Execution 起動: python -m kabusys.run_execution
- Monitoring 起動: python -m kabusys.run_monitoring
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

質問や追加のドキュメント化希望があれば教えてください。必要であれば各モジュールごとの API サンプル（コード片）や設定 .env のサンプルを追記します。