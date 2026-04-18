KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ基盤の一部を実装した Python パッケージです。本リポジトリには以下の主要機能を持つモジュール群が含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプト
- システム / 発注 / リスク監視のポーリング（Monitoring）
- Portfolio 構築・ポジションサイジングロジック（純粋関数）
- ファクター計算・特徴量解析（Research）
- AI を利用したニュースセンチメント（OpenAI 連携モジュール）
- 設定ウィザード・検証ツール・検証レポート等のユーティリティ

主な設計方針:
- DuckDB（分析用）と SQLite（監視・発注ログ）を併用
- 本番 / ペーパートレードを環境変数で切り替え（KABUSYS_ENV）
- OpenAI 連携はフェイルセーフ設計（API失敗は無害にフォールバック）
- ログは統一的に設定（console + 日次ローテートファイル）

機能一覧
-------
- run_execution.py
  - ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBroker を使い data/paper_trading.db に分離して記録。
  - 停止フラグ（data/stop_requested.flag）により安全に停止可能。
- run_monitoring.py
  - SystemMonitor のポーリング・監視ループを起動。MONITOR_POLL_INTERVAL で間隔を調整可能（デフォルト 60 秒）。
  - 本モニタは本番 sqlite_path を常に使用（監視は本番 DB を参照）。
- 設定管理
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env / config/*.yaml の事前検証 CLI（--strict が利用可）
- monitoring サブパッケージ
  - MonitoringDB: 監視ログの永続化（SQLite テーブル初期化・マイグレーション含む）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch / AlertManager 等（監視・Kill Switch 実装）
- portfolio サブパッケージ
  - 候補選定、等配分・スコア加重配分、ポジション算出（単元株丸め、aggregate cap 等）
  - セクター集中制限やレジーム乗数の調整
- research サブパッケージ
  - ファクター（モメンタム・バリュー・ボラティリティ等）計算（DuckDB を利用）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- ai サブパッケージ
  - news_nlp: raw_news を OpenAI に投げて銘柄別センチメント ai_scores に書き込み
  - regime_detector: ETF (1321) の MA200 乖離 + マクロニュースで市場レジーム（bull/neutral/bear）判定
- tools
  - paper_verification_report.py: ペーパートレード DB から検証レポートを生成（稼働率・約定率・レイテンシ等）

セットアップ手順
----------------
前提: Python 3.8+ を想定（DuckDB / psutil / openai 等を使用）

1. リポジトリをクローン
   - git clone <repo>

2. 必要パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - ない場合は最低限以下をインストール:
     - pip install duckdb psutil openai
   - 開発 / 検証用に PyYAML があれば config/*.yaml の内容検証が有効になります:
     - pip install pyyaml

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - もしくは .env を手動作成（.env.example を参考に必要な環境変数を設定）

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL にしたい場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ準備（必要に応じて）
   - デフォルトでは data/ 以下に DB・PID・フラグを作成します。権限やマウント先を適切に設定してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH: 分析用 DuckDB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う機能で必須（ai.news_nlp / ai.regime_detector）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（停止 / Kill スイッチ関連）

使い方（起動・ツール）
--------------------

1. Execution（注文エンジン）を起動
   - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に記録（本番 DB と完全分離）
     - 起動時に data/stop_requested.flag が存在すると起動を中止
     - 実行中は PID ファイル（data/execution.pid 等）を生成

2. Monitoring を起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒で変更可能（例: export MONITOR_POLL_INTERVAL=30）

3. 停止 / Kill Switch
   - Monitoring の KillSwitch が条件を満たした場合、data/kill.flag を書き込み ExecutionEngine に停止シグナルを送ります。
   - 手動で Engine を止めたい場合は data/stop_requested.flag を作成すると既存ループは検知して安全終了します。
   - 起動時に Kill Flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では 0 を推奨）。

4. .env を対話式で作る
   - python -m kabusys.config_setup

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

6. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数で指定することも可）

7. AI 機能（ニュース NLP / レジーム判定）
   - OPENAI_API_KEY を設定し、ai.score_news / ai.regime_detector.score_regime 等を呼び出して使用します（コマンドラインラッパーは付属していませんが関数は公開されています）
   - OpenAI 呼び出しはリトライ・JSON バリデーション・スコアクリップ等のフェイルセーフ実装があります。

ログ
---
- ログは kabusys.utils.logging_setup.setup_logging を通じて統一的に設定されます。
- デフォルト: logs/<app_name>.log に日次ローテーションで保存（30 日分保持）
- コンソールは stdout に出力されます（cron 等での一括リダイレクトを想定）

ディレクトリ構成（主要ファイル）
----------------------------
以下は src/kabusys 配下の主要ファイル群（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / 設定取得ユーティリティ
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ロギング初期化ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py        — SQLite 監視 DB 初期化 + 永続化層
    - system_monitor.py
    - trade_monitor.py        — （発注関連の監視）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                — Execution 関連モジュール（Engine, BrokerFactory, OrderManager 等）
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

（注）上記は主要モジュールの抜粋です。細かい実装は各ファイルを参照してください。

実運用上の注意
--------------
- 本番（KABUSYS_ENV=live）での起動前には必ず python -m kabusys.validate_config を実行して設定を確認してください。
- .env は絶対に Git にコミットしないでください（config_setup.py のヘッダに注意書きあり）。
- OpenAI API を利用する機能はコストとレイテンシに注意してください。API失敗時の挙動はフェイルセーフとなっていますが、想定外の反応や料金発生に留意してください。
- 単体テストや CI のセットアップは本リポジトリに含まれていません。ユニットテストを追加する際は OpenAI・外部API 呼び出し箇所をモックしてください。

貢献・拡張のヒント
------------------
- portfolio の lot_size を銘柄別に拡張する場合、stocks マスタに単元情報を追加し、calc_position_sizes の API を拡張してください（TODO コメントあり）。
- research モジュールは DuckDB のテーブル構造（prices_daily / raw_financials 等）に依存しています。データロードパイプラインに合わせて調整してください。
- monitoring のアラート出力（AlertManager）を Slack / LINE 等に拡張可能です（LINE 用のトークンが既に設定項目に含まれています）。

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス情報はリポジトリルートの LICENSE を参照してください（存在する場合）。

お問い合わせ
------------
実装や使い方についての質問はリポジトリ内の該当モジュール（config_setup.py / validate_config.py / run_*）の docstring をまず参照してください。不明点があれば具体的な実行コマンド・環境変数・ログ出力を添えて質問してください。