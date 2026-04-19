# CHANGELOG

すべての重要な変更点はこのファイルに記録します。本プロジェクトは Keep a Changelog の慣習に準拠します。

- フォーマット: https://keepachangelog.com/ja/1.0.0/
- 版管理: Semantic Versioning に準拠します（MAJOR.MINOR.PATCH）。

## [0.1.0] - 2026-04-19

初回リリース。本リリースでは自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、環境設定ツールおよび検証ツールを実装しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。

- 環境設定・ロード
  - Settings クラス（`kabusys.config`）を実装。環境変数の取得・検証をラップ。
  - 自動 .env ロード機能（プロジェクトルート検出：.git または pyproject.toml を探索）。
  - .env パース機構（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）を実装。
  - 環境変数の必須チェック `_require()`、KABUSYS_ENV / LOG_LEVEL 等の検証ロジックを実装。
  - Paper Trading 用設定（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）をサポートし、不正値検出を実装。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py`
    - ExecutionEngine の起動フローを実装（プロセス優先度設定、DB 接続、BrokerClientFactory の生成、OrderManager / RiskManager / Reconciler の組み立て）。
    - KABUSYS_ENV=paper_trading 時は paper 用 SQLite を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理を実装。
  - 監視ループ起動スクリプト `run_monitoring.py`
    - SystemMonitor の初期化とポーリングループを実装。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を参照（設計上の明示的挙動）。

- 監視 DB 初期化
  - `init_monitoring_db` の呼び出しにより、起動時に監視用テーブルの存在を冪等に保証。

- ロギングユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。
    - stdout ストリーム（StreamHandler）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。

- プロセス制御ユーティリティ
  - `kabusys.utils.process_priority` を実装。
    - Windows / POSIX（Linux, macOS 等）に対応した優先度設定（nice / HIGH_PRIORITY_CLASS 等）。
    - CPU affinity 設定関数 `set_cpu_affinity` を実装（最初の N コアに固定、権限不足時は警告してスキップ）。

- ポートフォリオ構築（純関数群）
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 select_candidates（スコア降順、タイブレーク処理）および等金額/スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中制限適用 apply_sector_cap（セクター別エクスポージャ算出、上限超過セクターの候補除外）。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数決定 calc_position_sizes（allocation_method: risk_based / equal / score）。
    - 単元株（lot_size）丸め、per-position および aggregate cap、コストバッファ考慮のスケーリングロジック実装。
    - リスクベース算出（risk_pct, stop_loss_pct）と最大保有比率（max_position_pct, max_utilization）を組み込み。

- 設定ウィザード・検証 CLI
  - `kabusys.config_setup`：対話式ウィザードで .env を作成/更新する CLI を実装（項目定義、既存 .env の読み込み、保存）。
  - `kabusys.validate_config`：.env と config/*.yaml の妥当性検証ツールを実装（必須環境変数チェック、パスの存在確認、PyYAML があれば YAML のパース検証、本番環境向けの追加警告など）。--strict モードをサポート。

- ペーパートレーディング検証ツール
  - `kabusys.tools.paper_verification_report`：Paper Trading 用 SQLite から稼働率、注文成功率、送信率、レイテンシ（P95）等の指標を集計してレポート出力。閾値判定（PASS/FAIL）を行う。
    - デフォルト DB パス: data/paper_trading.db（環境変数 / --db で上書き可）。
    - 日付フィルタ（--from / --to）をサポート。

- リサーチ用ファクター計算（着手）
  - `kabusys.research.factor_research`：DuckDB 経由で prices_daily 等のテーブルを参照する設計。モメンタム等のファクター計算関数を用意（実装の一部が含まれる、続き実装予定）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / Notes
- factor_research モジュールは実装途中（ファイル末尾が切れている/未完の関数あり）。今後のリリースで完了予定。
- apply_sector_cap 内で price が 0.0 の場合にエクスポージャが過小見積もられる可能性がある旨の TODO コメントあり（前日終値等によるフォールバックを検討）。
- position_sizing は現状で全銘柄共通の lot_size（デフォルト 100）を想定している。将来的に銘柄別単元対応を想定する拡張予定（TODO コメントあり）。
- プロセス優先度 / CPU affinity 設定は権限やプラットフォームに依存するため、失敗時は警告ログを出してスキップする設計。
- run_monitoring は設計上「監視は環境にかかわらず本番 sqlite_path を使用する」動作を明示的に行う。運用上の注意を要する。
- ログディレクトリ作成失敗時はファイルログを無効化してコンソール出力のみで動作する。

### Migration / Usage notes
- .env の自動ロードはデフォルトで有効。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用）。
- 設定検証は `python -m kabusys.validate_config` を実行してください。--strict をつけると警告も終了コード 1 として扱います。
- .env を対話で作成する場合は `python -m kabusys.config_setup` を使用してください。
- 実行系 / 監視系はそれぞれ `run_execution.py` / `run_monitoring.py` を直接実行するか、パッケージとしてエントリを用意して起動してください。
- Paper Trading を行う際は KABUSYS_ENV を `paper_trading` に設定すると paper 用 SQLite に記録され、本番 DB と隔離されます。

---

今後の予定（例）
- factor_research の完了（各ファクターの完全実装・テスト）。
- 戦略・実行部の単体テスト追加とエンドツーエンド検証。
- per-stock lot_size 等の細かな拡張と設定項目の追加。