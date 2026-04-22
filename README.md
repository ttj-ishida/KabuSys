KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買・研究・監視ツール群です。本リポジトリは以下の責務を持つモジュール群で構成されています。

- ExecutionEngine（発注エンジン）: 本番 / ペーパートレードでの発注処理
- Monitoring（監視）: システム状態・注文状況・リスク監視、Kill Switch 発動
- Portfolio（ポートフォリオ構築）: 銘柄選定、重み付け、株数計算
- Research（調査）: ファクター計算・特徴量探索
- AI（ニュース NLP / レジーム判定）: OpenAI を用いたニュースセンチメント評価・レジーム推定
- ユーティリティ: ログ設定、プロセス優先度設定、設定ウィザード・検証など
- Tools: Paper Trading の検証レポート生成スクリプト 等

主な特徴
--------
- 明確に分離された本番 / ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）
- DuckDB を使った価格・財務・ニュース等の分析クエリ（research / ai モジュール）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント・レジーム判定（API キー必須）
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch の実装
- .env による柔軟な設定（config_setup.py による対話的生成、validate_config.py による事前検証）
- 日次ローテートのログ出力とコンソール出力の統一（utils.logging_setup）

セットアップ手順
---------------
1. リポジトリをクローン
   - git clone <リポジトリ URL>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 必須（最低限）:
     - duckdb
     - psutil
     - openai
   - 推奨 / 補助:
     - PyYAML（config/*.yaml の内容検証を行う場合）
   - 例:
     - pip install duckdb psutil openai pyyaml

   注意: sqlite3 は通常の Python に同梱されています。OS 依存の追加セットアップは不要です。

4. .env の用意（対話ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは .env をプロジェクトルートに生成・更新します。
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - --strict を付けると警告もエラー扱いになります。

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）。デフォルト: development
- OPENAI_API_KEY: OpenAI を使う機能（ai.news_nlp, ai.regime_detector）で必須
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring.db）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL / LOG_DIR: ログ関連設定
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

使い方
------
※ すべてのコマンドはプロジェクトルート（.env がある場所）で実行してください。

主なエントリポイント（モジュール実行形式）
- 環境設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - 厳密チェック: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、data/paper_trading.db に記録します。
  - ExecutionEngine は data/stop_requested.flag や data/execution.pid を参照／作成します。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - Monitoring は本番 sqlite_path（Settings.sqlite_path）を使用して監視データを永続化します。
  - 停止は data/stop_requested.flag を作成するか KeyboardInterrupt（Ctrl+C）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH （優先順: --db > PAPER_TRADING_SQLITE_PATH > data/paper_trading.db）

- AI / 研究機能
  - AI 機能（ニューススコアリング / レジーム判定）はモジュール関数として提供されています。
    - 例（Python REPL またはスクリプト内）:
      from kabusys.ai.news_nlp import score_news
      from kabusys.ai.regime_detector import score_regime
    - これらは DuckDB 接続と target_date、APIキー（環境変数 OPENAI_API_KEY または引数）を受け取ります。

ログと監視
- logging_setup.setup_logging を各起動スクリプトが呼び出し、stdout と日次ローテートログ（logs/<app>.log）に出力します。
- monitoring により system_status, trade_logs, risk_logs, positions, dashboard を SQLite に記録します。

ディレクトリ構成
----------------
以下は主なファイルとディレクトリ（抜粋）です。実際のリポジトリにはさらに多くの実装ファイルが含まれます。

- src/
  - kabusys/
    - __init__.py
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring 起動スクリプト
    - config.py                — Settings（環境変数 / .env 自動読み込み）
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 起動前チェック CLI
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成
    - utils/
      - __init__.py
      - logging_setup.py       — ログ設定ユーティリティ
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - monitoring/
      - monitoring_db.py       — monitoring DB レイヤ
      - monitoring_engine.py   — 複数モニタの統合ループ
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （省略: 注文・約定監視）
      - risk_monitor.py        — ドローダウン・ポジション上限監視
      - kill_switch.py         — kill.flag の作成 / 評価
      - alert_manager.py       — （省略: 通知管理）
    - execution/
      - execution_engine.py    — ExecutionEngine 本体（省略ファイル多数）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - risk_manager.py
      - reconciler.py
      - ...
    - portfolio/
      - __init__.py
      - portfolio_builder.py   — 銘柄選定・スコアソート
      - position_sizing.py     — 株数決定・投下資金スケーリング
      - risk_adjustment.py     — セクターキャップ・レジーム乗数
    - research/
      - __init__.py
      - factor_research.py     — Momentum / Value / Volatility 計算
      - feature_exploration.py — 将来リターン / IC / 統計サマリ
    - ai/
      - __init__.py
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — レジーム判定（MA + マクロセンチメント合成）

補足 / 運用上の注意
------------------
- 本番運用時は KABUSYS_ENV=live を設定し、設定内容（APIキー、LINE 通知設定等）を慎重に確認してください。validate_config の live 向けガードを参照してください。
- AI 機能は OpenAI API を使用します。API コストとレート制限に注意してください。環境変数 OPENAI_API_KEY を必ず設定してください。
- Monitoring は停止フラグ（data/stop_requested.flag）や kill.flag（Settings.kill_flag_path）を利用して外部から停止/シャットダウンを制御します。
- ログディレクトリの作成に失敗した場合はコンソール出力のみで継続します（utils.logging_setup の設計方針）。
- データベースのマイグレーションは簡易的に init_monitoring_db 内で行います。互換性に注意して運用してください。

開発・拡張のヒント
------------------
- research および ai モジュールは DuckDB 接続を受け取る設計なので、ローカルで DuckDB を用意すればオフラインで高速に実験できます。
- ExecutionEngine の BrokerFactory は環境に応じて Mock / 実ブローカーを切り替えられるため、ペーパートレードで検証してから本番に移行してください。
- テストでは環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

ライセンス / バージョン
----------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"
- ライセンス表記はリポジトリの LICENSE ファイルをご確認ください（なければ運用前に追加してください）。

必要な情報や README に追記してほしい実行例（具体的な起動コマンドのテンプレート、.env の例、CI 用の簡易起動手順など）があれば教えてください。必要に応じて例 .env テンプレートや systemd / docker-compose での運用例も作成します。