# CHANGELOG

すべての非互換性のある変更はメジャーバージョンをインクリメントしてください。  
このファイルは Keep a Changelog の形式に準拠しています。  

- リリース日やエントリはコードベースから推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-18

Added
- プロジェクト初期実装を追加。
  - パッケージ情報:
    - バージョン: `kabusys.__version__ = "0.1.0"`（src/kabusys/__init__.py）
- 実行スクリプト:
  - run_execution.py: ExecutionEngine 起動用エントリポイントを追加。
    - KABUSYS_ENV による paper_trading モードをサポートし、paper_trading 時は専用の SQLite（data/paper_trading.db、環境変数で上書き可）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動・停止ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）検出、PID ファイル出力（data/execution.pid）処理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視コンポーネントは環境にかかわらず本番用 sqlite_path を使用する設計。
    - 停止フラグ検出でループを終了、例外捕捉とログ出力で安定稼働を図る。
- 設定管理:
  - config.py:
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
    - .env パース機能を強化（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理をサポート）。
    - 環境変数のラッパー `Settings` クラスを実装（各種パス、閾値、env 判定、paper_trading のパラメータ検証等）。
    - PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - config_setup.py:
    - 対話式ウィザードで .env を初期作成・更新する CLI を実装。
    - デフォルト値表示・シークレットマスク・入力検証を行い .env を安全に出力。
  - validate_config.py:
    - 起動前チェック用 CLI を実装（必須環境変数チェック、KABUSYS_ENV 検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パース検証（PyYAML がインストールされていない場合はスキップ）、本番環境向けガードチェック）。
    - --strict オプションで警告をエラー扱いにできる。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py:
    - 信号の候補選定（スコア降順、タイブレークに signal_rank）select_candidates。
    - 等金額配分 calc_equal_weights、スコア比率配分 calc_score_weights（全銘柄スコアが 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py:
    - sector cap 適用: セクター集中を抑える apply_sector_cap（unknown セクターは無視）。
    - レジームに応じた投資乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をサポート。未知レジームはフォールバックで 1.0）。
  - portfolio/position_sizing.py:
    - 資金配分・株数算出 calc_position_sizes を実装。
      - risk_based / equal / score の allocation_method をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限・aggregate cap（available_cash 超過時のスケールダウン）を実装。
      - cost_buffer により手数料・スリッページの保守的見積りを考慮。
      - いくつかの設計上の TODO（銘柄別 lot_size など）を注記。
- ユーティリティ:
  - utils/logging_setup.py:
    - アプリ共通のロギング設定ユーティリティを実装。
    - stdout 出力用 StreamHandler と 日次ローテーションの TimedRotatingFileHandler（既定 logs/ ディレクトリ、環境変数 LOG_DIR で変更可）を設定。
    - 既存ハンドラのクリア、ログレベルの解決順（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみへフォールバック。
  - utils/process_priority.py:
    - クロスプラットフォームでのプロセス優先度設定（Windows / POSIX 系の差分を吸収）。
    - CPU affinity 設定関数 set_cpu_affinity を実装（指定コア数にプロセスを固定）。
    - 権限不足や未対応プラットフォームでは警告ログを出して安全にスキップ。
- 監視・モニタリング:
  - monitoring 側の DB 初期化呼び出し（init_monitoring_db）を実行スクリプトに統合（冪等に監視テーブルを保証）。
  - SystemMonitor/monitoring_db 等の利用を想定した起動ロジックを実装。
- DuckDB / SQLite 統合:
  - データ処理向けに duckdb 接続を各処理で利用する設計を採用（duckdb_path の設定）。
  - 監視や execution 用に sqlite 接続を使用（環境ごとの sqlite_path 切替をサポート）。
- ツール:
  - tools/paper_verification_report.py:
    - ペーパートレーディング結果の検証レポート生成ツールを実装。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）等を計算して PASS/FAIL 判定を行う。
    - コマンドラインで期間（--from/--to）や DB パス（--db、環境変数 PAPER_TRADING_SQLITE_PATH）を指定可能。
- リサーチ:
  - research/factor_research.py:
    - ファクター計算モジュールの骨子を実装（Momentum / Value / Volatility / Liquidity に対応予定）。
    - DuckDB の prices_daily / raw_financials を参照する設計。関数 calc_momentum の実装開始（ファイル末尾で一部切れているが設計意図を実装）。

Changed
- N/A（初期リリース）

Fixed
- .env の読み込み仕様を堅牢化:
  - export 句対応、クォート内エスケープ処理、コメント扱いの改善。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env.local を優先して読み込み、OS 環境変数の上書きを保護する仕組みを実装。

Security
- .env の生成スクリプトで「.env を絶対に Git にコミットしないこと」の注意書きを出力。
- 設定検証で本番環境（KABUSYS_ENV=live）向けの警告（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START 設定）を追加。

Notes / Known issues / TODO
- portfolio.position_sizing: 銘柄別単元（lot_size）を将来的にマスタ化する旨の TODO を記載。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性を指摘するコメントあり。
- research.factor_research.py は計算ロジックの実装途中でファイル末尾が切れているため、完全実装が必要。
- ExecutionEngine / SystemMonitor の内部実装（詳細な engine/reconciler/risk manager のロジック）はこのバージョンの外側で別モジュールに分かれており、実装依存の動作確認が必要。

コマンド例
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- 実行スクリプト:
  - python -m kabusys.run_execution
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上。