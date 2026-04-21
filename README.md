README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤（プロトタイプ）です。  
主な役割は以下の通りです。

- 日次/オンデマンドでのファクター計算・リサーチ機能（DuckDBを使用）
- 発注実行エンジン（kabuステーション等のブローカークライアントを介して発注）
- 監視 (System / Trade / Risk) と Kill Switch による安全停止
- Paper Trading（ペーパートレード）用の分離された DB と検証ツール
- ニュース NLP（OpenAI）を用いた銘柄ごとのセンチメント算出
- 設定ウィザード・設定検証ツール、レポート生成ツール

本リポジトリはモジュール化されており、Execution、Monitoring、Research、AI、Portfolio 等の責務が分かれています。

主な機能一覧
-------------
- 実行エンジン起動スクリプト
  - src/kabusys/run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録
- 監視ループ起動スクリプト
  - src/kabusys/run_monitoring.py
  - SystemMonitor を定期的に実行し、system_status / trade_logs / risk_logs / dashboard を更新
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
- 設定管理
  - src/kabusys/config.py: .env の自動ロード・Settings API
  - src/kabusys/config_setup.py: 対話式 .env 作成ウィザード
  - src/kabusys/validate_config.py: 起動前の設定検証 CLI
- 監視サブシステム
  - MonitoringDB（SQLite）永続化層（src/kabusys/monitoring/monitoring_db.py）
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine / KillSwitch
- ポートフォリオ構築・サイズ算出
  - src/kabusys/portfolio/*: 候補選定・重み計算・リスク調整・株数算出（純粋関数群）
- 研究・ファクター計算
  - src/kabusys/research/*: momentum, volatility, value 等の因子計算、IC 計算など（DuckDB 使用）
- AI（OpenAI）連携
  - src/kabusys/ai/news_nlp.py: ニュース記事の銘柄別センチメントスコア算出・ai_scores への書込
  - src/kabusys/ai/regime_detector.py: マクロ + ETF MA200 を組み合わせた市場レジーム判定
- ユーティリティ
  - ロギング設定（TimedRotatingFileHandler）: src/kabusys/utils/logging_setup.py
  - プロセス優先度 / CPU affinity 設定: src/kabusys/utils/process_priority.py
- ツール
  - Paper Trading 検証レポート生成: src/kabusys/tools/paper_verification_report.py

セットアップ手順
----------------
前提
- Python 3.10 以上を想定（typing の | 演算子等を使用）
- SQLite は標準組み込み、その他は pip でインストール

推奨的なセットアップ手順
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必須パッケージのインストール（代表的な依存）
   - pip install duckdb psutil openai
   - 任意で PyYAML（config 検証時に YAML の内容検査を行う場合）:
     - pip install pyyaml

   （requirements.txt がある場合は pip install -r requirements.txt を利用）

3. 環境変数 / .env の準備
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに .env を作成。
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - OPENAI_API_KEY (AI 機能を使う場合)
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/…）
     - MONITOR_POLL_INTERVAL（監視ループの秒数、run_monitoring で使用）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 本番向けに厳格にチェックする場合:
     - python -m kabusys.validate_config --strict

5. データディレクトリ等
   - 多くのコードは data/ や logs/ を自動作成するようになっていますが、必要に応じて事前に作成してください。
   - ログはデフォルト logs/<app_name>.log に日次ローテーションで出力されます。

使い方（起動コマンド例）
----------------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告も失敗扱い

- Execution Engine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると paper_trading 用 DB に記録され、MockBrokerClient が利用されます
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで制御（監視側 / 運用手順に従う）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60）
  - run_monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 日付範囲を指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  - 環境変数 PAPER_TRADING_SQLITE_PATH を使ってデフォルトを上書き可能

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定した状態で、AI 用の関数を呼び出します（例: kabusys.ai.score_news / score_regime）。
  - これらは DuckDB 接続および target_date を引数に受け取り、内部で ai_scores / market_regime テーブルへ書き込みます。

運用上の注意
------------
- Kill Switch
  - risk_monitor などの判定により data/kill.flag が書き込まれると ExecutionEngine に停止シグナルを送ります。
  - 本番環境では KILL_FLAG_CLEAR_ON_START は 0 を推奨します（自動クリアは危険）。

- DB の分離
  - Paper Trading（KABUSYS_ENV=paper_trading）の場合、発注関連は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に分離されます。監視 DB は環境にかかわらず monitoring.db を使用します。

- 権限・優先度
  - 起動スクリプトは最初に set_process_priority("high") を呼びプロセス優先度の設定を試みます。OS によっては権限や対応がない場合スキップされます。

- ログ
  - ログディレクトリが作成できない場合はコンソール出力のみで継続します。ログレベルは環境変数 LOG_LEVEL で制御できます。

ディレクトリ構成
----------------
（src 以下を中心に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト

  - execution/
    - broker_factory.py
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py

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

  - data/                    — （実行時に使用される DB / ファイル等、例: data/monitoring.db 等）
  - logs/                    — ログ出力先（デフォルト）

  - tools/
    - paper_verification_report.py

  - utils/
    - logging_setup.py
    - process_priority.py

補足: 重要なファイル・パス（デフォルト）
-------------------------------------
- data/kabusys.duckdb            — DuckDB（分析用）
- data/monitoring.db             — 監視ログ SQLite
- data/paper_trading.db          — ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）
- data/execution.pid             — Execution 用 PID ファイル（Settings.pid_file_path）
- data/stop_requested.flag       — 起動中の監視/エンジンに停止を要求する際に使用するフラグファイル
- data/kill.flag                 — Kill Switch が書き込む停止フラグ

よくある質問 / トラブルシューティング
-------------------------------------
- .env が自動ロードされない
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていると自動ロードを無効化します。
  - プロジェクトルートが検出できない（.git や pyproject.toml が無い）場合は自動ロードをスキップします。

- YAML 検証をスキップする
  - validate_config は PyYAML が無い場合、YAML ファイルの内容検証をスキップします（警告が出ます）。

- OpenAI API 呼び出し失敗時
  - news_nlp / regime_detector はリトライとフォールバック（失敗時は 0.0 など）を実装しており、API が使えない場合は処理をスキップまたは安全側のデフォルトで継続します。

貢献・開発
----------
- 新しい機能を追加する場合は該当モジュールにユニットテストを追加し、設定ファイル（config/*.yaml）を必要に応じて更新してください。
- AI 系呼び出しは外部 API に依存するため、単体テストでは OpenAI 呼び出し部分をモックしてください（モジュール内に呼び出しラッパーがあり、そこをパッチする設計になっています）。

ライセンス
---------
- 本ドキュメントではライセンス情報がソースに含まれていません。実運用する場合は適切なライセンスを付与してください。

以上が本リポジトリの概要・セットアップ・運用方法のまとめです。必要であれば、README に含めるサンプル .env テンプレートや起動例のさらに詳しい手順（systemd / supervisor / cron 用のサービス定義）も作成します。希望があれば教えてください。