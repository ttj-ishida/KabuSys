README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を目的とした小規模なフレームワークです。  
主に以下の役割を持つコンポーネントで構成されています。

- ExecutionEngine: 発注・注文管理・リスク管理（実運用 / ペーパートレード対応）
- Monitoring: システム状態・注文状態・リスクを定期監視し、Kill Switch による停止やアラート通知を行う
- Research / Portfolio: ファクター算出やポートフォリオ構築の純粋関数群
- AI モジュール: LLM を使ったニュースセンチメント評価・市場レジーム判定
- ユーティリティ: 設定読み込み、ログ設定、プロセス優先度設定 等

主要機能
--------
- 実運用 / ペーパートレード切替（KABUSYS_ENV）
- 発注・注文管理・リスク制御（RiskManager / Reconciler 等）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch（flag ファイルによる停止シグナル）
- DuckDB / SQLite を用いたデータ格納・算出処理（ファクター・特徴量・各種集計）
- OpenAI API を用いたニュースセンチメント（ai.news_nlp）とレジーム判定（ai.regime_detector）
- 簡易 CLI: .env ウィザード（config_setup）、設定検証（validate_config）、ペーパートレード検証レポート生成（paper_verification_report）

前提（推奨）
------------
- Python 3.9+（型ヒントに Union 演算子などを使用）
- 必要な外部ライブラリ（用途に応じて）:
  - duckdb（分析用）
  - psutil（プロセス・リソース監視）
  - openai（AI モジュールを使用する場合）
  - PyYAML（validate_config で YAML 検証を行う場合）

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone ... && cd <repo>

2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （用途によっては openai や PyYAML は不要）

4. .env の作成（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードに従って必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力してください。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict オプションを付けると警告も失敗扱いになります。

主要環境変数（抜粋）
-------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

重要なオプション（よく使うもの）:
- KABUSYS_ENV — 実行モード (development / paper_trading / live)
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db） ※Monitoring は常にこの sqlite を使います
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（paper_trading 用）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR）
- OPENAI_API_KEY — OpenAI を利用する場合に必要
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1。production は 0 推奨）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）※run_monitoring に適用

使い方（主要コマンド）
--------------------

1. 実行エンジン（ExecutionEngine）を起動
   - python -m kabusys.run_execution
   - 補足:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用い、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。
     - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
     - 実行中は data/execution.pid に PID ファイルを出力します。停止は stop flag の作成で行います。

2. 監視ループを起動
   - python -m kabusys.run_monitoring
   - 補足:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（デフォルト 60 秒）。
     - 監視は Settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依存しません）。
     - 停止は data/stop_requested.flag を作成することで行います（監視プロセスが検知して終了します）。

3. .env 設定ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH（PAPER_TRADING_SQLITE_PATH より優先）

運用に関する注意
----------------
- kill.flag / stop_requested.flag:
  - ExecutionEngine の停止には data/kill.flag（Kill Switch）または data/stop_requested.flag を用いる設計が混在しています。run_execution/run_monitoring のコードを参照して、利用するフラグファイルを確認してください。
  - Settings.kill_flag_clear_on_start=1 を本番で設定すると危険（自動クリアされアラートが無効化される可能性がある）ため、live 環境では 0 を推奨します。

- ログ:
  - ログは kabusys.utils.logging_setup.setup_logging を経由して stdout と logs/<app_name>.log へ出力します。LOG_DIR 環境変数で出力先を変更可能です。

- DB の分離:
  - ペーパートレード時は paper_sqlite_path へ記録するので本番監視データと分離されます。一方、Monitoring は常に sqlite_path（デフォルト data/monitoring.db）を使用します。

ディレクトリ構成
----------------
（src/kabusys 以下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック（自動 .env ロード機能含む）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト

  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py     — マクロ + ETF MA でレジーム判定

  - monitoring/
    - monitoring_db.py       — SQLite のテーブル定義と簡易 CRUD
    - system_monitor.py      — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py       — （注文関係の監視: ファイルに含まれるが本 README では詳細省略）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - monitoring_engine.py   — 各 Monitor を束ねるループ
    - alert_manager.py       — （アラート送信ロジック：LINE 等）※コード参照

  - execution/
    - execution_engine.py    — ExecutionEngine（セッション制御・発注ループ）
    - broker_factory.py      — Broker クライアント生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算（DuckDB 利用）
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
    - __init__.py

  - data/
    - pipeline.py            — データパイプライン補助（例: get_last_price_date）
    - stats.py               — zscore_normalize 等（research から参照）

  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート生成

  - utils/
    - logging_setup.py       — 統一的なログ設定ユーティリティ
    - process_priority.py    — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

サンプル .env（抜粋）
-------------------
# KabuSys 環境設定（例）
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxx
KILL_FLAG_CLEAR_ON_START=0
PAPER_FILL_MODE=instant

開発・拡張のヒント
------------------
- DuckDB 接続を渡して純粋関数的にファクターを計算する設計になっています。研究用途では DuckDB のテーブル（prices_daily / raw_financials 等）を準備すればローカルで計算できます。
- AI 関連は OpenAI SDK の呼び出しをラップしており、テスト時には _call_openai_api をモックすることでネットワーク依存を排除できます。
- monitor / engine のコンポーネントは小さく分割されているため、個別にユニットテストを書きやすくなっています。

ライセンス・作者
----------------
（ここにライセンスや作者情報を追記してください）

補足・参照
----------
- 実装の詳細は各モジュールの docstring / コメントに記載されています。運用前に config_setup → validate_config を実行して設定整合性を確認してください。