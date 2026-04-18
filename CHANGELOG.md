# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠し、Semantic Versioning を想定します。

## [Unreleased]

### Added
- （今後のリリース用のプレースホルダ）

## [0.1.0] - 2026-04-18

初回リリース。プロジェクトのコア機能とユーティリティ群を導入。

### Added
- 実行用スクリプトを追加
  - run_execution.py: ExecutionEngine の起動スクリプト。プロセス優先度の設定、SQLite / DuckDB 接続、Broker クライアント生成、ExecutionEngine の起動・停止制御（停止フラグの検知）を提供。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き、停止フラグ検知、例外ハンドリングを実装。

- 設定関連
  - config.py: .env 自動読み込み（プロジェクトルート検出）、環境変数パース機能、Settings クラスを追加。J-Quants / kabuAPI / DB パス / Paper Trading の挙動切替や閾値等をプロパティとして提供。
    - .env の自動ロードは OS 環境変数を保護しつつ `.env` と `.env.local` を読み込む。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
    - .env 行パーサは `export ` プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ、インラインコメント処理に対応。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を追加。機密値のマスク表示、既存 .env の読み込み、保存前確認を実装。
  - validate_config.py: 起動前に環境変数と config/*.yaml を検証する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリチェック、PyYAML 未インストール時のフォールバック、`--strict` モードを実装。

- 監視 / Paper Trading
  - monitoring: 監視用 DB 初期化を保証する init_monitoring_db 呼び出しを導入（冪等）。
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・API レイテンシ（平均・最大・P95）などを集計し PASS/FAIL を判定。期間フィルタ、DB パス指定オプションをサポート。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・タイブレークでソートして上位 N を選定。
    - calc_equal_weights / calc_score_weights: 等配分・スコア加重の重み計算。全スコアが 0 の場合は等配分へフォールバックし警告を出力。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限を適用し、既存エクスポージャが閾値を超えるセクターの新規候補を除外。売却予定銘柄をエクスポージャ計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear 等）を提供。未知レジームはフォールバックして警告。
  - portfolio/position_sizing.py
    - calc_position_sizes: 等分・スコア・リスクベースの発注株数決定ロジックを実装。単元株（lot_size）丸め、1銘柄上限、aggregate cap によるスケールダウン、残余キャッシュによる端数配分処理を実装。価格欠損時のスキップやログ出力を含む。

- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一設定ユーティリティを追加。stdout 出力用 StreamHandler と日次ローテーションの TimedRotatingFileHandler（デフォルト logs/、30日保持）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（Windows の priority class / POSIX の nice 値）と CPU affinity 設定ユーティリティを追加。クロスプラットフォーム対応、権限不足や未対応環境での警告ログ出力を実装。

- research/factor_research.py: DuckDB を使ったファクター計算モジュール（モメンタム等）の骨組みを追加（関数定義と定数を含む）。（※実装途中の箇所あり）

- パッケージ情報
  - __init__.py にてバージョンを 0.1.0 として定義。

### Changed
- run_execution と run_monitoring の挙動で DB の扱いを明示
  - run_execution: KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用して本番 DB と分離（paper trading 用 DB は data/paper_trading.db がデフォルト）。
  - run_monitoring: 環境にかかわらず監視は本番 sqlite_path を使用する旨が明確化。

- ログ設定の挙動
  - setup_logging は既存ハンドラの flush/close/削除を行い二重設定を防止するように変更（統一的なログ管理のため）。

- .env 読み込みポリシー
  - OS 環境変数を保護する protected セットを導入し、.env.local の上書きは許可するが OS 環境変数は上書きしないように実装。

### Fixed
- 環境変数・入力パースの堅牢化
  - _parse_env_line においてクォートとエスケープ、export プレフィックス、インラインコメントの処理を強化し、より多様な .env フォーマットに対応。

- モニタリングのポーリング間隔検証
  - MONITOR_POLL_INTERVAL の値が不正（非数値や 0 以下）な場合にデフォルト（60 秒）へフォールバックし、警告ログを出す実装を追加。time.sleep に無効値が渡らないよう保護。

- プロセス優先度設定の例外処理
  - set_process_priority / set_cpu_affinity で権限不足や非対応プラットフォームの例外を捕捉し警告を出力するようにして起動の堅牢性を向上。

### Security
- 機密情報の扱い
  - config_setup の対話でシークレット項目をマスク表示することで、対話ログに機密が表示されないよう配慮。

### Notes / Known limitations
- research/factor_research.py はモジュール骨格と定数が存在するが、一部関数（ファクター計算本体）はまだ未完（ソースの末尾で途中終了している箇所あり）。今後の実装が必要。
- position_sizing の価格欠損時のフォールバックは TODO コメントが残っており、前日終値等の利用拡張が検討事項として存在する。
- ログファイル作成に失敗した場合はコンソールのみで動作するが、その際の詳細な挙動テストが推奨される。

---

保持する慣例:
- 重要な後方互換破壊やセキュリティ修正は各バージョンで明示します。