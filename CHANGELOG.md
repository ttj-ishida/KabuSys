# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」準拠です。  
リリース日はリポジトリ内のバージョン情報および現在日付に基づいています。

全体方針: 破壊的変更はメジャーアップデートでのみ行うこと。

## [0.1.0] - 2026-04-18

### Added
- 初回リリース: KabuSys の基本コンポーネントを追加。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 専用 SQLite (data/paper_trading.db) を使用し、本番 DB と完全に分離。  
    - BrokerClientFactory 経由でブローカークライアントを生成。ExecutionEngine をスレッドで実行し、data/stop_requested.flag による外部停止をサポート。PID ファイル書き込み機能あり（data/execution.pid）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視用 DB の初期化(init_monitoring_db)と duckdb 接続を行う。停止フラグでループ終了。
- 設定管理
  - src/kabusys/config.py: 環境変数/`.env` ロードと Settings クラスを追加。  
    - プロジェクトルートの自動検出（.git または pyproject.toml を探索）。  
    - 自動 .env ロード（`.env` → `.env.local`、OS 環境変数は保護）。自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` を提供。  
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメント（一定条件）に対応。  
    - 各種設定プロパティ（J-Quants / kabu API / DuckDB/SQLite パス / PAPER_FILL_MODE 等）を提供。`PAPER_FILL_MODE` の妥当性チェックを実施。
- 設定操作ツール
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新する CLI を追加（デフォルト値、シークレット表示、検証済み選択肢など）。`.env` 書式テンプレートを出力。
  - validate_config.py: 起動前の設定チェック CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース（PyYAML がある場合）を検査。`--strict` オプションで警告を FAIL 扱いにできる。
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを追加。  
    - stdout への StreamHandler（cron/タスクとの相性を考慮）と、日次ローテーションする TimedRotatingFileHandler（デフォルト logs/<app_name>.log、30日分保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順を実装。ログディレクトリ作成失敗時はファイル出力をスキップして標準出力のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX の差分を吸収して `set_process_priority("high"|"normal"|"low")` を提供。`set_cpu_affinity(n)` で最初の N コアにピン留め可能。権限不足などの場合は警告を出して安全にスキップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコア全0 の場合は等配分にフォールバック。
  - portfolio/risk_adjustment.py: セクター集中上限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知のセクター／レジームは安全にフォールバック。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装。  
    - allocation_method に応じた計算（risk_based / equal / score）を実装。単元（lot_size）考慮、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer による保守的見積り、残差の補正ロジックを実装。
- リサーチ
  - research/factor_research.py: ファクター計算モジュールの骨子を追加（モメンタム・ATR・流動性等を想定）。DuckDB 接続を受け取り prices_daily / raw_financials を参照して定量ファクターを計算する設計。calc_momentum の定数・インターフェイスを定義（実装は継続）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。  
    - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。閾値（稼働率 99% 等）やコマンドライン引数（--from / --to / --db）を提供。欠損テーブルがある場合は安全に N/A を返す。
- パッケージ情報
  - src/kabusys/__init__.py にバージョン `__version__ = "0.1.0"` を追加。

### Changed
- ログの設計方針: コンソール出力は stdout を利用する（stderr ではない）。日次ローテーション・30日保持を採用。
- .env の読み込みルール: OS 環境変数を保護しつつ `.env` と `.env.local` を適切な優先順位でロードする実装を導入。`.env.local` は OS 環境変数以外を上書きできる。

### Fixed / Improved
- .env パースの堅牢化:
  - export プレフィックス、引用符（'"/）、バックスラッシュエスケープ、インラインコメントの取り扱いを実装し、より現実的な .env 書式に対応。
- DB/ファイルパス周りの事前警告:
  - validate_config にて DB パスの親ディレクトリ存在チェックや config/*.yaml の存在チェックを行い、起動時のエラーを早期に検出可能にした。
- 安全設計:
  - run_monitoring は監視用初期化を確実に行う（init_monitoring_db 呼び出し）。run_execution は停止フラグを検出すると起動をキャンセル/停止する仕組みを導入。
- 例外・権限関連の安全なフォールバック:
  - process_priority / set_cpu_affinity / logging のファイルハンドラ作成などで権限不足や未対応環境が発生した場合に警告を出して処理をスキップするよう改善。

### Notes / その他
- PAPER_FILL_MODE の有効値は "instant" | "partial" | "never" | "reject"。不正値は ValueError を送出して明示的にエラー化。
- run_monitoring はコメント（ドキュメント）どおり監視用 DB に本番 sqlite_path を利用する（KABUSYS_ENV にかかわらず）。
- research/factor_research.py は設計・定数および calc_momentum のインターフェイスを含む骨子を追加しているが、実装の続き（完全な SQL/計算ロジック）は今後の開発予定。
- config.validate_config は PyYAML 未インストール時に YAML 検証をスキップし、警告を出力する。

### Removed
- なし（初回リリース）

---

今後の予定（参考）
- research モジュールの完全実装（ファクター計算の SQL 最適化と正規化ユーティリティ連携）
- ExecutionEngine / Broker クライアントの追加テストとモック整備
- config の型注釈やドキュメント整備、CI での validate_config 自動実行

（以上）