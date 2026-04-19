Keep a Changelog 準拠 — CHANGELOG.md (日本語)
==========================================

すべての変更は semver に従って管理します。  
このファイルはリポジトリのコードから推測して作成しています。実際のリリースノート作成時は差分を確認のうえ適宜修正してください。

v0.1.0 - 2026-04-19
-------------------

Added
- 基本アプリケーション構成とエントリポイントを追加
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。
  - エントリスクリプト:
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用。停止は data/stop_requested.flag を監視して行う。
    - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading に応じて paper_trading 用の専用 SQLite DB（data/paper_trading.db）と MockBrokerClient を使用して本番 DB と完全分離。プロセスの PID 管理・停止フラグ検出を実装。

- 環境設定・読み込み関連
  - config.py:
    - .env/.env.local の自動読み込み機能（OS 環境変数優先）。プロジェクトルートを .git または pyproject.toml から探索して自動ロード。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。
    - .env 行パーサの実装（export プレフィックス、クォート／エスケープ、インラインコメント処理をサポート）。
    - 各種設定プロパティを提供（J-Quants / kabu API / LINE / DuckDB / SQLite / PaperTrading 用パス / 監視閾値等）。設定値のバリデーション（env 値や PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の検証）。
    - settings = Settings() をエクスポート。

  - config_setup.py: 対話式ウィザードにより .env の生成・更新が可能。既存 .env 読込、シークレットマスキング、選択肢提示、書き込みテンプレートを提供。

  - validate_config.py: 起動前チェック CLI。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL 検証、DB パス親ディレクトリ確認、config/*.yaml の存在および PyYAML がある場合はパース検証、本番環境向けガード（LINE 通知設定、KILL_FLAG_CLEAR_ON_START の確認）など。--strict オプションで警告も失敗扱いにできる。

- 実行・監視用ユーティリティ
  - utils/logging_setup.py:
    - 一貫したログ設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリの作成失敗時はファイル出力をスキップしてコンソールのみで継続。ログレベル/ログディレクトリの優先順位を明示。
  - utils/process_priority.py:
    - クロスプラットフォームでプロセス優先度設定を行うユーティリティを追加（Windows の priority class、POSIX の nice）。AccessDenied 等の例外はワーニングで無害に扱う。CPU affinity を最初の N コアに固定する set_cpu_affinity も提供。

- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順で候補選択、同スコア時の tie-break に signal_rank を使用。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア合計が 0 の場合は等配分へフォールバック、警告出力）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、設定上限を超えるセクターの候補を除外（"unknown" セクターは除外対象外）。sell_codes を除外して当日売却予定銘柄を計算から除く機能あり。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームはフォールバックで 1.0 を返し警告。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method により発注株数を算出（risk_based / equal / score をサポート）。リスクベースではリスク許容率・ストップロスを用いた株数算出、単元株（lot_size）丸め、1 銘柄上限・aggregate cap、cost_buffer を考慮したスケーリングと端数処理（残余キャッシュでの追加配分）を実装。

- 分析・検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成スクリプトを追加。SQLite（PAPER_TRADING_SQLITE_PATH）から各種指標（稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数）を集計し、閾値に対する PASS/FAIL 判定を出力。期間フィルタ（--from/--to）および DB パス指定（--db）をサポート。P95 計算、N/A 表示、DB が存在しない場合のエラーメッセージを実装。

- データ研究モジュール（下地）
  - research/factor_research.py:
    - ファクター計算モジュールの骨子を追加。Momentum/Value/Volatility/Liquidity 系ファクターに関する設計方針、定数、calc_momentum の実装開始（prices_daily テーブル利用、MA200、1/3/6 ヶ月リターン等）。（注: ファイル末尾で calc_momentum の実装が途中で終わっているため一部実装中）

Changed
- DB 周りの振る舞いの明示化
  - 監視プロセス（run_monitoring）は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用する仕様に明示。
  - 実行エンジン（run_execution）は KABUSYS_ENV=paper_trading の場合、paper_sqlite_path（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使い本番 DB と分離。

- ログ出力設計
  - ログは stdout に出力しつつファイルに日次ローテーションで保存。ログディレクトリ作成失敗時はファイル出力をフォールバック。

Fixed
- 環境変数パースの堅牢化
  - .env パーサで export プレフィックスやクォート中のバックスラッシュエスケープ、インラインコメント処理をサポート。無効行は無視。
  - MONITOR_POLL_INTERVAL の異常値（0 以下や非整数）に対してデフォルト値へフォールバックしワーニングを出力するように改良。

Notes / Known issues
- research/factor_research.py の calc_momentum が途中で終わっており、ファクター計算モジュールは一部未完成。詳細な計算・テストは今後の実装が必要。
- 一部の実行コンポーネント（BrokerClientFactory、ExecutionEngine、OrderManager、Reconciler、RiskManager 等）はこの差分内で参照されているが実装ファイルはこの一覧に含まれていない（別ファイルで実装済みの想定）。実際に起動する場合はそれらの実装とインターフェースの整合性を確認してください。
- process_priority の優先度設定や CPU affinity は実行環境の権限によって AccessDenied などが発生する可能性があり、その場合はワーニングを出して処理を継続する設計です。

開発者向けメモ（推奨）
- factor_research の残り実装と単体テストを追加する。
- CLI スクリプト（run_execution/run_monitoring）のユニットテストおよび統合テストを追加し、stop フラグ・PIDファイル・DB 初期化の挙動を検証する。
- config_setup/validate_config の出力を CI で活用し、設定ミスを自動検出することを推奨。

（以上）