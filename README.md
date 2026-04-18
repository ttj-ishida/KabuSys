KabuSys — 日本株自動売買システム
=================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うための Python パッケージです。  
主要機能は以下の通りです：

- 発注実行エンジン（ExecutionEngine）とペーパートレード分離
- システム/トレード/リスク監視と Kill Switch（フラグファイル）による安全停止
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュース NLP を用いたセンチメント評価（OpenAI API 経由）
- 各種 CLI（環境ウィザード、設定検証、検証レポート生成）
- ログ設定・プロセス優先度・CPU affinity ユーティリティ

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番 / ペーパー切替）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config_setup.py: .env を対話式で作成/更新するウィザード
  - validate_config.py: .env および config/*.yaml の起動前チェック
  - config.Settings: 環境変数アクセスのラッパー（デフォルト値・検証含む）
- 監視
  - monitoring_engine.py: 各モニタを束ねてポーリング・アラート発行
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 個別監視ロジック
  - monitoring_db.py: SQLite に監視ログ・ダッシュボードを永続化
  - kill_switch.py: リスク条件で data/kill.flag を書いて Execution を停止
- 発注関連（実装ファイル群は execution パッケージ）
  - BrokerClientFactory：環境に応じて実ブローカー/モックを供給（paper_trading の分離）
  - OrderManager / OrderRepository / RiskManager / Reconciler / ExecutionEngine
- ポートフォリオ（純粋関数群）
  - portfolio_builder: 候補選定・重み計算
  - position_sizing: 株数決定・集約キャップ調整
  - risk_adjustment: セクターキャップ・レジーム乗数
- リサーチ
  - research.factor_research: Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン計算、IC、統計サマリー
- AI（OpenAI）
  - ai.news_nlp: ニュースを LLM でスコアリングして ai_scores テーブルへ書き込み
  - ai.regime_detector: ETF + マクロニュースで市場レジーム判定し market_regime に保存
- ツール
  - tools.paper_verification_report: ペーパートレードの検証レポートを生成

前提 / 必要パッケージ
--------------------
推奨 Python バージョン: 3.9+（パッケージの型注釈・機能から想定）  
必須 / 任意パッケージ（例）:
- 必須（起動に一般的に必要）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意
  - PyYAML（config/*.yaml の構文検証を行う場合）
  
インストール例（venv を想定）:
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai PyYAML

セットアップ手順
----------------
1. リポジトリをクローンし、仮想環境を作成して依存をインストールする（上記参照）。

2. .env の準備
   - 対話式ウィザードで作成:
     python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を配置（.env.example を参考にしてください）。
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用別 DB; デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能使用時）
     - LOG_LEVEL / LOG_DIR / KILL_FLAG_CLEAR_ON_START など

3. 設定検証（推奨）
   - 自動検証を実行して不足や警告を確認：
     python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

4. ディレクトリ作成
   - 実行時に data/ や logs/ を自動作成しますが、必要に応じて手動で作成して権限を確認してください。

使い方（起動・ツール）
--------------------
- ExecutionEngine を起動
  - 本番/ペーパーは KABUSYS_ENV による
  - 例（シンプル実行）:
    python -m kabusys.run_execution
  - 実行時の挙動:
    - プロセス優先度を "high" に設定（可能な環境で）
    - paper_trading 環境では MockBrokerClient を使用し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録
    - data/stop_requested.flag が存在すると起動をスキップまたは停止

- Monitoring を起動
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可（デフォルト 60 秒）
    python -m kabusys.run_monitoring
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用してログを記録します

- Kill Switch（手動）
  - kill.flag の書き込みで ExecutionEngine 停止を指示（通常は監視ロジックが自動的に書く）
  - 既定パスは data/kill.flag（Settings.kill_flag_path）

- ペーパートレード検証レポート生成
  - データベース（ペーパー用）から各種指標を計算して表示
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB ファイルパスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定してから利用
  - news_nlp.score_news / regime_detector.score_regime を DuckDB 接続と target_date を渡して呼び出します（プロダクションでは ExecutionEngine 内から呼ばれます）
  - 注意: API 呼び出しはレート制限や一時エラーに対してリトライ実装あり

環境変数の主な一覧（抜粋）
-------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 DB（paper_trading 時使用）
- LOG_LEVEL — デフォルト: INFO
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアする (0/1)

ディレクトリ構成
----------------
（主要ファイル/ディレクトリを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数ラッパー（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 & DB API
    - monitoring_engine.py   — モニタ束ね実行
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       (アラート送信ロジック等)
  - execution/
    - (ExecutionEngine, OrderManager, BrokerClientFactory など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

ログ
----
- デフォルトで StreamHandler（stdout）と日次ローテートされるファイルハンドラ（logs/<app_name>.log）を設定します。
- ログディレクトリは LOG_DIR 環境変数またはデフォルト "logs/" を使用。作成に失敗した場合はファイル出力をスキップして stdout のみで継続します。

運用上の注意
-------------
- KABUSYS_ENV=live の場合は慎重に設定を確認してください（validate_config.py は追加警告を出します）。
- kill.flag / stop_requested.flag / execution.pid 等のフラグファイルを使ってプロセス制御を行います。これらのファイルは data/ 配下に配置されます。
- データベース・ログのパスは .env で構成できます。運用ユーザーのファイル権限を適切に設定してください。
- OpenAI の API 呼び出しはコストとレート制限に注意してください。API キーは絶対に公開しないでください。

サンプル .env（抜粋）
--------------------
例（config_setup によって生成される形式を簡略化）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
OPENAI_API_KEY=sk-...

開発・拡張
-----------
- DuckDB を用いたファクター計算・AI 前処理は副作用を持たない純粋関数として設計されています（テスト容易）。
- モジュール間の依存は最小化され、AI 呼び出し等はリトライ・フェイルセーフを備えています。テスト時は外部 API 呼び出し部分（_call_openai_api 等）をモックすることを推奨します。

問い合わせ・貢献
----------------
バグ報告・機能要求は Issue でお願いします。プルリクエスト歓迎です。README やドキュメントの追加・改善も助かります。

以上が README の概要です。補足や追加したい項目（例: systemd 用サービスユニット例、より詳細な .env.example）などあれば教えてください。