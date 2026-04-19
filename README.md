# KabuSys

日本株向け自動売買システムの実装（ライブラリ + 起動スクリプト群）。

このリポジトリは戦略・ポートフォリオ構築・発注実行・監視・研究ツール・AI連携などを含むモジュール群を提供します。設計方針として「本番コードと研究コードを分離」「ルックアヘッドバイアスの排除」「フェイルセーフの優先」を重視しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要スクリプト／コマンド）
- 主要環境変数（抜粋）
- 実装上の注意点
- ディレクトリ構成

---

プロジェクト概要
- 日本株の自動売買を目的としたシステム基盤ライブラリ群。
- モジュール単位で使えるように設計されており、ExecutionEngine（発注/リスク/調整）・Monitoring（稼働監視 / Kill Switch）・Research（ファクター計算 / 特徴量解析）・AI（ニュース NLP / レジーム判定）等を含む。
- SQLite（監視ログ等）と DuckDB（分析用データ格納）を利用する構成。

---

主な機能
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象化（実運用では実ブローカ、paper_trading 時は MockBrokerClient）
  - 注文管理、注文リポジトリ、リコンシリエーション、リスク管理（RiskManager）等
  - Paper trading と live を完全に分離（paper_trading は専用 DB に記録）
- Monitoring
  - SystemMonitor（CPU/メモリ/Disk / データ鮮度 / 実行プロセス監視）
  - TradeMonitor / RiskMonitor / KillSwitch / AlertManager を組合せた MonitoringEngine
  - 監視ループ起動スクリプト（run_monitoring.py）
  - 監視ログ永続化用の SQLite テーブル群（monitoring_db.py）
- Portfolio construction
  - 候補選定、等配分／スコア加重、リスクベースのポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC 計算、統計サマリー等
  - DuckDB 接続を受けて SQL と Python の組合せで高速に実行
- AI（OpenAI 連携）
  - ニュースを LLM に投げて銘柄ごとのセンチメントを ai_scores に書き込む（news_nlp）
  - マクロニュース + ETF MA200 を組合せた市場レジーム判定（regime_detector）
  - OpenAI API 呼び出しは冗長なエラーハンドリングとリトライを実装
- ツール
  - 環境設定ウィザード（config_setup.py）で .env を対話的に生成
  - 設定検証 CLI（validate_config.py）で .env と config/*.yaml を事前チェック
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

セットアップ手順（開発 / ローカル実行向け）
1. 前提
   - Python 3.10 以降を推奨（PEP 604 の型記法などを使用）
   - システムに sqlite3 は標準搭載。外部ライブラリは下記をインストールしてください。
2. 依存ライブラリ（代表）
   - duckdb
   - psutil
   - openai（AI 機能を使う場合）
   - PyYAML（config 検証で YAML ファイル検証を行いたい場合）
   - 他、プロジェクトで追加しているパッケージがある場合は pyproject.toml / requirements.txt を参照
3. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -U pip
   - pip install duckdb psutil openai pyyaml
4. .env の準備
   - 対話式ウィザード: python -m kabusys.config_setup
     - J-Quants トークン・kabu API パスワードなど必須値を入力して .env を作成できます
   - 自動ロード: config モジュールはプロジェクトルートに .env / .env.local があれば自動で読み込みます
   - 自動ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密扱いにするには --strict を付与
6. データディレクトリ（logs, data）の作成
   - ログはデフォルトで logs/<app_name>.log に出力されます（ログディレクトリは自動作成を試行）
   - データファイルは data/ 以下に作成されます（必要に応じて .env で上書き）

---

使い方（主要スクリプト／コマンド）
- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話的に作成 / 更新します
- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も FAIL 扱いで exit(1)
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の MockBrokerClient を使用し、data/paper_trading.db（または env で指定した PAPER_TRADING_SQLITE_PATH）に記録します
    - プロセス優先度を "high" に設定します
    - data/stop_requested.flag が存在すると起動せず終了します
    - 実行時に data/execution.pid を書きます（設定に応じて）
- Monitoring 起動（監視ループ）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60 秒）
    - 監視は常に本番 sqlite_path を使用（設定にかかわらず）
    - data/stop_requested.flag を検知するとループを終了します
- Paper Trading 検証レポート出力
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB ファイルパスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）
- AI / リサーチ API（ライブラリ関数として利用）
  - ニューススコア付与:
    - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=<OPENAI_API_KEY>)
    - OpenAI API キーは引数か環境変数 OPENAI_API_KEY を使用
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(conn, target_date, api_key=<OPENAI_API_KEY>)

運用時の停止（Kill Switch / Stop Flag）
- data/kill.flag : Kill Switch が設定されると ExecutionEngine に停止シグナルを出すためにこのファイルを作成します（KillSwitch クラスが書き込む）
- data/stop_requested.flag : run_execution/run_monitoring が外部停止指示（手動停止等）を検出するためのフラグファイル。存在すると起動・ループ継続を停止します

ログ
- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- デフォルトログディレクトリ: logs/
- ログローテーション: 日次、30 日分保持

---

主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DUCKDB_PATH: 分析用 DB（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の約定動作）
- OPENAI_API_KEY: OpenAI を使う機能で参照
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = 自動クリア、0 = クリアしない）

注意点 / 実装上の要約
- 設定の自動読み込み: config モジュールはプロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動ロードします。テスト等で自動ロードを止めるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 分離:
  - 監視機能は常に sqlite_path（監視 DB）を使用します（KABUSYS_ENV に依らない）。
  - ExecutionEngine は paper_trading の場合のみ paper_sqlite_path を使って本番 DB と完全分離します。
- OpenAI 連携:
  - news_nlp / regime_detector は OpenAI API を使います。API のレート制限・接続エラー等を考慮してリトライと保険（フェイルセーフ）を実装していますが、APIキーが未設定だと例外を投げます。
- フェイルセーフ設計:
  - LLM 呼び出し失敗時は基本的に安全側のデフォルト値（例: macro_sentiment = 0.0）で続行するように実装されています。
- ロック / 同時実行:
  - run_execution は PID ファイルを使います。外部スクリプトや運用監視と合わせて使ってください。
- DuckDB / SQLite API 互換性:
  - 一部実装で DuckDB の executemany の仕様や型バインドの注意点（空リスト不可等）に配慮しています。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/.env 読み込み、Settings クラス
  - config_setup.py                — .env ウィザード（対話式）
  - validate_config.py             — 起動前設定検証 CLI
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証用レポート生成
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
    - news_nlp.py                   — ニュースセンチメント（OpenAI）
    - regime_detector.py            — 市場レジーム判定（OpenAI + ETF MA）
    - __init__.py
  - monitoring/
    - monitoring_db.py              — SQLite スキーマ / 永続化層
    - system_monitor.py
    - risk_monitor.py
    - trade_monitor.py (実装ファイルあり)
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (実装ファイルあり)
  - execution/
    - execution_engine.py (実装ファイルあり)
    - broker_factory.py (実装ファイルあり)
    - order_manager.py (実装ファイルあり)
    - order_repository.py (実装ファイルあり)
    - reconciler.py (実装ファイルあり)
    - risk_manager.py (実装ファイルあり)
  - utils/
    - logging_setup.py               — ログ設定ユーティリティ
    - process_priority.py            — プロセス優先度 / CPU affinity 設定
    - __init__.py

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください）

---

追加情報 / 開発者向けメモ
- unit test を書く際は config の自動 .env ロードを無効化するか、環境変数をテスト内で注入してください（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
- LLM 呼び出し部分（news_nlp._call_openai_api, regime_detector._call_openai_api 等）は単体テスト向けに patch / monkeypatch して置換する設計になっています。
- DuckDB クエリは基本的に prices_daily / raw_financials / raw_news 等のテーブルを前提にしています。テスト用データを作ってから各関数を呼び出してください。

---

問題報告 / 貢献
- バグレポートや機能提案は issue を立ててください。Pull Request での貢献歓迎です。

---

以上がこのコードベースの概要と利用方法になります。必要であれば「設定ファイルのサンプル .env.example」や「起動時のユースケース別チェックリスト（本番切替手順等）」を追加で作成します。どの情報を優先的に整備しましょうか？