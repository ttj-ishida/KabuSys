# KabuSys

日本株向け自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、売買ロジック、リスク管理、監視、研究用ユーティリティ、AI を利用したニュース分析などを含む自動売買フレームワークの一部です。各モジュールは可能な限り副作用を抑え、テストしやすい純粋関数 / 小さなクラスに分割されています。

## 概要

- ExecutionEngine: 発注処理・リスク制御・オーダー管理を行う起動スクリプト/エンジン
- Monitoring: システム稼働監視、トレード監視、リスク監視、Kill Switch（停止フラグ）管理
- Portfolio: 銘柄選定・ウェイト計算・ポジションサイズ計算・セクター制約などの純粋関数群
- Research: DuckDB を使ったファクター計算・特徴量解析ユーティリティ
- AI: OpenAI を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）
- Tools: Paper Trading 検証レポート生成などのユーティリティスクリプト
- Utils: ロギングセットアップ、プロセス優先度設定など共通ユーティリティ

## 主な機能一覧

- .env ウィザード（対話式）で環境変数ファイルを生成・編集
  - コマンド: python -m kabusys.config_setup
- 起動前設定検証（ENV / config yaml 等のチェック）
  - コマンド: python -m kabusys.validate_config [--strict]
- Execution エンジン起動（本番 / ペーパートレード対応）
  - コマンド: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に分離記録
- Monitoring 起動（ポーリングループ）
  - コマンド: python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
- News NLP（OpenAI）を用いた銘柄別センチメントスコア生成
  - API: kabusys.ai.score_news
  - OPENAI_API_KEY を環境変数で指定
- 市場レジーム判定（AI + ETF MA を組み合わせる）
  - API: kabusys.ai.regime_detector.score_regime
- Paper Trading 検証レポート生成
  - コマンド: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
- DuckDB を用いたファクター計算（momentum / volatility / value 等）
  - API: kabusys.research.calc_momentum / calc_volatility / calc_value
- ポートフォリオ構築 / ポジションサイズ計算
  - API: kabusys.portfolio.select_candidates / calc_equal_weights / calc_score_weights / calc_position_sizes / apply_sector_cap / calc_regime_multiplier

## セットアップ手順

前提: Python 3.10 以上（| 型注釈、match などを使わないが union | 型を使用しているため 3.10+ を推奨）

1. リポジトリをチェックアウト
2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または .venv\Scripts\activate（Windows）
3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - 追加（任意 / 機能による）: PyYAML（config 検証で YAML をパースする場合）
     - pip install pyyaml
   - その他、サンプル実装で使われるパッケージがある場合は適宜追加してください
4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（.env.example を参照してください）
5. 設定検証
   - python -m kabusys.validate_config
   - 必須環境変数（最低）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な環境変数の例（デフォルト値があるものは括弧内に示します）:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - DUCKDB_PATH (data/kabusys.duckdb)
     - SQLITE_PATH (data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
     - LOG_LEVEL (INFO)
     - OPENAI_API_KEY （AI 機能を使う場合必須）

ディレクトリ・ファイルに対してアプリが書き込みを行うため、data/ や logs/ の書き込み権限を確認してください（setup_logging が logs/ を作成します）。

## 使い方（起動例）

- ExecutionEngine を起動（本番 / ペーパー制御は KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 停止シグナル:
    - Monitoring / 外部からエンジンを停止する場合は data/kill.flag を作成（KillSwitch 機能）
    - run_execution は data/stop_requested.flag の存在を検知して停止する実装が入っています（プロジェクトルートの data/stop_requested.flag）
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可能）

- Monitoring を起動（ポーリングで状態を収集）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を指定（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は本番 sqlite_path を使用（環境にかかわらず同じ DB を利用）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で別パスを指定可能（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可）

- コンフィグ作成・検証
  - python -m kabusys.config_setup
  - python -m kabusys.validate_config [--strict]

- ライブラリとしての利用例（Python スクリプト内）
  - from kabusys.research import calc_momentum
  - from kabusys.ai import score_news
  - from kabusys.portfolio import calc_position_sizes

## 監視・停止仕組み

- run_monitoring / MonitoringEngine は定期的に SystemMonitor / TradeMonitor / RiskMonitor を呼び出します。
- KillSwitch は RiskMonitor 等の結果に基づき data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送ります。
- すべてのループ起動スクリプトはプロジェクトルートの data/stop_requested.flag を検知して安全に終了するようになっています。
- ログ:
  - デフォルトログディレクトリ: logs/
  - ログファイル名: <app_name>.log（例: logs/execution.log, logs/monitoring.log）
  - 日次ローテーション・最大 30 日保管（TimedRotatingFileHandler）

## 環境変数まとめ（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API を使う機能で必要
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

.config_setup ウィザードで主要変数は対話的に設定できます。

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py — パッケージ定義（__version__）
  - config.py — 環境変数 / Settings 管理、.env 自動読み込みロジック
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングスクリプト
  - utils/
    - logging_setup.py — ロギング設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - execution/  (エンジン内部はここに配置される想定)
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py — SQLite ベースの監視データ永続化
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（滞留・異常約定等）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — Kill Switch（kill.flag の書き込み / クリア）
    - monitoring_engine.py — 各モニタを束ねる
    - alert_manager.py — LINE 等への通知（実装に応じて）
  - portfolio/
    - portfolio_builder.py — 候補選定 / ウェイト計算
    - position_sizing.py — 発注株数計算
    - risk_adjustment.py — セクター制約 / レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value 等の計算（DuckDB）
    - feature_exploration.py — forward returns / IC / summary
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコア化して ai_scores に書き込む
    - regime_detector.py — ETF MA + マクロニュースでレジーム判定
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト
  - data/ (ランタイムで作成される想定)
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード時）
    - kill.flag / stop_requested.flag / execution.pid など

※ 上記は主要ファイルのみ抜粋しています。実際の実装ファイル群はさらに細分化されています。

## 運用上の注意

- KABUSYS_ENV=live の場合は本番環境です。LINE の通知設定や kill flag のクリア設定等を慎重に扱ってください（validate_config にて live 用の警告を出します）。
- .env ファイルは決してバージョン管理にコミットしないでください（config_setup のヘッダにも記載）。
- OpenAI を利用する機能は API 利用料が発生します。利用頻度やバッチサイズに注意してください。
- DuckDB / SQLite のファイルパスは適切なバックアップ・ディスク容量管理を行ってください。monitoring は本番 sqlite_path を参照する実装があるため、監視 DB の扱いに注意してください。
- プロセス優先度変更や CPU affinity 設定は環境によって権限が必要です。設定に失敗してもワーニングで継続します。

---

この README はコードベースの主要な使い方と構成をまとめたものです。より詳細なドキュメント（設計書、PortfolioConstruction.md、StrategyModel.md 等）がある場合は併せて参照してください。必要であれば、README にサンプル .env テンプレートや起動のフルワークフロー（cron / systemd 例）を追加します。