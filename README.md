README
======

概要
----
KabuSys は日本株向けの自動売買 / 研究プラットフォームのコアライブラリ群です。本リポジトリは以下の主要機能を含みます。

- 注文実行 Engine（本番 / ペーパートレード対応）
- 監視コンポーネント（プロセス稼働・データ鮮度・注文異常・リスク監視）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイジング）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP を用いたセンチメントスコアリング（OpenAI）
- 各種ユーティリティ / CLI（設定ウィザード・設定検証・検証レポート）

主な特徴
--------
- 環境分離: KABUSYS_ENV によって development / paper_trading / live を切替可能。ペーパートレードは本番 DB と分離して data/paper_trading.db に記録されます。
- フェイルセーフ: 監視側で Kill Switch（data/kill.flag）を使って ExecutionEngine を停止できます。監視側は stop フラグ（data/stop_requested.flag）で停止できます。
- DuckDB / SQLite を利用したデータ格納（DuckDB は分析、SQLite は監視 / 発注ログ用）。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai モジュール）、市場レジーム判定。
- 設定ウィザード（.env 作成支援）と設定検証 CLI を提供。

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の | 演算子を使用）
- Git リポジトリルートに配置されていること（.env 自動ロードでプロジェクトルートを探索します）

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存ライブラリをインストール
   - 必須ライブラリの例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証で任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （実際の requirements.txt はリポジトリに含めていないため、必要に応じてプロジェクトで管理してください）

3. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 手動で .env を作成する場合は .env.example を参考に必要な環境変数を設定してください。
   - 自動ロード:
     - デフォルトでプロジェクトルートの .env と .env.local を読み込みます。
     - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗として扱います。

主要環境変数（抜粋）
--------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — news_nlp / regime_detector などで使用
- LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag をクリア（1 = クリアする。production では 0 推奨）
- PAPER_FILL_MODE — ペーパートレード時の約定振る舞い（instant|partial|never|reject）

使い方
------

主要 CLI / 実行エントリ

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ExecutionEngine（注文実行プロセス）起動
  - 通常（デフォルト環境を使用）:
    - python -m kabusys.run_execution
  - ペーパートレードで起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - ペーパートレードでは MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH で指定された DB（デフォルト data/paper_trading.db）に分離記録されます。
  - 停止方法:
    - 実行中に data/stop_requested.flag を設置するとプロセスは安全に停止します（run_execution は起動中に定期的にフラグをチェックして engine.stop() を呼びます）。

- Monitoring（監視）プロセス起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60）。
  - 監視は Settings.sqlite_path を本番の監視 DB として常に使用します（環境に依らず）。
  - 停止方法:
    - data/stop_requested.flag を作成すると run_monitoring のループが終了します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH で DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

- AI / リサーチ関数（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores テーブルを参照して OpenAI へ送信しスコアを保存します。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込みます。
  - 注意:
    - OpenAI 呼び出しには OPENAI_API_KEY が必要（引数で渡すことも可能）。
    - 失敗時はフォールバックやスキップを行いフェイルセーフになっています。

運用上のポイント
----------------
- Kill Switch:
  - KillSwitch（kabusys.monitoring.kill_switch）はリスク条件（ドローダウン／ポジション数等）に基づいて data/kill.flag を書きます。ExecutionEngine は kill.flag を見て停止する設計です（run_execution の設定に依存）。
  - 本番環境で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアしますが、これは危険なので本番では 0 を推奨します。
- プロセス優先度:
  - run_execution / run_monitoring は起動時にプロセス優先度を "high" に設定しようとします（psutil を使用）。権限不足の場合は警告を出してスキップします。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は幾つかのスキーマ変更（カラム追加）を冪等で行います。既存 DB を開く際に必要なマイグレーションを適用します。
- データ鮮度:
  - SystemMonitor は DuckDB の prices_daily から最終価格日の差分でデータ鮮度を判定します（デフォルト許容: 3 日以内）。

ディレクトリ構成
----------------
以下は主要なファイル / ディレクトリ（src/kabusys以下）です。実際のリポジトリには他のファイルも含まれます。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / .env 自動読み込みロジック
  - config_setup.py            — 対話式 .env ウィザード
  - validate_config.py         — 設定検証 CLI
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py              — ニュース NLP（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB 層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         — アラート送信を担う（ファイルはここにある想定）
  - execution/                  — ExecutionEngine / Order 関連（複数ファイル）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - data/ (リポジトリ外に作成されることが多い)
    - monitoring.db (デフォルト: data/monitoring.db)
    - kabusys.duckdb (デフォルト: data/kabusys.duckdb)
    - paper_trading.db (ペーパートレード用デフォルト: data/paper_trading.db)
    - kill.flag / stop_requested.flag / execution.pid

補足・開発向けメモ
------------------
- テスト時の .env 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI関連は外部 API 呼び出しを伴うため、テストでは _call_openai_api をモックする設計になっています（news_nlp / regime_detector 参照）。
- DuckDB の SQL クエリはリサーチ用途に最適化されています。prices_daily / raw_financials 等のテーブルスキーマに依存するのでデータの投入と整合性に注意してください。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を載せていません。実際のプロジェクトでは LICENSE を参照してください。
- バグ報告・改善提案は Issue / Pull Request を通じて行ってください。

---

必要に応じて、README に実際の requirements.txt の内容や LICENSE、開発者向けのセットアップ（Docker / systemd サービス定義など）を追記できます。追加で欲しい情報があれば教えてください。