# KabuSys

日本株自動売買システムの Python コードベース。ポートフォリオ構築、発注実行、監視、リサーチ、AI（ニュースセンチメント・レジーム判定）などのモジュール群を含みます。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存パッケージ
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主な項目）
- ファイル / ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買を目的としたモジュール群です。
- 主な機能は「シグナルの生成 → ポートフォリオ構築 → 発注（実取引 or ペーパートレード） → 監視 / アラート / Kill Switch」。
- DuckDB をデータ分析用に、SQLite を軽量永続化（監視ログ・ペーパートレード記録）に使用します。
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価やマクロセンチメントを使ったレジーム判定機能を備えます（APIキー必須）。

---

機能一覧
- execution（ExecutionEngine）
  - 本番 / ペーパートレード両対応。環境 KABUSYS_ENV に応じてブローカークライアントを切替。
  - リスク管理（RiskManager）、注文管理（OrderManager）、整合性チェック（Reconciler）。
- monitoring
  - SystemMonitor：CPU・メモリ・ディスク、データ鮮度、実行プロセス生存を監視し履歴を SQLite に保存。
  - TradeMonitor / RiskMonitor：滞留注文・約定異常・ドローダウン・ポジション数などを監視、必要時に kill.flag を書き込み。
  - MonitoringEngine：上記監視器のポーリングとアラート連携。
- portfolio
  - 候補選定（select_candidates）、重み計算（等金額 / スコア重み）、ポジションサイズ計算（リスクベース等）、セクター制限、レジーム乗数。
- research
  - ファクター計算（momentum, value, volatility）、将来リターン、IC（Information Coefficient）解析、統計サマリ。
- ai
  - news_nlp.score_news：ニュースを LLM で採点し ai_scores テーブルへ書き込み。
  - regime_detector.score_regime：ETF とニュースを組み合わせて市場レジーム判定。
- tools
  - paper_verification_report：ペーパートレード DB からレポート（稼働率、成功率、レイテンシ等）を生成。
- utils
  - ロギング設定（統一的な stdout + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
  - 環境設定読み込み（.env 自動読み込み / config.Settings）

---

前提・依存パッケージ
- Python 3.9+
- 主要依存（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config ファイル検証 optional）
- 実行環境により追加パッケージが必要になる可能性があります。プロジェクト内に requirements.txt がある場合はそれを使用してください（本リポジトリの例では明示ファイル無しのため、上記パッケージを pip でインストールしてください）。

---

セットアップ手順（ローカル開発想定）
1. リポジトリをクローンし、仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （追加で必要なパッケージがあればインストール）

3. .env の作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは .env を生成・編集します。生成後、設定内容を確認してください。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

5. ディレクトリ（初回実行で自動作成される場合が多い）
   - data/ : SQLite や flag, pid ファイルの配置場所（デフォルト）
   - logs/ : ログ出力ディレクトリ（デフォルト）

---

使い方（主要コマンド例）
- ExecutionEngine（本番/ペーパー起動）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading なら paper_trading 用の MockBrokerClient と data/paper_trading.db が使用され、本番 DB と分離されます。
  - 実行中に data/stop_requested.flag を作成すると安全に停止されます。
- Monitoring（監視ループ起動）
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用します（監視 DB は常に production path）。
- 設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - --from YYYY-MM-DD --to YYYY-MM-DD や --db PATH で期間 / DB を指定可能。

モジュール API（一部）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続と日付を与えてニューススコアを ai_scores に書き込む（OpenAI APIキー必須）。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - DuckDB で市場レジームを計算して market_regime テーブルへ書き込み。

停止 / Kill Switch
- kill.flag（デフォルト data/kill.flag）を作成すると ExecutionEngine に停止シグナルを送ります（KillSwitch が設計されています）。
- stop_requested.flag（data/stop_requested.flag）を作成すると run_monitoring/run_execution のループが検知して終了します。
- PID ファイル: data/execution.pid（ExecutionEngine の PID を書き込みます）。

---

主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視）ファイルパス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時に必要）
- MONITOR_POLL_INTERVAL: monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" で有効、デフォルト 0。production では 0 推奨）

.env 作成の注意
- .env は絶対に Git 管理に含めないでください（Secrets を含むため）。
- config_setup で .env を作成した後、validate_config で検証してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 起動前設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ（stdout + 日次ローテート）
    - process_priority.py   — プロセス優先度・CPU affinity 設定
  - execution/              — 発注関連実装群（BrokerFactory, ExecutionEngine, OrderManager, RiskManager, Reconciler など）
  - monitoring/
    - monitoring_db.py      — SQLite スキーマ初期化 / 永続化 API
    - system_monitor.py     — システム監視（CPU/メモリ/データ鮮度/プロセス）
    - risk_monitor.py       — ドローダウン / ポジション上限検知
    - kill_switch.py        — kill.flag の書き込み/評価
    - monitoring_engine.py  — 各 monitor を束ねるポーリングエンジン
    - (TradeMonitor / AlertManager など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py           — ニュースを LLM に送りセンチメントを計算 / 書き込み
    - regime_detector.py    — ETF とマクロニュースからレジーム判定
    - __init__.py
  - data/ (実行時に生成される想定)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
    - kill.flag / stop_requested.flag / execution.pid
  - logs/
    - execution.log, monitoring.log ...（デフォルト）

---

運用上の注意 / ベストプラクティス
- 本番（KABUSYS_ENV=live）では Kill Switch、LINE 通知などの設定を必ず確認してください。validate_config は本番チェック用の警告を出します。
- .env はローカル / CI 環境ごとに安全に管理し、決してリポジトリにコミットしないこと。
- OpenAI の呼び出しは API エラーやレート制限を想定して指数バックオフやフェイルセーフの設計がありますが、API課金やレイテンシの影響を考慮してください。
- Monitoring は常に production の sqlite_path を使用する設計です（監視データは環境に依らず一貫して送る想定）。
- ペーパートレードを行う場合は KABUSYS_ENV=paper_trading を利用し、DB を分離してください（PAPER_TRADING_SQLITE_PATH）。

---

トラブルシューティング（よくある事象）
- .env が読み込まれない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定していないか確認。config.py はプロジェクトルート（.git または pyproject.toml）を探して .env を自動読み込みします。
- ログファイルが生成されない場合:
  - 権限やログディレクトリ作成の失敗が原因の可能性があります。stdout に警告が出ます。LOG_DIR を指定するか、logs/ を作成してください。
- OpenAI 呼び出しの認証エラー:
  - OPENAI_API_KEY が設定されているか確認してください。ai モジュールの関数は api_key 引数で上書き可能です。

---

ライセンス / 貢献
- 本 README はコードベースの簡易ドキュメントです。実際のライセンスや貢献ガイドがプロジェクト内にある場合はそちらに従ってください。

---

必要であれば、各モジュール（ExecutionEngine、OrderManager、RiskManager、Monitoring の挙動）について詳細な使用例や API 仕様、ユニットテストの書き方を追記します。どのモジュールの詳細を優先して欲しいか教えてください。