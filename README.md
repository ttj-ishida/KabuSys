README
=====

概要
----
KabuSys は日本株の自動売買 / 研究 / 監視を目的とした軽量なフレームワークです。  
このコードベースは主に以下の機能群を含みます。

- ExecutionEngine：発注・注文管理・リスク管理の実行エンジン（本番 / ペーパートレード切替対応）
- Monitoring：システム稼働・注文状況・リスク監視（Kill Switch / アラート連携想定）
- Portfolio 構築：候補選定・配分重み計算・ポジションサイズ算出・セクター制約
- Research：DuckDB を用いたファクター計算・特徴量探索（モメンタム / バリュー / ボラティリティ 等）
- AI 支援：ニュースの NLP スコアリング、マクロセンチメントを用いた市場レジーム判定（OpenAI 利用）
- ツール：ペーパートレード検証レポート生成や設定ウィザード / 設定検証 CLI 等
- ユーティリティ：ログ設定・プロセス優先度設定・DB 永続化レイヤ等

主な設計方針として、ルックアヘッドを防ぐ実装（date.today() を直接参照しない等）や本番とペーパーの DB 分離、フェイルセーフ（API 失敗時のフォールバック）を重視しています。

主な機能一覧
--------------
- run_execution.py
  - ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し paper_trading.db に記録。
  - 停止フラグ（data/stop_requested.flag）検知でエンジン停止。PID ファイル（data/execution.pid）出力。
- run_monitoring.py
  - SystemMonitor をポーリングして監視ログを記録（デフォルト 60 秒間隔、MONITOR_POLL_INTERVAL で上書き可）。
  - 監視は本番用 sqlite_path を参照（環境に依存せず一貫した監視 DB を使用）。
- monitoring モジュール
  - system_monitor, trade_monitor, risk_monitor, kill_switch, monitoring_engine, monitoring_db（SQLite 永続化）
- portfolio モジュール
  - 候補選定、等金額/スコア重み、ポジションサイズ算出、セクターキャップ、レジーム乗数
- research モジュール
  - DuckDB を用いたファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ
- ai モジュール
  - news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメントスコアを ai_scores に書込む
  - regime_detector: ETF(1321) の MA とマクロニュースを組み合わせて日次の市場レジーム判定
- tools
  - paper_verification_report: ペーパートレード DB から検証レポートを出力
- 設定関連
  - config_setup.py: .env 作成/更新の対話ウィザード
  - validate_config.py: .env と config/*.yaml の検証 CLI

セットアップ手順
----------------
1. Python 環境の準備（推奨: v3.10+）
   - 仮想環境を作成して有効化してください:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb psutil openai
   - PyYAML は config/*.yaml の内容検証で使われるため任意: pip install pyyaml
   - その他、実環境で発注用のブローカークライアントを使う場合は該当の依存を追加してください。

3. プロジェクトルートで .env を作成
   - インタラクティブに作る（推奨）:
     - python -m kabusys.config_setup
   - 手動で作る場合は .env.example を参考に .env を作成してください（.env は絶対に Git にコミットしないでください）。

4. 設定検証
   - python -m kabusys.validate_config
   - 警告も失敗にしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / ログ パスは data/ と logs/ です。自動で作成されますが、権限等に注意してください。

主な環境変数（抜粋）
-------------------
（重要なものだけを記載。config_setup ウィザードで設定できます。）
- KABUSYS_ENV: execution モード。development / paper_trading / live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp/regime_detector）に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）※KABUSYS_ENV=paper_trading 時に使用
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定モード (instant/partial/never/reject)
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

使い方（起動・CLI）
-------------------
- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱い

- ExecutionEngine 起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 終了時は data/execution.pid（デフォルト）を使用してプロセス管理します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に（env にかかわらず）本番用 sqlite_path を使用して監視ログを記録します。

- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

注意点 / 運用上のメモ
--------------------
- .env は機密情報を含むため決してリポジトリにコミットしないでください。
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を設定してください。API 呼び出しはリトライとフォールバックを備えていますが、コストに注意してください。
- 実運用（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨します（自動クリアは危険）。
- ログ: kabusys.utils.logging_setup により logs/<app_name>.log に日次ローテーションで出力されます（デフォルト logs/）。
- 停止フラグ: data/stop_requested.flag — このファイルが存在すると run_execution/run_monitoring のループは終了または起動停止します。
- Kill Switch: monitoring から条件に応じて data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。

ディレクトリ構成
----------------
主要ファイル・ディレクトリ（src/kabusys ルートを基準）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定読み込みロジック
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト

  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity 設定
    - __init__.py

  - monitoring/
    - monitoring_db.py        — SQLite スキーマ + 永続化 API
    - monitoring_engine.py    — 複数モニタの統合ループ
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文ログ・異常検出（コード参照）
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — （アラート送信ロジック、実装参照）

  - execution/
    - execution_engine.py     — 実際の ExecutionEngine（起動点は run_execution.py）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py

  - portfolio/
    - portfolio_builder.py    — 候補選定 / 重み計算
    - position_sizing.py      — 発注株数計算
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py      — momentum/value/volatility 等のファクター計算
    - feature_exploration.py  — 将来リターン・IC・統計サマリ
    - __init__.py

  - ai/
    - news_nlp.py             — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py      — 市場レジーム判定（MA + マクロ NLP）
    - __init__.py

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート出力
    - __init__.py

補足（開発者向け）
-----------------
- DuckDB 接続を受け渡してデータ処理を行う設計のため、価格・財務データは DuckDB 上のテーブル（prices_daily / raw_financials / raw_news 等）として用意することを想定しています。
- 多くの関数は「副作用を持たない純粋関数」あるいは DB 層と一貫した API（MonitoringDB 等）を使うことでテスト容易性を高めています。ユニットテストでは外部 API 呼び出し（OpenAI 等）はモックすることが容易です。
- 既知のデフォルトパス:
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - logs/<app_name>.log

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（現状 0.1.0）。
- ライセンス情報はリポジトリルートの LICENSE 等を参照してください（ここでは省略）。

以上がプロジェクトの概要・セットアップ・使い方のサマリです。README の内容について特に詳しく記載してほしい箇所（例: 起動手順の詳細、CI/CD、環境固有設定など）があれば教えてください。