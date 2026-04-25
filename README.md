README
=====

概要
----
KabuSys は日本株向けの自動売買システムおよびそれを支えるユーティリティ群です。本リポジトリは以下の主要機能を含みます。

- 実行エンジン (ExecutionEngine): 発注・オーダー管理・リスク管理を行うコア
- 監視コンポーネント (Monitoring): システム状態・注文状況・リスクを定期チェックし、Kill Switch を発動可能
- 研究・リサーチ (Research): ファクター計算・特徴量探索・将来リターン計算
- ポートフォリオ構築 (Portfolio): 候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム調整
- AI 支援モジュール (AI): ニュースの NLP スコアリング、マクロからのレジーム判定（OpenAI API を利用）
- ツール: Paper Trading の検証レポート生成、.env 設定ウィザード、設定検証 CLI 等
- 汎用ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込みなど

本 README はコードベース（src/kabusys/...）の利用者向けに、セットアップと基本的な使い方を日本語でまとめたものです。

主な機能一覧
------------
- Execution
  - ExecutionEngine 起動スクリプト (run_execution.py)
  - 実際のブローカークライアントは環境変数 KABUSYS_ENV により paper_trading（Mock）/live を切替
  - Paper trading 用 DB を分離して記録（data/paper_trading.db デフォルト）
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせる監視エンジン
  - ポーリングループ（run_monitoring.py）。MONITOR_POLL_INTERVAL で間隔変更可（デフォルト 60s）
  - KillSwitch による flag ファイル書き込みで ExecutionEngine を安全停止可能
  - 監視用 DB は monitoring.db（設定により path 指定）
- Research
  - momentum / volatility / value 等のファクター計算（DuckDB を利用）
  - forward returns、IC（スピアマンランク相関）やファクター統計
- Portfolio construction
  - 候補選定（スコア順）、等金額/スコア重み付け、リスクベースの数量決定
  - セクター上限適用、レジーム乗数（bull/neutral/bear）計算
- AI（OpenAI）
  - ニュースをまとめて LLM に投げ、銘柄ごとのセンチメント（ai_score）を生成して ai_scores テーブルへ書き込み
  - マクロニュースと ETF MA 乖離を組合せた市場レジーム判定
- ツール
  - 対話式 .env 生成ウィザード (config_setup.py)
  - 設定検証 CLI (validate_config.py)
  - Paper Trading 検証レポート生成 (tools.paper_verification_report)

必須前提（概略）
----------------
- Python 3.10 以上（PEP 604 の | 型などを使用）
- SQLite（標準ライブラリ）
- DuckDB
- psutil
- OpenAI Python SDK（AI 機能を使う場合）
- PyYAML（config/*.yaml の構文検証を行う場合に任意で使用）

セットアップ手順
----------------

1. Python 環境作成（例）
   - 推奨: venv を使う
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - 追加（任意）
     - pip install PyYAML

   （プロジェクトに requirements.txt がない場合は上記を参照してください）

3. リポジトリルートに移動し、データ・ログ用ディレクトリを作成
   - mkdir -p data logs

4. .env の準備
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成し、以下の必須環境変数を設定
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development | paper_trading | live、デフォルト: development）

   自動ロード: config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）から .env を自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いで exit 1 になります
     - python -m kabusys.validate_config --strict

6. DB の初期化
   - 各起動スクリプトは必要に応じて DB スキーマ（監視テーブルなど）を自動作成します（init_monitoring_db）。通常は追加の手動初期化は不要です。

環境変数（主要）
----------------
- KABUSYS_ENV: 実行環境
  - development / paper_trading / live
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（0/1）

使い方 (例)
------------

- ExecutionEngine（取引エンジン）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、Paper DB（PAPER_TRADING_SQLITE_PATH）に記録されます
  - 起動時、data/execution.pid に PID が書き込まれます
  - 停止: プロセスを Ctrl-C または外部から data/stop_requested.flag を作成すると安全停止します
  - Kill Switch（監視からの強制停止）により data/kill.flag が作成されると、次回の起動で検出・停止や通知が可能です

- Monitoring（監視ループ）を起動
  - python -m kabusys.run_monitoring
  - デフォルト 60 秒間隔で SystemMonitor.check_once() を呼び出し、監視ログ（monitoring.db）へ永続化します
  - MONITOR_POLL_INTERVAL 環境変数で秒数を変更できます（1 以上のみ有効）
  - 監視は KABUSYS_ENV に関係なく production 用 sqlite_path を使用してログを書きます
  - 停止: data/stop_requested.flag を作成するとループが終了します

- .env を対話的に作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付与すると警告がある場合でも exit 1

- Paper Trading 検証レポートを生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB パスを指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を使います

- AI 機能（ニューススコア・レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY）
  - ニューススコア:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
      - conn は DuckDB 接続。内部で raw_news / news_symbols / ai_scores テーブルを利用
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

停止・強制停止フロー
--------------------
- ソフト停止（管理者が停止したいとき）
  - data/stop_requested.flag を作成すると run_execution と run_monitoring が検出して安全シャットダウンします
- Kill Switch（監視による強制停止）
  - RiskMonitor 等の結果に応じて KillSwitch が data/kill.flag に理由を書き込みます
  - ExecutionEngine は起動時や運転中にこのフラグを検出すると安全停止します
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では 0 推奨）

ログ
----
- ログは logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/、30 日保持）
- コンソール出力は stdout に書かれます
- setup_logging() ユーティリティで統一的に設定されます

ディレクトリ構成（抜粋）
-----------------------
以下は src/kabusys 以下の主なファイル/パッケージ構成の概要です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数/.env のロードと Settings クラス
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - logging_setup.py       # ログ初期化ユーティリティ
    - process_priority.py    # プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       # （ファイルは本 README の対象コードに部分的あり）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       # （アラート送信ロジック）
  - execution/
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
  - ai/
    - news_nlp.py
    - regime_detector.py

（上記はリポジトリ内の主なファイルを抜粋したものです）

開発メモ / 注意事項
-------------------
- .env はセキュアな情報を含むため Git にコミットしないでください（config_setup.py のヘッダにも注意書きがあります）。
- KABUSYS_ENV を live に設定する場合は非常に慎重に。validate_config の追加チェックや LINE 通知設定等を事前に確認してください。
- AI（OpenAI）へは機密テキストを送信する点に注意してください。API 使用料が発生します。
- DuckDB / SQLite のパスは環境変数で柔軟に切替え可能。Paper Trading を本番 DB と分離することを推奨します。
- process_priority.set_process_priority() は OS による制約で失敗することがあります（権限不足など）。その場合は警告ログのみ出力して継続します。

ライセンス・バージョン
---------------------
- パッケージバージョンは src/kabusys/__version__ = "0.1.0"
- ライセンス表記等はリポジトリのルートにある LICENSE 等を参照してください（本コード抜粋には含まれていません）。

補足 / サポート
----------------
この README はコード断片からの要約です。詳細な API 使用方法や各コンポーネントの内部仕様は該当するソースファイルの docstring・コメントを参照してください。必要なら起動スクリプトや各モジュールの使い方を個別にドキュメント化できます。ご希望があれば教えてください。