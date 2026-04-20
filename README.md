README.md

プロジェクト概要
- KabuSys は日本株向けの自動売買 / リサーチ基盤の実装スケルトンです。  
  主な機能はシグナル → ポートフォリオ構築 → 発注（ExecutionEngine）と、運用中の監視（Monitoring）およびリサーチ / AI 換算のユーティリティ群です。
- 設計方針の要点:
  - 本番・ペーパートレードを環境変数で切替可能（KABUSYS_ENV）。
  - DB は DuckDB（時系列・リサーチ）と SQLite（監視・発注ログ）を併用。
  - ロギング・プロセス優先度・Kill Switch 等の運用機能を標準提供。
  - LLM (OpenAI) を用いたニュース NLP / レジーム検出機能を備える（環境変数 OPENAI_API_KEY 必須）。

主な機能一覧
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading 時は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離。
  - プロセス優先度設定、PID 管理、停止フラグ検出（data/stop_requested.flag）を実施。
- Monitoring ポーリング（run_monitoring.py）
  - System / Trade / Risk Monitor を定期実行して監視ログを SQLite に永続化。
  - MONITOR_POLL_INTERVAL でポーリング間隔を制御（デフォルト 60 秒）。
  - Kill Switch（リスク条件で data/kill.flag を書き込む）と AlertManager 連携を想定。
- 設定ウィザード（config_setup.py）
  - .env の対話的生成・更新ツール。
- 設定検証ツール（validate_config.py）
  - 必須環境変数や config/*.yaml の存在確認、起動前チェック。
- リサーチ / ポートフォリオ構築
  - ファクター算出（research.calc_momentum / calc_volatility / calc_value 等）。
  - ポートフォリオ構築補助（portfolio.select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。
- AI モジュール
  - news_nlp.score_news: raw_news を集約して OpenAI へ送り銘柄別センチメントスコアを ai_scores に保存。
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM 判定を組み合わせて市場レジーム判定を行い market_regime に書込む。
- 運用ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）。

セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone ...（省略）
2. Python 環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate
3. 依存パッケージをインストール
   - 必要ライブラリ（例）
     - duckdb
     - psutil
     - openai
     - pyyaml（設定ファイル検証時に使用）
   - 例: pip install duckdb psutil openai pyyaml
4. .env を作成
   - 対話式で作る: python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数（デフォルト値や説明）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 時）
     - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
     - OPENAI_API_KEY: OpenAI を使う場合必須
     - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒。run_monitoring 用）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
5. 設定検証
   - python -m kabusys.validate_config
   - 厳格モード: python -m kabusys.validate_config --strict

使い方（コマンド例）
- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を環境変数にセットするとペーパートレードモードで起動（MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録）。
- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring（30秒間隔に変更）
- .env を対話式で作成 / 更新
  - python -m kabusys.config_setup
- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
- AI モジュール（プログラムから呼ぶ）
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="…")

運用上のポイント
- Kill Switch / stop flag
  - risk モニタ等が kill.flag（デフォルト data/kill.flag）を書き込むと ExecutionEngine は停止シグナルを受けられる（起動時 KILL_FLAG_CLEAR_ON_START により自動クリアの制御あり）。
  - 管理者が強制停止したい場合は data/stop_requested.flag を作成すると run_* スクリプトはループを抜けて終了する。
- ログ
  - ログはデフォルト logs/<app_name>.log に日次ローテーションで保存（30日分保持）。
  - ログディレクトリは LOG_DIR 環境変数で変更可能。ディレクトリ作成に失敗するとコンソールのみ出力にフォールバック。
- DB
  - DuckDB: 分析用（prices_daily / raw_financials / raw_news 等）
  - SQLite:
    - monitoring.db: system_status / trade_logs / positions / risk_logs / dashboard（デフォルト SQLITE_PATH）
    - paper_trading.db: ペーパートレード時の発注ログ（PAPER_TRADING_SQLITE_PATH）
- プロセス優先度・CPU affinity
  - 起動時に set_process_priority("high") が呼ばれます。OS によっては設定権限が必要な場合があります。
- OpenAI 利用
  - OPENAI_API_KEY を設定してください。AI 絡みの処理はリトライや失敗時フォールバックが組み込まれていますが、API キー未設定では実行できません。

ディレクトリ構成（主なファイルと役割）
- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 & Settings 管理（自動 .env ロード機能含む）
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前検証ツール
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py — 監視用 SQLite の永続化層
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 発注系監視（存在）
    - risk_monitor.py — ドローダウン / ポジション数監視
    - kill_switch.py — kill.flag 管理
    - monitoring_engine.py — 各 Monitor を束ねる
    - alert_manager.py — アラート送信ロジック（存在）
  - execution/ (発注系; 実装ファイル多数)
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, broker_factory.py, risk_manager.py, ...
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・上限処理
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + ETF MA）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成

補足
- .env は決してリポジトリにコミットしないこと（config_setup にも注意書きが入っています）。
- 開発 / テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効にできます。
- config/*.yaml（system_config.yaml 等）は運用設定用に用意されていますが、未作成時は validate_config が警告を出します。サンプルは scripts/generate_config.py（存在する場合）で生成可能。

以上が本リポジトリの概要と基本的な使い方です。必要に応じて各モジュール内の docstring や関数コメントを参照してください。