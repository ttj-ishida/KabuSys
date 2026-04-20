# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
このファイルはコードベースから推測して生成された初期の変更履歴です（実際のコミット履歴ではありません）。

## [Unreleased]

- なし

## [0.1.0] - 2026-04-20

初回公開リリース。プロジェクトのコア機能（起動スクリプト、設定管理、ログ/プロセスユーティリティ、ポートフォリオ構築ロジック、検証ツール、レポート生成など）を追加。

### Added

- 一般
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージのモジュール公開 (`__all__`) を設定。

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト直下の `data/stop_requested.flag` によって検知。
    - Monitoring は環境（KABUSYS_ENV）に関わらず本番用 `sqlite_path` を使用する設計。
    - DB 初期化（監視用テーブル）および DuckDB 接続を行う。
    - 例外発生時にログ出力して次ポーリングにフォールバック。

  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）。
    - プロセス優先度設定、監視フラグによる停止、PID ファイル管理、スレッド実行/停止ロジックを備える。

- 設定関連
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml 基準）。
    - `.env` / `.env.local` の読み込み順と OS 環境変数保護（上書き制御）を実装。
    - 複雑な .env パーサを実装（export プレフィックス、クォート内エスケープ、インラインコメント処理などに対応）。
    - Settings クラスを提供し、アプリケーション設定を環境変数から提供（DB パス、API トークン、Paper Trading 設定、監視閾値等）。
    - `paper_fill_mode` の検証（有効値制約）。
    - 環境種別チェック（development / paper_trading / live）とログレベル検証。
    - `settings` インスタンスをエクスポート。

  - config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装。
    - デフォルト値・選択肢・機密入力マスク表示・保存確認を実装。
    - `.env` 書き込みテンプレートを提供（書き込み時に Git にコミットしないよう注意喚起）。

  - validate_config.py
    - 起動前チェック CLI を追加（必須環境変数、KABUSYS_ENV の妥当性、DB パス、config/*.yaml の存在とパース、live 環境でのガード等）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ログ / プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次回転）を設定するユーティリティ `setup_logging` を追加。
    - ログディレクトリ作成のフォールバック処理、既存ハンドラのクリーンアップ、レベル解決ロジックを実装。
    - stdout を使用することで cron 等でリダイレクトしやすい設計。

  - utils/process_priority.py
    - マルチプラットフォーム対応のプロセス優先度設定 `set_process_priority` と CPU affinity 設定 `set_cpu_affinity` を追加。
    - Windows/Linux/macOS 等の差分を吸収し、権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 `select_candidates`（スコア降順、タイブレーク: signal_rank）。
    - 等分配 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等分にフォールバック）。

  - portfolio/risk_adjustment.py
    - セクター集中制限適用 `apply_sector_cap`（既存ポジションのセクター別時価を算出して候補をフィルタ）。
    - 市場レジームに応じた乗数 `calc_regime_multiplier`（bull/neutral/bear をマップ、未知値は警告とフォールバック）。

  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出関数 `calc_position_sizes` を追加。
    - `risk_based`, `equal`, `score` の割当方式をサポート。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、コストバッファを考慮したスケーリングロジックを実装。
    - 端数処理で fractional remainder に基づく追加配分ロジックを実装。

  - portfolio/__init__.py で主要 API をエクスポート。

- リサーチ / ファクター
  - research/factor_research.py
    - DuckDB 接続を受けてファクター（Momentum、Value、Volatility、Liquidity）を計算するモジュールを追加。
    - モメンタム計算関数 `calc_momentum` 等の骨組みを実装（営業日ベースのウィンドウ、MA200 乖離、1m/3m/6m など）。
    - （注）ファイル末尾で実装が途中の箇所がある（後述の Known issues を参照）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成ツールを追加。
    - 検証指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ、リスク却下数。
    - 判定基準（しきい値）を定義し、PASS/FAIL を出力。
    - DB パスのオーバーライド（環境変数または --db）に対応。

- 監視 DB
  - monitoring.monitoring_db.init_monitoring_db を参照して、起動時に監視テーブルの存在を保証（冪等に初期化）。

### Changed

- なし（初回リリースとして機能追加中心）

### Fixed

- なし（初回リリース）

### Removed

- なし

### Security

- .env ファイルは絶対にリポジトリにコミットしないよう .env 作成テンプレートやウィザードで注意喚起。

### Notes / Known issues / TODO

- research/factor_research.py の末尾が途中（ファイルに "start_da" で途切れている）であり、関数実装が未完了の可能性がある。将来的に完全なファクター計算ロジックの実装が必要。
- portfolio/risk_adjustment.apply_sector_cap 内で price が欠損（0.0）の場合に露出が過少見積もられる旨の TODO コメント。前日終値などのフォールバック価格導入が検討課題。
- position_sizing.calc_position_sizes は将来的に銘柄別の lot_size 対応を想定した TODO コメントあり（現状は全銘柄共通 lot_size）。
- run_monitoring の設計上、Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照するため、テスト時の DB 分離に注意が必要（意図的な設計）。
- process_priority / set_cpu_affinity は権限不足や未対応 OS の場合に動作しないことがある（警告でスキップ）。
- ログディレクトリ作成失敗時はファイル出力を無効化してコンソール出力のみで継続する。

---

この CHANGELOG はコードの静的解析とドキュメンテーション文字列から推測して生成しています。実際のコミットメッセージや差分に基づく正確な履歴が必要な場合は、Git の履歴から CHANGELOG を生成してください。