KabuSys — 日本株自動売買システム（README）
====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を行うためのモジュール群です。本リポジトリは以下の主要機能を含みます。

- 発注エンジン（ExecutionEngine）と Order 管理
- 監視（Monitoring）: システム状態、注文滞留、リスク監視、Kill Switch
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制約）
- 研究（ファクター計算、将来リターン、IC 計算など）
- AI 補助（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- ペーパートレード用の分離 DB と検証レポート生成ツール
- 環境設定ウィザード・設定検証ツール

機能一覧
--------
主な機能と役割（抜粋）:

- config_setup: .env を対話式で作成/更新するウィザード（python -m kabusys.config_setup）
- validate_config: .env および config/*.yaml の事前検証ツール（python -m kabusys.validate_config）
- run_execution: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading の場合は MockBroker を使用して data/paper_trading.db に記録
- run_monitoring: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔上書き可）
- monitoring モジュール:
  - SystemMonitor: CPU/メモリ/Disk、プロセス PID、データ鮮度を監視して monitoring DB に記録
  - TradeMonitor: 注文滞留・約定異常価格を検出してリスクログへ記録
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新、アラート発行
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringEngine: 上記 Monitor を束ねて定期実行、AlertManager 経由で通知（AlertManager の実装場所あり）
- portfolio パッケージ:
  - 候補選定、等重/スコア重み、リスク調整（セクター上限）、ポジションサイズ計算（単元株丸め等）
- research パッケージ:
  - ファクター計算（Momentum, Volatility, Value 等）、特徴量探索、IC 計算、統計要約
- ai パッケージ:
  - news_nlp.score_news: raw_news を LLM（OpenAI）でスコア化して ai_scores テーブルへ書き込む
  - regime_detector.score_regime: MA とマクロニュース（LLM）を合成して市場レジーム判定、market_regime へ書き込み
- tools:
  - paper_verification_report: ペーパートレード DB から検証レポートを生成（合格基準あり）

セットアップ手順
----------------
以下は一般的なセットアップ手順の例です。プロジェクトに requirements.txt があればそれに従ってください。

1. Python 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

2. 依存パッケージインストール（例）
   - pip install duckdb psutil openai
   - PyYAML は config 検証で必要（任意）: pip install pyyaml

   （プロジェクト内に requirements.txt があれば pip install -r requirements.txt を使用）

3. .env の作成
   - 対話式で作る: python -m kabusys.config_setup
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
   - OpenAI を使う機能を利用する場合:
     - OPENAI_API_KEY を環境変数として設定（または関数引数で渡す）

4. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告を FAIL 扱いにする場合: python -m kabusys.validate_config --strict

5. データディレクトリの準備
   - デフォルト DB 等は data/ 配下に作られます。必要に応じて .env でパスを変更してください。
   - デフォルト:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

使い方（主要コマンド）
--------------------

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式に作成・更新します

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗とする

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が変わる:
    - development: 発注しない（ローカル開発向け）
    - paper_trading: MockBroker を使用し paper_trading DB に記録（本番 DB と分離）
    - live: 本番ブローカーで実際に発注
  - 停止方法:
    - プロセス起動中に data/stop_requested.flag を作成すると run_execution は検知して停止します
    - Kill Switch は data/kill.flag を生成して強制停止させる仕組みです（監視モジュール経由）

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依存せず本番監視 DB を参照）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パス指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数でも可）
  - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）などを計算し PASS/FAIL を出力

- AI 機能（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: API 呼び出しはリトライ・バックオフを組み込んでいますが、API キーとコスト管理に注意してください

重要な環境変数（主なもの）
--------------------------
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能利用時に必要）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔、秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1=クリア、0=クリアしない）

停止・キルフラグについて
------------------------
- stop_requested.flag（data/stop_requested.flag）: run_monitoring/run_execution がポーリング中に検出すると安全に停止します
- kill.flag（data/kill.flag）: KillSwitch により生成される強制停止フラグ。ExecutionEngine 起動時の挙動に影響します
- KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動でクリアしますが、本番では 0 を推奨します

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 配下の主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py       — monitoring DB（SQLite）テーブル初期化 & 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — 通知管理（実装参照）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ

補足・設計上の注意
-----------------
- ペーパートレードは本番 DB と完全分離されます（PAPER_TRADING_SQLITE_PATH を使用）
- 設定ファイル config/*.yaml はオプション（validate_config は存在チェックと PyYAML によるパース検証を行います）
- AI（OpenAI）呼び出しは外部 API を使用するため、API の失敗に備えたフェイルセーフ（フォールバック値、リトライ、部分書き込み）が組み込まれています
- プロセス優先度は起動時に set_process_priority("high") が呼ばれます（psutil を使用）。権限不足等で失敗した場合は警告が出ますが処理は継続します
- DuckDB は分析用途（prices_daily 等テーブル）で使われ、research/ai モジュールは DuckDB 接続を受け取って SQL を実行します

トラブルシューティング
-----------------------
- .env の自動ロードが働かない場合:
  - プロジェクトルート検出は .git または pyproject.toml に依存します。配布後に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
- 設定検証でエラーが出る場合は .env.example を参考に必須変数を設定してください
- OpenAI 呼び出しでエラーが出る場合は API キー、ネットワーク、利用制限（レート・課金）を確認してください

ライセンス・バージョン
---------------------
- バージョン: kabusys.__version__ = 0.1.0
- ライセンス情報はリポジトリルートの LICENSE を確認してください（存在する場合）

お問い合わせ
-----------
実装や拡張についてはソース内 docstring とコメントを参照してください。各モジュールは単体テストしやすいように設計されています（外部依存は引数で注入可能）。

以上。必要であれば README に含める具体的な実行例（コマンド例や .env のテンプレート）を追加します。ご希望があれば追記してください。