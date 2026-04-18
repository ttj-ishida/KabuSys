# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ツールキットです。  
このリポジトリには実行エンジン、監視コンポーネント、ポートフォリオ構築、リサーチ（ファクター計算）や AI ベースのニュース解析など、バックテスト・本番運用に必要な機能群が含まれます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（実行コマンド例）
- 環境変数 / 主要設定
- ディレクトリ構成（主要ファイルの説明）
- 運用メモ（Kill Switch / 停止フラグ 等）

---

プロジェクト概要
- 日本株の自動売買システム用ユーティリティ群と基盤ライブラリ。
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）を切り替えて動作。
- DuckDB / SQLite をデータ格納に使用。OpenAI を使ったニュース NLP やレジーム判定機能も備える。

---

機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番/ペーパートレードを切替
  - BrokerClientFactory 経由でブローカー接続（paper_trading では Mock）
  - 発注管理、リスク管理、照合（reconciler）を組み立てて実行
- Monitoring（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor をポーリングしログ・アラートを管理
  - kill.flag による自動停止（Kill Switch）評価
- 監視データベース層（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブルの初期化・操作
- Portfolio construction
  - 銘柄選定、重み計算、ポジションサイズ計算（等重/スコア重/リスクベース等）
  - セクター上限適用、レジーム乗数計算
- Research（research パッケージ）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を使用）
  - 将来リターン、IC（Information Coefficient）、統計サマリー等
- AI モジュール（ai）
  - news_nlp: OpenAI でニュースをスコアリングし ai_scores テーブルへ書き込み
  - regime_detector: ETF（1321）MA とマクロニュースの LLM スコアを合成して市場レジーム判定
- ツールスクリプト
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前設定チェック CLI
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成
- ユーティリティ
  - logging_setup: 統一ログ設定（stdout + 日次ローテート）
  - process_priority: プロセス優先度・CPU affinity 設定ユーティリティ

---

セットアップ手順（ローカル開発向け）
前提: Python 3.10+ を推奨（typing の union 演算子 | を使用）。

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS/Linux
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - 必須パッケージ例:
     - duckdb
     - psutil
     - openai
   - オプション:
     - PyYAML（validate_config の YAML 検証に使用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt は本リポジトリに含まれていないため、用途に応じて追加してください。

4. 初期設定（.env）の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を作成し、必須キーを設定する。

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

6. データディレクトリの準備
   - デフォルトでは data/ 配下に SQLite / PID / フラグ等を配置します。必要に応じ作成:
     - mkdir -p data logs

---

環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API パスワード

運用に影響する主な設定:
- KABUSYS_ENV: execution 動作モード（development / paper_trading / live）
  - paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- LOG_DIR: ログディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）に必須
- PAPER_FILL_MODE: ペーパートレードでの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（"1" でクリア）

補足:
- Settings クラスは .env 自動読み込みを行います（プロジェクトルートの .env / .env.local）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

使い方（代表的コマンド）

1) .env の生成（対話式）
- python -m kabusys.config_setup

2) 設定検証
- python -m kabusys.validate_config
- 厳密モード: python -m kabusys.validate_config --strict

3) ExecutionEngine の起動（本番 / ペーパー切替は KABUSYS_ENV）
- python -m kabusys.run_execution
  - 起動直後に data/stop_requested.flag が存在すると起動しません。
  - run_execution は background スレッドで engine.run_session を起動し、stop フラグを監視します。
  - PID は data/execution.pid に書き込まれます（設定により変更可能）。

4) Monitoring の起動
- python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（秒、デフォルト: 60）。
  - 監視は常に本番 sqlite_path を使用（KABUSYS_ENV に関係なく monitoring DB は本番 DB を参照）。
  - 停止は data/stop_requested.flag を作成すると監視ループが検知して終了します。

5) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで SQLite パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも可）。

6) AI 機能の呼び出し（ライブラリ API）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（api_key 引数 or OPENAI_API_KEY 環境変数）。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

停止・Kill Switch・フラグファイル
- 停止要求（外部からの停止）:
  - data/stop_requested.flag を作成すると、run_execution と run_monitoring の両方が検知して安全に停止します。
- Kill Switch:
  - リスク条件（ドローダウン超過、ポジション上限超過など）で KillSwitch が data/kill.flag を書き込みます。ExecutionEngine 側はこのファイルを検出して停止する設計です。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアしますが、本番では 0 を推奨します。

---

ログ
- ログは stdout（コンソール）とファイル（logs/<app_name>.log）に出力されます。
- ローテーション: 日次、30世代保持（設定は util/logging_setup.py）。

---

ディレクトリ構成（主要ファイル説明）
- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — Settings クラス（.env / 環境変数管理・検証）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書き込み
    - regime_detector.py — 市場レジーム判定（ETF MA + マクロニュース LLM）
  - monitoring/
    - monitoring_db.py — SQLite 操作用ユーティリティ（テーブル作成/マイグレーション含む）
    - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
    - trade_monitor.py — （注文・約定の監視）※実装ファイルあり
    - risk_monitor.py — ドローダウン/ポジション上限監視
    - kill_switch.py — Kill Switch ロジック（フラグ書込）
    - monitoring_engine.py — 各 Monitor をまとめるエンジン
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
      - Execution のコアロジック（起動・発注・リスク制御・照合等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数計算（単元丸め・リスク制限・aggregate cap）
    - risk_adjustment.py — セクター制限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - data/ （実行時に生成される想定）
    - monitoring.db（デフォルト SQLITE_PATH）
    - paper_trading.db（ペーパートレード用）
    - kill.flag, stop_requested.flag, execution.pid など
  - logs/ （ログ出力先、デフォルト）

---

運用上の注意 / ベストプラクティス
- 本番運用前に必ず python -m kabusys.validate_config で設定を検証する。
- KABUSYS_ENV=live のときは LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を設定し、KILL_FLAG_CLEAR_ON_START は 0 にすることを推奨。
- ペーパートレードは本番 DB と分離（paper_sqlite_path を使用）されるので安全に検証できます。PAPER_FILL_MODE を適切に設定してください。
- OpenAI を使う機能は API 利用料が発生します。API キーと利用量に注意してください。AI 呼び出しに失敗した場合、多くの箇所でフォールバックやスキップ処理が入っていますが、ログを確認しておくこと。
- ログディレクトリや data/ 配下のディレクトリは適切な権限で作成してください。logging_setup はディレクトリ作成失敗時にファイル出力を無効化して stdout のみで継続します。

---

サポート / 拡張ポイント（開発者向け）
- BrokerClientFactory を拡張して別ブローカー接続を追加可能
- position_sizing: 銘柄別 lot_size を導入したり、手数料モデルを反映する拡張が想定される
- research モジュールは DuckDB 内の prices_daily / raw_financials テーブルに依存。データパイプラインを整備して投入すること
- news_nlp / regime_detector のテストは OpenAI 呼び出しをモック化すること（コード内コメント参照）

---

以上。README の内容で不明点や追加で載せたいコマンド・サンプル（例: systemd サービス定義、Dockerfile、requirements.txt など）があれば教えてください。必要に応じて追記します。