KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。  
本リポジトリには以下の主要機能群が含まれます。

- 実行エンジン（ExecutionEngine）: 注文発行、リスク管理、約定管理
- 監視（Monitoring）: システム状態・注文・リスクの定期チェック、Kill Switch
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ算出、セクター制限
- リサーチ: ファクター計算（モメンタム・バリュー・ボラティリティ等）、特徴量解析
- AI ユーティリティ: ニュースのセンチメント解析、レジーム判定（OpenAI）
- ユーティリティ: 設定ウィザード、設定検証、ログ設定、プロセス優先度制御
- 運用ツール: ペーパートレード検証レポート生成、その他スクリプト

設計上の注目点
- Paper Trading と Live（本番）が明確に分離される設計（専用 DB、MockBrokerClient）。
- DuckDB をリサーチ用に使用、SQLite を監視・注文ログに使用。
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム検知をサポート（API キー必須）。
- .env ベースの設定管理と対話型設定ウィザード、起動前の設定検証ツールあり。

主な機能一覧
----------------
- 実行
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により Paper/Live 切替）
  - 注文管理・リスク管理・Reconciler を組み立ててスレッドで実行
- 監視
  - run_monitoring.py: SystemMonitor を周期的に実行（MONITOR_POLL_INTERVAL で調整）
  - monitoring_engine モジュール: System / Trade / Risk 監視を束ねる実行ループ
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止
- ポートフォリオ
  - 候補選定、等比率／スコア比率重み、リスクベースのポジションサイズ計算
  - セクターキャップとレジーム乗数
- リサーチ
  - calc_momentum, calc_volatility, calc_value: DuckDB 上でファクターを計算
  - feature_exploration: 前方リターン計算、IC 計算、統計サマリ
- AI
  - news_nlp: ニュース記事を集約して LLM に投げ、銘柄ごとのスコアを ai_scores に書き込み
  - regime_detector: ETF（1321）の MA200 とマクロニュースの LLM スコアを合成して market_regime を判定
- ツール
  - config_setup.py: .env を対話式で作成/更新
  - validate_config.py: .env と config/*.yaml の整合検査
  - tools/paper_verification_report.py: ペーパートレード DB を解析して検証レポートを印字

セットアップ手順
----------------
前提
- Python 3.10 以上を推奨
- 必要パッケージ（例）: duckdb, psutil, openai, PyYAML（config 検証用）など
  - 実際はプロジェクトの requirements.txt を参照してください（本コードスニペットには同梱されていません）。

1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows では .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install duckdb psutil openai
   - （PyYAML を使う場合）pip install pyyaml

3. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - 生成された .env は絶対に Git にコミットしないこと。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. データディレクトリの作成（必要なら）
   - デフォルト DB / PID / フラグファイル等は data/ 以下を使用します。起動時に自動作成される場合もありますが、手動で用意しておくと安全です。

重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: execution モード ("development" | "paper_trading" | "live")（デフォルト: development）
  - paper_trading の場合、実行エンジンは MockBrokerClient を使用し専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 本番での自動クリアは危険（本番では 0 推奨）

使い方（起動・運用）
------------------

1) .env 作成・検証
- python -m kabusys.config_setup
- python -m kabusys.validate_config

2) 監視（Monitoring）を起動
- デフォルト（60秒間隔）:
  - python -m kabusys.run_monitoring
- 間隔を変更する場合:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- run_monitoring は監視用 SQLite（Settings.sqlite_path）に接続し、SystemMonitor をポーリングします。停止は data/stop_requested.flag を作成するか Ctrl+C。

3) 実行エンジン（Execution）を起動
- 本番／ペーパートレードは KABUSYS_ENV に依存:
  - export KABUSYS_ENV=paper_trading
  - python -m kabusys.run_execution
- 実行中に停止したい場合:
  - data/stop_requested.flag を作成するとエンジンが停止します。
- 実行エンジンは pid ファイル (data/execution.pid) を使います。KillSwitch により data/kill.flag が作成されると安全停止指示となります。

4) Paper Trading 検証レポート
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db で PAPER_TRADING_SQLITE_PATH をオーバーライド可能

5) AI 関連
- news_nlp.score_news / regime_detector.score_regime を呼ぶと OpenAI を使ってスコアを計算し DuckDB に保存します。API キーは OPENAI_API_KEY を指定してください。
- API 呼び出しはリトライやフォールバック（失敗時はスコア 0 等）を備えています。

ログ
----
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- 起動時に setup_logging(app_name="execution" or "monitoring") が呼ばれます。
- LOG_DIR 環境変数で出力先を変更できます。ファイル出力ができない場合はコンソール出力のみになります。

停止・Kill スイッチ
------------------
- stop_requested.flag:
  - run_monitoring / run_execution が監視している外部停止フラグ（data/stop_requested.flag）。このファイルを置くとループを抜けます。
- kill.flag:
  - KillSwitch（監視ロジック）が条件を満たした場合に data/kill.flag を作成します。ExecutionEngine 側では kill.flag の存在を検査して安全停止／運用上の判断を行えます。
- KILL_FLAG_CLEAR_ON_START 環境変数を 1 に設定すると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下を想定）

- kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — Settings クラス (.env 自動ロード、設定アクセス)
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 起動前設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py              — ニュース NLP（OpenAI） → ai_scores 書込
    - regime_detector.py       — マクロ + MA200 合成によるレジーム判定
  - monitoring/
    - monitoring_db.py         — SQLite スキーマ初期化・永続化ロジック
    - system_monitor.py        — システム / データ鮮度監視
    - trade_monitor.py         — （注文の滞留や約定異常を検出するモジュール）
    - risk_monitor.py          — ドローダウン / ポジション上限監視
    - kill_switch.py           — Kill Switch ロジック
    - monitoring_engine.py     — 監視各コンポーネントの統合
    - alert_manager.py         — （通知送信管理：LINE など）
  - execution/
    - execution_engine.py      — ExecutionEngine 本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み付け
    - position_sizing.py       — 株数決定・制限・単元丸め
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py      — ファクター計算（momentum/value/volatility）
    - feature_exploration.py  — 将来リターン・IC・統計
  - utils/
    - logging_setup.py        — 共通ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - data/ (runtime: DB ファイル / pid / flag 等を格納するデフォルト先)

補足・運用上の注意
-----------------
- 本番（KABUSYS_ENV=live）での起動は慎重に行ってください。validate_config の警告をよく確認してください。
- .env をリポジトリにコミットしないこと（トークンやパスワードが含まれるため）。
- OpenAI を使った処理は API 費用が発生します。運用時は呼び出し頻度・コストに注意してください。
- DuckDB / SQLite のパスを共有ファイルにしないでください（複数プロセスでの同時書き込みは想定外の問題を起こす場合があります）。
- process_priority や CPU affinity の設定は OS 権限により失敗する場合があり、その場合は警告ログが出ますが処理自体は継続します。

バージョン
---------
パッケージのバージョンは kabusys.__version__ で管理されています（例: "0.1.0"）。

ライセンス / 貢献
-----------------
（ここにプロジェクトのライセンス・貢献ガイドラインを追記してください）

--- 
この README はコードベースの主要機能と運用方法をまとめたものです。追加の詳細（API の細かい挙動、各コンポーネントの内部仕様）は該当モジュールのドキュメント／ソースコードの docstring を参照してください。