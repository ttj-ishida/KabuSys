# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）。  
このリポジトリは、戦略・ポートフォリオ構築・発注制御（ExecutionEngine）・監視（Monitoring）・研究用ツール・AI支援モジュール等を含むモジュール化された実装を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要コマンド例）
- 環境変数（主要項目）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は「日本株の自動売買システム」を目的としたコードベースです。
- 発注周り（ExecutionEngine）、監視（Monitoring）、リスク管理、ポートフォリオ構築、ファクター計算・リサーチ、AI（ニュース NLP / レジーム判定）を有しています。
- paper_trading（ペーパートレード）モードにより、実際の注文と分離して動作させられる設計です（専用 SQLite DB を使用）。

主な機能
- 実行エンジン（ExecutionEngine）
  - ブローカークライアントの抽象化（本番と Mock を切り替え可能）
  - 発注管理、リスク管理、照合（reconciler）
  - 起動 / 停止用の pid ファイル・停止フラグに対応
- 監視モジュール（Monitoring）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度監視
  - TradeMonitor: 発注・約定ログの監視（滞留注文・約定異常などの検出）
  - RiskMonitor: ドローダウンやポジション上限の監視とアラート
  - KillSwitch: 監視結果に基づく停止フラグ書込（data/kill.flag）
  - MonitoringEngine: 各 Monitor を束ねたポーリングループ
  - 永続化: SQLite ベースの監視 DB（monitoring_db）
- ポートフォリオ構築（pure function群）
  - 候補選定、等金額/スコア重み、ポジションサイズ計算、セクター上限、レジーム乗数
- 研究 / ファクター計算（DuckDB ベース）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC 等の統計ツール
- AI モジュール（OpenAI）
  - ニュースのセンチメント評価（news_nlp）
  - マクロニュース＋ETF MA で市場レジーム判定（regime_detector）
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
- 設定ユーティリティ
  - 対話式 .env ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）
- ロギング / プロセス優先度ユーティリティ
  - 統一的なログ設定（logs/<app>.log 日次ローテーション）
  - プロセス優先度・CPU affinity 設定

---

セットアップ手順（開発・ローカル実行向け）
前提
- Python 3.10 以上を推奨（型注釈に Python 3.10 の構文を使用）
- 仮想環境を作ることを推奨（venv / poetry 等）

1. リポジトリをクローンして仮想環境を作成
   - git clone ...
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb psutil openai
   - PyYAML は設定ファイルの検証で任意: pip install PyYAML
   - （実運用用の追加パッケージや requirements.txt があればそちらを使用）

3. ディレクトリ作成
   - デフォルトで使用するデータ/ログディレクトリを作成:
     - mkdir -p data logs

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - もしくは .env.example を参考に .env を手動作成
   - 自動的に .env をロードする挙動は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます

5. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いにして終了コード 1 になります

注意:
- OpenAI を使う機能を実行する場合は OPENAI_API_KEY を設定する必要があります。
- 実取引（live）モードでは設定を慎重に（LINE 通知等の設定確認を推奨）。

---

主要な使い方 / 実行コマンド
（プロジェクトルートで実行）

- 設定ウィザード（.env を生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動
  - 通常（デフォルト .env の KABUSYS_ENV に従う）
    - python -m kabusys.run_execution
  - ペーパートレードで起動する例:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - paper_trading の場合は MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します
  - 停止方法:
    - run_execution は data/stop_requested.flag を監視します。手動停止用にフラグファイルを作成するとエンジンが停止します。
    - また、監視側（KillSwitch）が data/kill.flag を書き込むとアラート／停止のトリガになります。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を環境変数で上書き:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    - デフォルト 60 秒
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します
  - 停止方法:
    - data/stop_requested.flag を作成すると監視ループが終了（上位の停止処理のためのフラグ）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI モジュール（コード呼び出し例）
  - news scoring:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key optional if OPENAI_API_KEY set
  - regime scoring:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

ログ
- ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリを事前に作成してください）。
- setup_logging() により stdout にも出力されます。

---

主要な環境変数（抜粋）
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
  - KABU_API_PASSWORD — kabuステーション API パスワード（必須）

- 実行環境・動作切替
  - KABUSYS_ENV — execution/monitoring の実行環境（development / paper_trading / live）デフォルト: development
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

- データベース / パス
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）

- OpenAI / AI
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
  - PAPER_FILL_MODE — MockBroker の約定モード（instant / partial / never / reject）

- ログ / レベル
  - LOG_LEVEL — デフォルト INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ保存先（デフォルト logs/）

- モニタリング
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

補足: .env 自動読み込み
- config.py はプロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local があれば自動で読み込みます。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - config_setup.py         — 対話式 .env ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity ユーティリティ
  - execution/               — 発注エンジン関連（BrokerClientFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py      — SQLite ベースの監視 DB レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
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
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — 市場レジーム判定
  - tools/
    - paper_verification_report.py

その他ファイル・ディレクトリ（推奨）
- data/                     — データベース・フラグファイル等（SQLITE/duckdb/pid/flag）
  - monitoring.db (デフォルト)
  - paper_trading.db (paper_trading 用)
  - kill.flag
  - stop_requested.flag
  - execution.pid
- logs/
  - execution.log
  - monitoring.log
  - ...（日次ローテーション）

---

運用上の注意
- KABUSYS_ENV=live での運用は危険を伴います。validate_config で警告を確認し、LINE 等の通知設定を確認してください。
- KillSwitch（data/kill.flag）は監視から発行される重要な停止トリガです。KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に自動クリアしてしまうため、本番では 0 を推奨します。
- paper_trading モードは本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しは失敗時にフェイルセーフ（ゼロやスキップ）でフォールバックする実装ですが、API 使用についてはコストとレート制限に注意してください。

---

貢献 / 開発メモ
- 単体テスト・モックは各モジュールで想定されています（例: news_nlp の OpenAI 呼び出しは差し替え可能）。
- DuckDB 接続を利用するリサーチ機能は外部 API に依存せず、ローカルデータベース上で完結する設計です。
- 構成ファイル（config/*.yaml）は設定テンプレート生成スクリプト等で補える想定（validate_config から参照）。

---

ライセンス / 著作権
- この README にはライセンス情報が含まれていません。実際の運用・配布の際は適切なライセンスファイルをプロジェクトルートに追加してください。

---

README は以上です。必要であれば、実行例のスクショ/ログの例、または詳細な環境変数一覧（すべての Settings プロパティ）を追加で生成できます。どの情報を詳しく追記しますか？