# KabuSys

日本株向け自動売買 / 研究支援ライブラリ群。  
このリポジトリは実運用向けの監視・発注・ポートフォリオ構成・ファクター計算・AI 補助モジュール等を含んでいます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 前提・依存関係
- セットアップ手順
- 環境設定の作成・検証
- 実行方法（監視 / エンジン / レポート）
- 主要環境変数（抜粋）
- 監視・停止フラグの挙動
- ディレクトリ構成（主要ファイル）

---

プロジェクト概要
- KabuSys は日本株自動売買のためのコンポーネント群です。発注エンジン（Execution Engine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースの NLP によるセンチメント評価・レジーム判定）、および研究用ユーティリティを提供します。
- 設計方針として、本番 DB や発注 API への直接アクセスを制御しつつ（ペーパートレード用 DB の分離など）、ログ／監視／安全停止（Kill Switch）機構を備えています。

主な機能
- 環境設定ウィザード（.env の対話式生成）
- 設定検証 CLI（環境変数や config/*.yaml のチェック）
- 実行エンジン起動スクリプト（paper_trading モード対応）
- 監視プロセス（SystemMonitor / TradeMonitor / RiskMonitor を束ねる）
- Kill Switch：条件に応じた停止フラグ書込み
- Paper Trading の検証レポート生成スクリプト
- ポートフォリオ構築・サイズ算出（等重み・スコア重み・リスクベース）
- 研究用ファクター計算・特徴量探索（DuckDB ベース）
- AI モジュール（OpenAI を使ったニュースセンチメント / レジーム判定）
- 統合的なログ設定（コンソール + 日次ローテートファイル）

前提・依存関係
- Python 3.10 以上（typing の | 演算子等を使用）
- 推奨パッケージ（代表例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証で任意）
- SQLite：標準ライブラリ sqlite3 を使用
- （実運用で kabuステーション API 等のクライアントが必要）

セットアップ手順（ローカル開発の流れ）
1. リポジトリをクローン
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトに requirements.txt があればそれを利用）
4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabu API トークンや DB パス等の入力を促します
5. 設定の検証
   - python -m kabusys.validate_config
   - --strict オプションをつけると警告も失敗（exit 1）扱いになります

主要な使い方（コマンド例）
- 環境設定ウィザード
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config [--strict]
- 監視ループ起動（SystemMonitor を定期実行）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を秒で上書き（デフォルト 60 秒）
  - 監視は KABUSYS_ENV に関わらず settings.sqlite_path（本番 sqlite_path）を使用します
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、data/paper_trading.db を使用して本番 DB と分離します
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - 環境変数 PAPER_TRADING_SQLITE_PATH または --db で DB パスを指定可能
- AI 関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — OPENAI_API_KEY 必須
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) — OPENAI_API_KEY 必須

主要環境変数（抜粋）
- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- 動作モード / ログ
  - KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）
  - LOG_DIR — ログディレクトリ（デフォルト: logs/）
- DB パス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- その他
  - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で必要）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE — Paper Trading の約定挙動: instant | partial | never | reject（デフォルト: instant）
  - KILL_FLAG_CLEAR_ON_START — （1）で起動時に kill.flag を自動クリア（本番では 0 推奨）

監視・停止フラグの挙動（重要）
- stop_requested.flag（data/stop_requested.flag）:
  - run_monitoring / run_execution はこのファイルの存在を検出すると安全にループを停止します（停止フラグ）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）:
  - KillSwitch が内部条件（ドローダウン超過・ポジション上限超過等）を満たすと書き込みます。ExecutionEngine はこのフラグを検出して停止します。
  - KILL_FLAG_CLEAR_ON_START=1 を使うと起動時に自動クリアする（本番では危険なのでデフォルト 0 を推奨）。
- execution.pid（data/execution.pid）:
  - ExecutionEngine の PID 書き込み先。run_execution はこの PID ファイルを使います。

ログとプロセス優先度
- ログはデフォルトで stdout と 日次ローテートのファイル出力（logs/<app_name>.log）に出力されます（30 日保持）。
- 起動スクリプトは最初に set_process_priority("high") を呼び、可能な限り高い優先度で実行を試みます（プラットフォーム依存、失敗時は警告）。

AI 機能について
- news_nlp（ニュース NLP）は OpenAI（gpt-4o-mini 等）を利用して銘柄別センチメントを計算し ai_scores テーブルへ書き込みます。OPENAI_API_KEY が必須。
- regime_detector は ETF (1321) の MA200 とマクロニュースの LLM センチメントを合成して日次の市場レジームを作成します。OPENAI_API_KEY が必須。
- 両者とも API 呼び出しに対するリトライやフェイルセーフが実装されており、API 失敗時は安全側の値（例: macro_sentiment=0.0）で継続します。

開発者向けメモ（設計・実装のポイント）
- 設定ロード: config.py はプロジェクトルート（.git または pyproject.toml）の検出を試み、自動で .env を読み込みます。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。
- DB 分離: run_monitoring は環境に関わらず本番 sqlite_path を使用する設計（監視ログは一元管理）。run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使用して本番 DB と分離します。
- DuckDB は研究 / ファクター計算向けの列指向 DB（prices_daily、raw_financials 等のテーブルを想定）。
- 多くのモジュールは DB 接続（sqlite3/duckdb）を外部から受け取る設計で、単体テストや DI が容易です。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / Settings 管理
  - config_setup.py                — .env 対話式ウィザード
  - validate_config.py             — 設定検証 CLI
  - run_monitoring.py              — SystemMonitor ポーリングループ起動
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py             — ログ設定ユーティリティ
    - process_priority.py          — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             — SQLite 永続化層（監視）
    - system_monitor.py
    - trade_monitor.py (参照されるがここに含まれる想定)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照されるがここに含まれる想定)
  - execution/
    - execution_engine.py (参照される)
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
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

（上記は本リポジトリに含まれる主要ファイルの抜粋です。詳細はソースを参照してください。）

トラブルシューティング（よくある注意点）
- .env に秘密情報を含めるため、絶対に Git にコミットしないでください。
- PyYAML がない場合、validate_config は YAML のパース検証をスキップします（警告）。
- DuckDB / OpenAI のバージョン差による挙動差が発生する可能性があるため、開発環境ではパッケージバージョンを固定することを推奨します。
- run_monitoring.run_execution は stop_requested.flag / kill.flag / execution.pid 等のファイルを data/ 配下に作成・参照します。必要に応じて data/ ディレクトリの書き込み権限を確認してください。

ライセンス / 貢献
- （この README にはライセンス情報を含めていません。リポジトリの LICENSE ファイルをご確認ください）

---

ご質問や README の追記（例: 具体的な設定例、運用手順書、Docker 化手順など）を希望される場合は、どの項目を詳しくしたいか教えてください。