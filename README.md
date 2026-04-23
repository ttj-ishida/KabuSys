# KabuSys

日本株向け自動売買・研究フレームワーク（ライブラリ兼実行スクリプト）

バージョン: 0.1.0

---

このリポジトリは、取引エンジン、監視、ポートフォリオ構築、ファクター研究、AI（ニュース NLP）連携などを含む日本株自動売買システムのコア実装群を提供します。実行スクリプトを使って ExecutionEngine / Monitoring を起動したり、ツールでペーパートレード検証レポートを出力できます。ライブラリとして研究用・ユーティリティ関数も利用可能です。

目次
- プロジェクト概要
- 主な機能一覧
- 前提・依存パッケージ
- セットアップ手順
- 環境変数（.env）と初期設定
- 実行例（使い方）
- 主要スクリプトの動作上の注意
- ディレクトリ構成（概略）

---

プロジェクト概要
- ExecutionEngine（発注処理）と Monitoring（監視）を中心にした自動売買プラットフォームのコア。
- DuckDB を用いたリサーチ・ファクター計算、SQLite を用いた監視・発注ログの永続化。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント評価・市場レジーム判定の統合機能。
- Paper Trading（ペーパートレード）モードがあり、本番 DB と分離して動作可能。

主な機能一覧
- Execution
  - ブローカークライアント抽象 → 実環境／モック（paper_trading）切替
  - OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine 起動スクリプト
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる監視エンジン
  - kill.flag による安全停止（Kill Switch）
  - 監視ログ（system_status, trade_logs, positions, risk_logs, dashboard）を SQLite に永続化
- Portfolio
  - 候補選定、重み算出（等分・スコア加重）、ポジションサイズ算出（リスクベース等）
  - セクター上限適用やレジーム乗数の適用
- Research
  - ファクター（モメンタム / ボラティリティ / バリュー）計算（DuckDB を用いる）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI（ニュース NLP / レジーム判定）
  - raw_news を LLM に投げて銘柄別センチメントを算出・ai_scores に書き込み
  - マクロニュース + ETF (1321) MA200乖離を合成して market_regime を判定
- Tools
  - Paper Trading 検証レポート生成スクリプト（期間指定で PASS/FAIL 判定）
- 開発支援
  - .env 対話式ウィザード（config_setup）
  - 起動前設定検証 CLI（validate_config）
  - ログ設定ユーティリティ、プロセス優先度ユーティリティ等

前提・依存パッケージ
- Python 3.10+
- 必須ライブラリ（最低限）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- オプション
  - PyYAML（config/*.yaml の検証を行う場合）
- SQLite は標準ライブラリで利用可能

推奨インストールコマンド（例）
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

セットアップ手順
1. レポジトリをクローン・Python 仮想環境を用意する
2. 必要パッケージをインストール（上記参照）
3. 環境変数を設定（.env を作成）
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - あるいは手動で `.env` を用意（例は下記）
4. 設定を検証:
   ```bash
   python -m kabusys.validate_config
   # 警告も失敗扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要なデータディレクトリを確認（デフォルトは `data/`、`logs/`）
   - 実行時に自動作成される場合がありますが、パーミッション等を確認してください。

重要な環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API パスワード
- 運用関連
  - KABUSYS_ENV : 実行環境 (development | paper_trading | live) — デフォルト: development
  - LOG_LEVEL   : ログレベル (DEBUG/INFO/...)
- DB パス
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : SQLite 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（paper_trading 時）
- AI
  - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
- その他
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, PAPER_FILL_MODE（instant|partial|never|reject）
- 自動 .env ロード
  - プロジェクトルートにある `.env` / `.env.local` が自動で読み込まれます（環境変数が上書きされる仕組みあり）
  - 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

使い方（コマンド例）
- 環境設定ウィザード（.env 作成）
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```
- ExecutionEngine 起動（本番 / ペーパートレードに応じて .env の KABUSYS_ENV を切替）
  ```bash
  python -m kabusys.run_execution
  ```
  - paper_trading の場合、MockBrokerClient が使われ、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - data/stop_requested.flag が存在すると起動しない・停止するロジックあり。
- Monitoring 起動
  ```bash
  # ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能（秒、デフォルト 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は環境に関わらず本番の sqlite_path を使用して監視テーブルを初期化します（monitoring 用 DB を指定可能）。
- Paper Trading 検証レポート出力
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
- ライブラリ関数の利用例（Python REPL / スクリプト内）
  - DuckDB 接続を作成してファクター計算
    ```python
    import duckdb
    from kabusys.research import calc_momentum
    conn = duckdb.connect("data/kabusys.duckdb")
    result = calc_momentum(conn, target_date=date(2026,4,20))
    ```
  - AI スコアリング（ニュース）
    ```python
    from kabusys.ai.news_nlp import score_news
    # duckdb_conn: duckdb connection object
    n = score_news(duckdb_conn, target_date=date(2026,4,20), api_key="sk-...")
    ```
    ※ OpenAI API キーは環境変数 OPENAI_API_KEY を使うことも可能
- ログ
  - デフォルトで stdout にも出力され、日次ローテーションで logs/<app_name>.log に保存されます（ディレクトリは LOG_DIR / デフォルト "logs"）。

主要スクリプトの挙動・注意事項
- run_execution.py
  - 起動時にプロセス優先度を high に設定し、指定された SQLite（paper_trading の場合は専用）と DuckDB に接続します。
  - Engine は別スレッドで run_session を実行し、data/stop_requested.flag を検知すると停止します。
  - PID ファイル（data/execution.pid）を書きます。
- run_monitoring.py
  - SystemMonitor の単純なポーリングループを実行します。MONITOR_POLL_INTERVAL で間隔を制御。
  - Monitoring 初期化は環境に依存せず本番 sqlite_path を使います（監視 DB の分離に注意）。
- Kill Switch
  - RiskMonitor / KillSwitch により drawdown やポジション上限超過が検出されると data/kill.flag に理由を書いて ExecutionEngine に停止を要求します。
- Paper Trading
  - KABUSYS_ENV=paper_trading のときは Mock ブローカーを使用し、本番 DB と切り離した PAPER_TRADING_SQLITE_PATH に記録します。
- AI 呼び出し
  - OpenAI API リクエストはリトライ（429/タイムアウト/5xx）やレスポンス検証を含む実装。
  - API の失敗はフェイルセーフ的に 0.0 などでフォールバックする設計の箇所がありますが、必ず API キーを設定してください。

ディレクトリ構成（主要ファイル・モジュール）
（src/kabusys 以下の概略）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — 優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite 監視 DB 操作ラッパー
    - system_monitor.py
    - trade_monitor.py       — （trade 整合・滞留検知等）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - broker_factory.py
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
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング
    - regime_detector.py     — マーケットレジーム判定
    - __init__.py
  - data/                   — デフォルト DB / flag / PID を置く想定ディレクトリ（コミットしない）
  - logs/                   — ログ出力先（デフォルト）

補足・運用上の注意
- .env は絶対にリポジトリにコミットしないこと（config_setup でも注意書きあり）。
- KABUSYS_ENV を live にする場合は取り扱いに十分注意してください（validate_config は live 時に追加警告を出します）。
- Monitoring は監視用 DB に対して起動するため、監視データ参照 / 書き込みパスに注意してください。
- OpenAI を利用する機能は API コストおよびレイテンシを考慮して利用してください。API の失敗はある程度フォールバックしますが、信頼性要件に応じた運用設計を行ってください。

---

この README はコードベースの主要点をまとめたものです。詳細や追加設定は各モジュールのドキュメント（ソースコード内 docstring）を参照してください。問題や不明点があれば、どの点を詳しく知りたいか教えてください。