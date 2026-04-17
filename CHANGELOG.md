# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このファイルはリポジトリ内の現行コードベースから推測して作成した変更履歴です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-17

初期リリース。主要な機能・CLI・ユーティリティ群を実装。

### Added
- 基本情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 実行エントリポイント
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 停止フラグ（data/stop_requested.flag）を検出して安全にループを終了。
    - 監視は常に本番用の sqlite_path を使用する（環境に依存しない）。
    - 起動時にプロセス優先度を High に設定する処理を追加。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を利用して paper_trading 用の専用 SQLite（data/paper_trading.db、`PAPER_TRADING_SQLITE_PATH` で変更可）を使用し、本番 DB と分離。
    - 起動前に停止フラグ (data/stop_requested.flag) を確認。運転中に停止フラグを検知すると Engine を停止。
    - 起動時にプロセス優先度を High に設定する処理を追加。
    - ExecutionEngine の PID 管理用ファイル（data/execution.pid）を利用。

- 設定管理・支援ツール
  - config.py
    - 環境変数読み込み・管理クラス `Settings` を実装。多くの設定値（DB パス、API トークン、監視閾値、環境種別など）をプロパティとして提供。
    - 自動 .env ロード機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースはシングル/ダブルクォート、エスケープ、コメント等に柔軟に対応。
    - `PAPER_FILL_MODE` のバリデーションを実装（有効値: instant|partial|never|reject）。
    - `KABUSYS_ENV`/`LOG_LEVEL` 等の妥当性チェックを実装（不正値で例外を発生）。

  - config_setup.py
    - .env の対話式ウィザードを実装。既存 .env 読み込み、ユーザー入力、確認後にファイル書き込み。
    - 各種設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DB パス等）をサポート。
    - シークレット項目はマスク表示、オプション項目は空でスキップ可能。

  - validate_config.py
    - 起動前検証 CLI を追加。
    - 必須環境変数未設定チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML が存在する場合）を実行。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定未設定、KILL_FLAG_CLEAR_ON_START が 1 の警告等）を実装。
    - `--strict` オプションで警告も FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - BUY シグナルの候補選定（スコア降順、タイブレークに signal_rank）。
    - 等金額配分（calc_equal_weights）／スコア加重配分（calc_score_weights）。全スコアが 0 の場合は等金額にフォールバック。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap（当日売却予定銘柄の除外や "unknown" セクターの扱いを明記）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバックで警告）。

  - portfolio/position_sizing.py
    - 発注株数算出ロジック calc_position_sizes を実装。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株丸め（lot_size）、1 銘柄上限・aggregate cap、cost_buffer（手数料・スリッページ見積）を考慮したスケーリングロジックを実装。
    - 価格欠損時のスキップ、logging によるデバッグ情報を提供。

- ユーティリティ
  - utils/process_priority.py
    - プラットフォーム差分を吸収したプロセス優先度設定 set_process_priority(level) を実装（Windows/Linux/Mac 等に対応）。
    - CPU affinity を設定する set_cpu_affinity(cpu_count) を実装（指定が None の場合は何もしない）。
    - 権限不足や未対応環境時に警告を出して安全にスキップ。

- リサーチ / ファクター計算
  - research/factor_research.py
    - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルから複数のファクター（モメンタム、MA200 乖離、ATR、平均出来高等）を計算する関数群（calc_momentum, calc_volatility 等）を実装。
    - P95 等の集計計算用の補助ロジックを含む。欠損データ時の取り扱い（None）を明記。

- ツール
  - tools/paper_verification_report.py
    - ペーパートレード結果検証レポートを生成する CLI を追加。
    - デフォルト DB パスは `data/paper_trading.db`（環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で上書き可）。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ 等。
    - 判定基準（閾値）：稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 latency <= 200 ms。
    - 期間フィルタ（--from, --to）をサポート。

- DB 初期化
  - monitoring/monitoring_db.init_monitoring_db を run_* スクリプトから呼び出して、監視テーブルが存在することを保証（冪等）。

### Changed
- .env 自動読み込みの挙動
  - プロジェクトルート探索に .git または pyproject.toml を使用するようにして、作業ディレクトリに依存しない自動読み込みを実現。
  - OS 環境変数は protected として .env の上書きを防ぐ（.env.local は override=True だが protected により OS 環境変数を保持）。

- エラーハンドリングの改善
  - 起動スクリプト・各種ユーティリティで例外時に適切にログ出力または警告を行い、全体動作を停止させない動作に変更（例: monitoring loop 内で check_once() が失敗しても続行）。

### Fixed
- 環境変数パーサの堅牢性向上
  - export プレフィックス、クォートされた値、エスケープシーケンス、インラインコメントの扱いなどを改善し、 .env の多様な書式に対応。
- position_sizing のスケーリング時における端数配分ロジックを実装し、残余キャッシュを活用して lot_size 単位で再配分するように修正。

### Notes / Observations
- 実行系（ExecutionEngine）や BrokerClientFactory、Reconciler、RiskManager 等の内部実装は本変更履歴作成時点のコード断片に依存しており、詳細は別モジュール（src/kabusys/execution/*）の実装を参照してください。
- monitoring は常に本番用の sqlite_path を参照する設計となっており、paper_trading 環境でも監視データを本番 DB に書き込む点に注意（run_execution は paper_trading の場合 DB を分離する）。
- 一部関数で将来の拡張（銘柄ごとの lot_size マッピングや価格フォールバック等）が TODO コメントとして残されています。

---

この CHANGELOG はコードベースの内容から推測して作成したものであり、実際のコミット履歴やプロジェクト運用上の変更履歴と完全に一致しない場合があります。必要であれば特定ファイルごとにより詳しい注記を追加します。