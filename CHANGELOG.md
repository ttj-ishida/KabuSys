# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠し、慣例に従ってセマンティックバージョニングを使用します。

- リリース日に関しては、コードベースの現状から初回公開バージョンとして記載しています。
- 記載内容はソースコードから推測してまとめたものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

（現在差分はありません）

---

## [0.1.0] - 2026-04-21

初回リリース。日本株自動売買システム「KabuSys」の基本コンポーネントを実装。

### Added
- 基本設定/環境変数管理
  - Settings クラス（kabusys.config）を実装。環境変数から各種設定（J-Quants / kabu API / DB パス /監視閾値 / 実行環境など）を取得するプロパティを提供。
  - .env 自動読み込み機能を追加（プロジェクトルートの検出: .git または pyproject.toml を基準）。`.env` / `.env.local` の読み込み順・上書きルールを実装。自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env パースは export KEY=val 形式やクォート・エスケープ・インラインコメントに対応。

- 設定関連 CLI
  - 対話式設定ウィザード（kabusys.config_setup）を追加。`.env` の初期作成・更新を支援するウィザードを実装。
  - 設定検証ツール（kabusys.validate_config）を追加。必須環境変数、KABUSYS_ENV 値、LOG_LEVEL、DB パスや config/*.yaml の存在・パースのチェック、および本番時の注意喚起（LINE 設定や KILL_FLAG_CLEAR_ON_START）を行う。

- 実行/監視プロセス起動スクリプト
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）を実装。
    - プロセス優先度を「high」に設定するユーティリティ呼び出しを行う。
    - Paper Trading 環境時は paper_trading 専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離する設計。
    - BrokerClientFactory によるブローカークライアント生成（paper_trading の場合は MockBrokerClient の利用を想定）。
    - ExecutionEngine をスレッドで起動し、data/stop_requested.flag を検知したら安全に停止する仕組みを実装。PID ファイル管理（data/execution.pid）。
  - SystemMonitor 起動スクリプト（kabusys.run_monitoring）を実装。
    - 監視ループを実行し、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、不正値は警告してデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、KeyboardInterrupt に対応。

- DB / モニタリング初期化
  - init_monitoring_db 呼び出しを行い、監視用テーブルの存在を保証（冪等に初期化）。

- ロギングとプロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ（kabusys.utils.logging_setup）を追加。
    - コンソール出力（stdout）用 StreamHandler、日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順に対応。既存ハンドラはクリアしてから再設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップして警告を出す堅牢性を実装。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加。
    - Windows / POSIX の差を吸収してカレントプロセスの優先度を設定（"high" / "normal" / "low"）。
    - CPU affinity を最初の N コアにピン留めする機能も提供。アクセス権限不足等は警告してスキップ。

- ポートフォリオ構築（純粋関数群）
  - portfolio.builder: 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を追加。
    - calc_score_weights は全スコアが 0 の場合に等金額配分にフォールバックし警告を出力。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジームによる投下資金乗数）を追加。
    - apply_sector_cap は当日売却予定銘柄を除外して既存エクスポージャーを計算。unknown セクターは上限適用除外。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" をサポートし、未知の値は警告の上 1.0 にフォールバック。
  - portfolio.position_sizing: calc_position_sizes を追加。
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）、コストバッファ（cost_buffer）を考慮した aggregate cap スケールダウンを実装。
    - 価格欠損時はスキップする堅牢性、スケーリング時の残差配分ロジックを実装。

- リサーチ / ファクター計算（骨組み）
  - research.factor_research にモメンタム等のファクター計算モジュールの骨組みを追加（DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照する設計）。
  - 期日ベースの窓長や ATR / MA 等の定数を定義（実装途中の関数あり）。

- Paper Trading 検証ツール
  - tools.paper_verification_report を追加。Paper Trading の SQLite（PAPER_TRADING_SQLITE_PATH）から指標を集計し、稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）をレポート出力。閾値による PASS/FAIL 判定を実装。期間フィルタ（--from/--to）をサポート。

- パッケージ情報
  - パッケージルートに __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため変更履歴はなし）

### Fixed
- （初回リリースのため修正履歴はなし）

### Notes / Known issues / TODO
- position_sizing の価格欠損時に前日終値等のフォールバックが未実装（TODO コメントあり）。これにより価格データ欠損時にエクスポージャーが過小評価される可能性あり。
- research.factor_research 内の関数は実装の途中（コード末尾で途中切れの状態があるため、完全実装が必要）。
- ロギング用ファイルハンドラ作成やプロセス優先度設定は環境によって失敗する可能性があり、その場合は警告を出してフォールバックする設計。
- .env は機密情報を含むため Git 管理から除外するようウィザード内に注意書きあり。

### Security
- 機密値（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）は .env に保存する想定。`.env` の取り扱いに注意すること。

---

著者: KabuSys 開発チーム（ソースコードから自動生成された CHANGELOG）
- 参考: ソース内ドキュメント、CLI ヘルプ、コードコメントに基づき作成。