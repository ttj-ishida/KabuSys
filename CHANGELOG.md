CHANGELOG
=========

すべての重要な変更履歴を記録します（Keep a Changelog 準拠）。
初回リリース（コードベースから推測した機能群）をまとめています。

[0.1.0] - 2026-04-23
-------------------

### Added
- 全体
  - パッケージ初期版を追加。バージョンは __version__ = "0.1.0"（src/kabusys/__init__.py）。
  - プロジェクトルート検出および .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - .env / .env.local を OS 環境変数と衝突しないように読み込む。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。
    - 環境変数パースはクォート・エスケープ・インラインコメントに対応。
  - Settings クラスによる集中設定管理を追加（src/kabusys/config.py）。
    - 環境（KABUSYS_ENV）、DB パス（DUCKDB_PATH / SQLITE_PATH）、Paper Trading 設定、監視しきい値等のプロパティを提供。
    - PAPER_FILL_MODE のバリデーション（"instant" / "partial" / "never" / "reject"）を実装。

- 起動スクリプト / 実行
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は Paper Trading 用 SQLite（data/paper_trading.db など）を使用し、本番 DB と分離。
    - BrokerClientFactory を経由したブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を利用した安全な停止処理を実装。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化。

- 設定ツール / 検証
  - 対話式 .env 作成ウィザードを実装（src/kabusys/config_setup.py）。
    - 複数の設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を案内して .env を生成。
  - 起動前設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ有無、config/*.yaml の存在・パース検証（PyYAML があれば内容検証）を実行。
    - --strict モードで警告もエラー扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - コンソール (stdout) 出力用 StreamHandler と 日次ローテートの TimedRotatingFileHandler（デフォルト logs/ ディレクトリ、30 日保持）を設定。
    - LOG_LEVEL / LOG_DIR 引数・環境変数対応。ディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収して優先度設定（high/normal/low）を提供。CPU affinity 固定機能も提供。権限不足や未サポート環境では警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順＋タイブレークロジック
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコアが全て 0 の場合は等配分へフォールバック）
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有セクター比率が閾値を超える場合に新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた資金乗数を返す（未知レジームは警告後 1.0 でフォールバック）
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - allocation_method ("risk_based", "equal", "score") に基づく発注株数計算
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的見積り
    - スケールダウン時の再配分における残差取り扱い（fractional remainder）を考慮

- Paper Trading 検証ツール
  - Paper Trading の検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計し、PASS/FAIL 判定を出力。
    - デフォルト DB パスは data/paper_trading.db。--db オプション／PAPER_TRADING_SQLITE_PATH 環境変数で上書き可。

- 研究用ファクター計算（基礎）
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Value / Volatility / Liquidity 等の設計方針と定数を定義。DuckDB を利用して prices_daily / raw_financials を参照する設計。
    - （ファイル終端が途中のため、一部実装未完）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Known issues
- position_sizing の価格欠損処理に関する TODO があり、price が 0.0 の場合にエクスポージャーが過少評価される可能性がコメントで示されている（src/kabusys/portfolio/risk_adjustment.py）。
- factor_research.py はファイル末尾で途中（"start_da" のような未完のコード断片が存在）になっており、完全な実装は未提供。
- .env の書き出しテンプレートと自動読み込みは用意されているが、ユーザーは .env を絶対にリポジトリにコミットしないことに注意。
- 実際の発注処理やブローカークライアントの実装は BrokerClientFactory / ExecutionEngine 側に依存しており、Paper vs Live の動作分離は設定に依存する（安全運用のため validate_config や Kill Switch の設定推奨）。

この CHANGELOG は、提供されているコードの内容から推測して作成しています。実際のリリースノートや変更履歴を作成する際は、コミット履歴やリリース担当者の確認に基づいて補正してください。