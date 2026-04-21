CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
（本ファイルはコードから推測して作成した推定の変更履歴です。）

Unreleased
----------

### Added
- 設計上の TODO / 今後の改善候補を追加:
  - position_sizing: 銘柄ごとの lot_size マップ対応（現在は全銘柄共通の単元数を想定）。
  - position_sizing: 価格欠損時のフォールバック（前日終値や取得原価など）の導入検討。
  - research.calc_momentum: 実装未完（ファイル末尾でトランケートされているため残作業あり）。
  - ログ出力や DB 作成失敗時のより詳細なフォールバック処理や通知の改善。

### Changed
- なし（Unreleased は将来の変更予定を示す）

### Fixed
- なし

0.1.0 - 2026-04-21
------------------

初回リリース。以下の主要機能・モジュールを実装。

### Added
- コア設定・環境管理
  - Settings クラスによる環境変数ベースの設定取得機能を実装。
  - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 環境変数の厳密チェック（valid 値チェック、必須変数チェック）。
  - config_setup: 対話式 .env 作成ウィザードを追加。
  - validate_config: .env および config/*.yaml の起動前検証 CLI を追加（--strict オプションあり）。

- 実行 / 監視ランナー
  - run_execution: ExecutionEngine 起動スクリプトを実装。
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager (RiskConfig を含む), Reconciler, ExecutionEngine の組み立て。
    - 停止フラグ (data/stop_requested.flag) と PID ファイルの取り扱い。
    - プロセス優先度を起動直後に "high" に設定。
  - run_monitoring: SystemMonitor ポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き対応（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用。
    - SystemMonitor の check_once を定期実行し、例外はログに記録してループ継続。

- モニタリング / DB
  - sqlite3 / duckdb 接続サポートと init_monitoring_db 呼び出し（監視テーブルの初期化・冪等性確保）。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコアソートと上位 N 選定。
    - calc_equal_weights, calc_score_weights: 等金額配分・スコア加重配分（スコアが全て 0 の場合は等金額にフォールバック）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限に基づく候補除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知値はフォールバック）。
  - position_sizing:
    - calc_position_sizes: 発注株数決定ロジック（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株丸め、1銘柄上限・aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した保守的見積り。
    - スケーリング時の残差配分ロジック（fractional remainder を評価し lot 単位で追加配分）。

- ユーティリティ
  - logging_setup:
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを提供。
    - LOG_LEVEL / LOG_DIR の環境変数による上書きと引数による優先解決。
    - ログディレクトリ作成失敗時はファイル出力を無効化してコンソールのみで継続。
  - process_priority:
    - Windows / POSIX の差異を吸収してプロセス優先度（nice / Windows priority class）を設定。
    - CPU affinity 設定ユーティリティ（最初の N コアに固定）。
    - psutil の権限エラー等を許容して安全にフォールバック。
  - 環境変数パーサ:
    - .env ファイル行のパースロジックを実装（export プレフィックス、シングル/ダブルクオート、バックスラッシュエスケープ、インラインコメント解析等に対応）。

- 解析 / リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨子（モメンタム／MA／ATR 等を計画）。DuckDB 接続で prices_daily / raw_financials を参照する設計。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 向け検証レポート生成 CLI を実装。
    - 稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均 / 最大 / P95）を算出して判定 (PASS/FAIL)。
    - P95 計算、自動日付フィルタ、DB パスのオーバーライド対応（環境変数 / --db）。

- パッケージ情報
  - __version__ を "0.1.0" として設定。
  - パッケージの公開 API を __all__ で整理（portfolio 等のエクスポート）。

### Changed
- なし（初回リリースのため過去バージョンからの変更は無し）

### Fixed
- なし（初回リリース）

### Known issues / Notes
- research.calc_momentum の実装が途中で終了している（ファイル末尾が切れている）。完全実装が必要。
- position_sizing の TODO: 銘柄別 lot_size と価格フォールバックの改善ポイントあり（既にソース内にコメントと TODO を記載）。
- config/*.yaml の検証は PyYAML 未インストール時にスキップされる（validate_config が警告を出す）。
- .env 自動ロードはプロジェクトルートが特定できない場合はスキップされる設計。
- run_monitoring は monitoring 用 DB に本番 sqlite_path を使用するため、意図的に環境分離されない点に注意。

Security
--------
- なし（本リリースで特筆すべきセキュリティ修正は無し）

Acknowledgements / Notes
------------------------
- 本 CHANGELOG はコード内容から推測して作成したものであり、実際のリリースノートや変更履歴と差異がある可能性があります。必要に応じて修正・追記してください。