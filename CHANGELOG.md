# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
慣例に従い、主なカテゴリは Added / Changed / Fixed / Deprecated / Removed / Security です。

最新のバージョン: 0.1.0 — 初回公開相当の機能群をまとめたリリースです。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回リリース。KabuSys のコア機能と運用用ツール群を実装しました。

### Added
- 全体
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - 環境設定の自動読み込み機能を実装（.env / .env.local の読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
  - .env ファイルの堅牢なパース実装（シングル/ダブルクォート、export プレフィックス、インラインコメント処理など）。
  - Settings クラスを実装し、環境変数経由の設定取得を明確化（J-Quants / kabuAPI / DB パス / 監視閾値など）。
  - 環境設定ウィザード CLI を実装（python -m kabusys.config_setup）。対話式で .env を生成・更新可能。
  - 設定検証 CLI を実装（python -m kabusys.validate_config）。必須環境変数やファイルの存在・YAML パース検証を実行。
- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db を既定）を使用し、本番 DB と分離。
    - ブローカークライアント生成を BrokerClientFactory 経由で行う（Mock 実装との切替を想定）。
    - ExecutionEngine をスレッドで実行し、data/stop_requested.flag による安全な停止をサポート。実行用 PID ファイルをサポート。
  - SystemMonitor ポーリングループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用する挙動を採用。
    - 停止フラグ（data/stop_requested.flag）を検知してループを抜けるグレースフルシャットダウンを実装。
- データベース / 分析
  - DuckDB を利用するためのパス設定と接続管理（Settings.duckdb_path）。
  - 監視 DB の初期化ユーティリティ呼び出しを導入（init_monitoring_db を起動時に実行して監視テーブルの存在を保証）。
- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順・signal_rank によるタイブレークで上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を実装。全スコアがゼロの場合は等配分にフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存保有のセクター比率が閾値を超える場合、新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数を返す（bull/neutral/bear）。
  - 株数決定・リスク制限・丸め処理（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づく発注株数算出、単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的見積りおよび残差処理を実装。
- ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout への StreamHandler（標準出力）と日次ローテーション（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成と失敗時のフォールバックを実装。
  - プロセス優先度ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）や CPU affinity を設定する機能を提供。psutil を利用し、失敗時は警告でスキップ。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - レポートは system_status / trade_logs / risk_logs から稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計し、閾値に基づく PASS/FAIL 判定を出力。
    - コマンドライン引数 --from / --to / --db に対応。デフォルト DB は data/paper_trading.db。
- リサーチ
  - ファクター計算モジュールの骨組みを追加（src/kabusys/research/factor_research.py）。
    - モメンタム指標（1M/3M/6M リターン、MA200 乖離）などの計算ロジックの開始点を実装（DuckDB 接続を想定）。

### Changed
- 設定の自動読み込みポリシーを定義
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。既存の OS 環境変数はデフォルトで保護（protected）され、自動ロードで上書きされないように実装。
- ログ出力設計
  - StreamHandler を stdout に向けることで、cron / Task Scheduler 等からのリダイレクト運用を考慮。

### Fixed
- .env パーサでのエッジケース対応
  - クォート内のバックスラッシュエスケープや、クォート無しでのコメント扱い（'#' の前が空白・タブの場合のみコメントと解釈）に対応し、より堅牢にエントリを読み込めるようにしました。

### Deprecated
- なし

### Removed
- なし

### Security
- 機密情報の取り扱い（.env の secret フィールド、config_setup によるマスク表示）を意識した実装を行っていますが、.env は決してリポジトリにコミットしないことを README 等で明記してください。

---

備考:
- 実装済みの各モジュールは運用中の環境（development / paper_trading / live）に合わせて挙動が切り替わります。特に paper_trading の DB 分離、MONITOR_POLL_INTERVAL の上書き、KILL_FLAG_CLEAR_ON_START の設定などは運用時に注意して設定してください。
- 一部モジュール（例えば research の一部関数）は今後の拡張やテストで更に完成度を高める予定です（コード内 TODO コメントあり）。