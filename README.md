README
======

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ／実行フレームワークです。  
主な目的は以下です。

- ストラテジーの研究（ファクター計算・特徴量探索）
- ポートフォリオ構築とポジションサイズ決定ロジック
- 実際の発注を担う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働性や注文状況を監視する Monitoring コンポーネント
- ニュースを LLM でスコアリングして運用に使う AI モジュール
- ペーパートレード検証や補助ツール類

プロジェクトはモジュール化されており、研究（research）環境と実稼働（execution / monitoring）を分離して扱えます。

主な機能
--------
- Execution（発注）:
  - ExecutionEngine によるセッション実行
  - BrokerClientFactory による本番／モック（paper_trading）ブローカー切替
  - OrderManager / OrderRepository / Reconciler / RiskManager による注文管理・再整合・リスク制御

- Monitoring（監視）:
  - SystemMonitor：CPU / メモリ / ディスク / データ鮮度 / Execution プロセス生存診断
  - TradeMonitor：滞留注文（stale orders）や約定価格異常の検出
  - RiskMonitor：ドローダウン、ポジション上限の監視とダッシュボード永続化
  - KillSwitch：重大リスク発生時に stop flag を書き込んで Execution を停止
  - MonitoringEngine：上記を束ねた定期ポーリング（アラート送出フック有り）
  - MonitoringDB：SQLite ベースの監視ログ永続化層（スキーマ作成・マイグレーション有り）

- Research / Data:
  - factor_research：モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - feature_exploration：将来リターン計算、IC（Spearman）等の統計解析
  - DuckDB を用いた分析処理（prices_daily, raw_financials 等を前提）

- Portfolio:
  - 銘柄選定（select_candidates）
  - 重み計算（等重・スコア重み）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイズ計算（単元丸め・aggregate cap・コストバッファ対応）

- AI（OpenAI）:
  - news_nlp: ニュース記事を銘柄ごとに集約し LLM（gpt-4o-mini）でセンチメントをスコア化、ai_scores に書き込み
  - regime_detector: ETF（1321）MA200 とマクロニュースセンチメントから日次レジーム（bull/neutral/bear）判定
  - 再試行・バックオフ、レスポンス検証などフェイルセーフ実装あり

- ツール:
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: .env と config/*.yaml の基本チェック CLI
  - paper_verification_report: ペーパートレード DB から検証レポート生成

前提 / 必要ライブラリ
--------------------
推奨: Python 3.10 以上（| 型注釈などを使用）

主要依存（代表例）:
- duckdb
- psutil
- openai
- PyYAML（config 検査時に使用。無くても動くが警告）
- sqlite3 は標準ライブラリ

（requirements.txt は本リポジトリに含まれている想定のため、環境に合わせて pip install を行ってください。）

セットアップ手順
----------------
1. リポジトリをクローン / 配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - 追加の開発用パッケージやバージョン固定はプロジェクトの requirements.txt を参照
4. データディレクトリを作成
   - mkdir -p data
5. 環境変数の準備 (.env)
   - python -m kabusys.config_setup
   - あるいは .env.example を参考に .env を作成
   重要な環境変数例:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH（必要に応じて）
     - LOG_LEVEL（DEBUG/INFO/...）
     - PAPER_FILL_MODE（paper_trading モードの fill 動作: instant|partial|never|reject）
6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります
7. DB 初期化
   - Monitoring コンポーネントは起動時に SQLite スキーマを自動作成します（init_monitoring_db）

使い方（主要コマンド）
--------------------
- ExecutionEngine 起動（本番 or ペーパートレード）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い、paper_trading 用 DB（data/paper_trading.db 等）へ記録します
  - 起動時に data/execution.pid が作成され、data/stop_requested.flag 等で停止制御できます

- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）

- 対話式 .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict で警告を失敗扱いにする

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

環境変数 / ファイルについて（主要）
-----------------------------------
- KABUSYS_ENV: execution の動作モード（development / paper_trading / live）
- OPENAI_API_KEY: AI モジュール（news_nlp, regime_detector）で使用
- SQLITE_PATH: 監視ログ（monitoring.db）のパス（デフォルト data/monitoring.db）
- DUCKDB_PATH: 分析用 DuckDB のパス（デフォルト data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード時に使用）
- PID / flag:
  - data/execution.pid: ExecutionEngine の PID 保持
  - data/stop_requested.flag: スクリプト側で外部停止を要求するフラグ（run_execution/run_monitoring が検出）
  - data/kill.flag: KillSwitch が書き込む停止フラグ（ExecutionEngine 側で検出して停止）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

注意事項 / 運用のヒント
---------------------
- OpenAI を使う機能は API キーと料金が必要です。通信失敗時はフェイルセーフでスコア 0 やスキップにフォールバックする実装がありますが、運用上の挙動を理解しておいてください。
- paper_trading は本番 DB と明確に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照して監視データを記録します（運用上の意図的な設計）。
- 単体モジュール（research, portfolio 等）は外部 DB に依存しない純粋関数として設計されている箇所が多く、ユニットテストが容易です。
- process priority / cpu affinity は utils/process_priority.py を通じて OS に依存せず呼び出せます。権限不足で設定に失敗した場合は警告でスキップされます。
- MONITOR 側は stop_requested.flag を使って安全に停止できます。Execution 側は kill.flag を KillSwitch で監視して停止します。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はリポジトリの主要なファイル／モジュール構成（src/kabusys 配下）です。実際のファイルはこのほかにも含まれます。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（.env 自動ロード）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト

  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - order_record.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py        — SQLite スキーマ / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py

  - data/
    - pipeline.py             — DuckDB を使ったデータ取得ユーティリティ（prices_daily など）
    - stats.py                — 正規化ユーティリティ等

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

  - utils/
    - process_priority.py

ライセンス / 貢献
-----------------
- 本 README ではライセンス情報は省略しています。プロジェクトの LICENSE ファイルを参照してください。
- 貢献する場合はまず issue を立て、仕様や API に関する合意のもとでプルリクエストを送ってください。

付録: よく使うコマンド例
-----------------------
- .env を作る（対話式）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Execution 起動（デフォルト）
  - python -m kabusys.run_execution
- Monitoring 起動（60秒間隔）
  - python -m kabusys.run_monitoring
- Paper Trading レポート（2026-04-01〜2026-04-11）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

お問い合わせ / ドキュメント参照
-----------------------------
- 各モジュール内に詳細な docstring と実装ノートが記載されています。特に portfolio / research / ai モジュールはアルゴリズムに関する注釈が豊富なため、実装や拡張時に参照してください。