# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

現在のバージョン: 0.1.0

## [Unreleased]

- なし

## [0.1.0] - 2026-04-19

### Added
- 初期リリース。KabuSys 自動売買フレームワークの基本コンポーネントを実装。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading の場合は本番 DB とは分離された paper_trading 用 SQLite を使用する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を参照する旨を明記。
- 環境設定・検証関連 CLI
  - config_setup.py: 対話式ウィザードで `.env` を作成・更新するユーティリティを追加。secret 項目はマスク表示、デフォルト値・選択肢対応。
  - validate_config.py: `.env` と config/*.yaml の事前検証ツールを追加。必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML がない場合はスキップ）などを実施。--strict オプションで警告を FAIL 扱いにできる。
- 設定管理
  - config.py: 自動でプロジェクトルートを探索して `.env` / `.env.local` を読み込む仕組みを追加（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。.env パースは export プレフィックス、クォート、エスケープ、インラインコメントなどに対応。Settings クラスを通して型変換・妥当性チェック付きで環境変数へアクセス可能に。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler を設定する共通ユーティリティを追加。既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックなどを実装。
  - utils/process_priority.py: Windows / POSIX の差を吸収して現在プロセスの優先度（high/normal/low）や CPU affinity を設定するユーティリティを追加。権限不足や未対応 OS 時は安全にスキップする。
- ポートフォリオ構築モジュール（純関数）
  - portfolio/portfolio_builder.py: シグナル候補選定（スコア順）、等配分・スコア加重の重み計算を実装。全スコアが 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）とマーケットレジームに応じた投下資金乗数（calc_regime_multiplier）を実装。未知のレジームはフォールバックで 1.0 を返し警告を出す。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数決定ロジックを実装。単元株丸め、per-position 上限（max_position_pct）、aggregate cap によるスケーリング、cost_buffer を用いた保守的なコスト見積り、残差処理による追加配分処理などを備える。
- Execution 周辺コンポーネント統合（起動スクリプトから組み立てられる）
  - BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler、ExecutionEngine の組み立てと起動フロー。RiskConfig のデフォルト値（例: max_position_pct=0.20 等）を設定し、初期ポートフォリオ値をブローカーから取得する仕組みを導入。
- 監視・モニタリング
  - monitoring 側の DB 初期化（init_monitoring_db）呼び出しを起動処理に追加し、監視テーブルの存在を冪等に保証。
  - 停止制御フラグ（data/stop_requested.flag）および PID ファイルの取り扱いを導入。
- ツール
  - tools/paper_verification_report.py: ペーパートレード用 DB から期間指定で検証レポートを生成する CLI を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、閾値に基づいて PASS/FAIL を判定する機能を実装。P95 計算や欠損データハンドリングを含む。
- research
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を用いたファクター計算モジュール（モメンタム等）を追加（設計・初期実装）。将来的なファクター集計処理の基盤を含む。

### Changed
- logging の出力先は stdout をデフォルトに（cron/Task Scheduler との互換性向上のため）。ログディレクトリ作成失敗時はファイル出力を無効化してコンソールログのみで継続。
- .env 自動読み込みの優先順位を明確化（OS 環境 > .env.local > .env）。OS 環境変数は保護され、.env.local で上書き可能。
- run_execution.py の DB 接続は環境により paper_trading 用 DB と本番 DB を切り替えるように変更（分離を明確化）。

### Fixed
- .env パーサーの堅牢化: export プレフィックス、クォート・バックスラッシュエスケープ、インラインコメントの扱いなどに対応し、誤ったパースによる設定ミスを軽減。
- process_priority / set_cpu_affinity: 非対応 OS や権限不足時に例外でプロセスを停止させないように例外を捕捉して警告にフォールバック。
- ポートフォリオの重み計算 (calc_score_weights): 全スコアが 0 の場合に適切に等金額配分にフォールバックして負の/ゼロ除算を回避。

### Security
- .env を生成する際にファイルに敏感情報が書かれる旨を README/コメントで注意喚起（.env を絶対に Git にコミットしない旨をテンプレートに記載）。

### Notes / Implementation details
- バージョンはパッケージルートの __version__ に合わせて 0.1.0 を設定。
- 多くの機能は外部依存（psutil, duckdb, PyYAML）を利用するが、依存が満たされない場合でも実行可能な範囲でフォールバック（例: YAML 未インストール時はパース検査をスキップ、ログディレクトリ作成失敗時はコンソールログのみ）する実装方針を採用。
- 一部モジュール（research/factor_research.py 等）は計算ロジックの骨格を提供しており、今後の拡張でファクター実装を追加予定。

---

（今後のリリースでは、機能追加・微調整・バグ修正・後方互換性に関する注意を明記します。）