# KabuSys

日本株向け自動売買システムのコアライブラリ群（プロトタイプ）。  
このリポジトリには、発注エンジン、監視・アラート、ポートフォリオ構築、リサーチ（ファクター計算）、およびニュースを用いたAIスコアリングなどの主要コンポーネントが含まれています。

注意: .env などの秘密情報は絶対に git にコミットしないでください。

---

目次
- プロジェクト概要
- 機能一覧
- 動作要件（依存ライブラリ）
- セットアップ手順
- 使い方（主要コマンド）
- 重要な環境変数
- ログ・停止フラグについて
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買システムの基礎モジュール群です。
- 発注ロジック（ExecutionEngine）と監視（MonitoringEngine）、リスク管理、ポートフォリオ構築、リサーチ（ファクター・IC 等）、およびニュースを用いたAIによるセンチメントスコアリングを含みます。
- 実行モードとして development / paper_trading / live を切り替えられ、paper_trading 時は実取引と分離された専用 DB と Mock ブローカーが使われます。

機能一覧
- Execution
  - ExecutionEngine による発注セッション管理
  - BrokerClientFactory を介した本番/モックブローカー切替（KABUSYS_ENV=paper_trading）
  - OrderRepository / OrderManager / Reconciler / RiskManager 等による発注フロー
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス生存・データ鮮度監視
  - TradeMonitor: 発注ログの監視（滞留注文・異常約定等）
  - RiskMonitor: ドローダウンやポジション上限の監視とアラート記録
  - KillSwitch: 条件に応じて data/kill.flag を生成し ExecutionEngine に停止シグナルを送る
  - MonitoringEngine: 各モニタを周期的に実行しアラート判定
- Portfolio
  - 候補選定、等金額／スコア加重の重み算出
  - リスク調整（セクター上限・レジーム乗数）
  - 発注数決定（position sizing） — lot 単位丸め、aggregate cap のスケーリング
- Research
  - ファクター計算（Momentum, Volatility, Value 等）: DuckDB を用いた SQL ベース集計
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュース NLP（OpenAI）で銘柄別センチメントスコア生成（ai_scores テーブルへ保存）
  - レジーム判定（ETF の MA200 とマクロセンチメントの合成）
- ツール
  - 環境設定ウィザード（python -m kabusys.config_setup）: .env 作成支援
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

動作要件（主要依存ライブラリ）
- Python 3.10+（型注釈等を利用）
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config/*.yaml の内容検証は任意・validate_config で使用）
- sqlite3（標準ライブラリ）
- これらは requirements.txt が無い場合、pip でインストールしてください:
  pip install duckdb psutil openai PyYAML

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone <repo> && cd <repo>
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai PyYAML
4. 環境変数設定 (.env) — ウィザード推奨
   - python -m kabusys.config_setup
   - ウィザードは .env を生成します（デフォルト: プロジェクト直下の .env）
   - 作成後、設定を検証: python -m kabusys.validate_config
5. データディレクトリ
   - data/ は自動作成される処理が多いですが、必要に応じて手動作成してください
   - 監視 DB デフォルト: data/monitoring.db
   - DuckDB デフォルト: data/kabusys.duckdb
   - Paper Trading DB: data/paper_trading.db

主要な使い方（コマンド例）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い（exit 1）
- ExecutionEngine を起動（本番/ペーパーは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 実行中の停止: プロセスに SIGINT（Ctrl+C）を送るか、プロジェクトルート/data/stop_requested.flag を作成すると安全に停止します
    - 実行時に PID ファイル data/execution.pid を書き込みます（設定で変更可）
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用して監視データを書き込む点に注意
  - 停止: 同様に data/stop_requested.flag を作成、または Ctrl+C
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で DB パス指定可

重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants API 用
- KABU_API_PASSWORD (必須): kabuステーション API パスワード
- KABUSYS_ENV: execution モード ('development' / 'paper_trading' / 'live')（デフォルト: development）
- OPENAI_API_KEY: OpenAI を用いる AI 機能で必須
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject、デフォルト instant）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- LOG_LEVEL: ログレベル（INFO など）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（本番は 0 推奨）

ログ・停止フラグについて
- ロギング:
  - kabusys.utils.logging_setup.setup_logging を通じて統一設定
  - デフォルトのログディレクトリ: logs/
  - 各アプリ名（execution / monitoring など）で logs/<app_name>.log に日次ローテーションで出力
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring は安全に終了処理を行います
  - KillSwitch はルールに合致した場合 data/kill.flag を書き込み、ExecutionEngine 側が停止する仕組みです
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag を自動クリアします（本番では危険）

開発者向け注意
- DuckDB を用いた分析系（research, ai）はローカルの DuckDB ファイル（prices_daily, raw_news, raw_financials 等）に依存します。適切なデータがないと出力は不完全になります。
- AI 関連（news_nlp, regime_detector）は OpenAI API を利用します。API 利用には課金やレート制限の考慮が必要です。
- .env 自動ロード: kabusys.config はプロジェクトルート（.git または pyproject.toml）を基に .env を自動読み込みします。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数/設定読み込み・Settings クラス
  - config_setup.py — .env 対話ウィザード（python -m kabusys.config_setup）
  - validate_config.py — 設定検証 CLI（python -m kabusys.validate_config）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring のポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度設定ユーティリティ
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 発注株数算出
  - research/
    - factor_research.py — モメンタム/ボラティリティ/バリュー等のファクター計算
    - feature_exploration.py — 将来リターン/IC/統計サマリー
  - ai/
    - news_nlp.py — ニュース記事を OpenAI で評価し ai_scores に書込む
    - regime_detector.py — マーケットレジーム判定（MA200 と LLM センチメントの合成）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite テーブル作成・永続化 API
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — (発注ログ監視) — ※実装ファイルあり（この README の対象外部分）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag 制御
    - alert_manager.py — (アラート送信管理) — ※実装ファイルあり（この README の対象外部分）
  - execution/
    - execution_engine.py, broker_factory.py, order_repository.py, order_manager.py, reconciler.py, risk_manager.py
      （発注エンジンと関連コンポーネント）
  - data/ （実行時に使用されるファイル類）
    - monitoring.db（デフォルト） / paper_trading.db / kabusys.duckdb など
    - execution.pid / stop_requested.flag / kill.flag

ライセンス・貢献
- （ここにプロジェクトのライセンスや貢献方法を追記してください）

お問い合わせ
- 実行方法や拡張について不明点があれば、リポジトリの issue または開発チームにお問い合わせください。

以上。README を参照して環境構築・実行を行ってください。必要であれば、実行例や systemd / supervisor 用のサービス定義テンプレートなども追加できます。