# Changelog

すべての変更は "Keep a Changelog" の形式に準拠して記載しています。  
慣例に従い重要な変更点をカテゴリ別（Added / Changed / Fixed / Removed / Security / Notes）でまとめています。

## [Unreleased]

## [0.1.0] - 2026-04-18

初回リリース — KabuSys コードベースの最初の実装を公開します。以下はこのリリースで追加された主要な機能と改善点の概要です。

### Added
- パッケージ基盤
  - kabusys パッケージ本体（バージョン 0.1.0 を package レベルで設定）。
- 実行／監視エントリポイント
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は Paper Trading 用の専用 SQLite（data/paper_trading.db をデフォルト）を使用することにより本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動ロジックを実装。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた起動・停止管理。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視ロジックは環境にかかわらず本番用の sqlite_path を参照して監視情報を記録。
    - 停止フラグ検知、例外ハンドリング、KeyboardInterrupt 対応を実装。
- 設定管理
  - config.py: Settings クラスを実装（環境変数読み取り・バリデーション）。
    - 自動 .env 読み込み（プロジェクトルートの検出による .env / .env.local の読み込み、OS 環境変数を保護）。
    - 複数のプロパティ（J-Quants トークン、kabu API、DB パス、paper_trading 用パス、監視閾値、KABUSYS_ENV/LOG_LEVEL 等）を提供。
    - PAPER_FILL_MODE の検証ロジックを追加（有効値のチェック）。
  - config_setup.py: 対話式ウィザードを実装して .env の初期作成・更新を支援。
    - シークレット項目のマスク・既存値の再利用・デフォルト値の提示・確認保存機能。
- 設定検証ツール
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、`--strict` オプションで警告をエラー扱いにする機能。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading 用 SQLite を解析して検証レポート（稼働率、注文成功率、送信率、レイテンシ等）を出力するスクリプトを追加。
    - CLI 引数で期間（--from / --to）や DB パス（--db）を指定可能。
    - P95 計算、閾値による PASS/FAIL 判定を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: シグナルのスコア順選別。
    - calc_equal_weights / calc_score_weights: 重み付けロジック（スコア合計が 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を防ぐフィルタリングを実装（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下倍率を実装（bull/neutral/bear とフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算、単元株（lot_size）揃え、per-stock/max_utilization/aggregate cap の処理、コストバッファを考慮したスケーリング。
- 研究モジュール（計算骨格）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格（モメンタム等の計算方針と一部実装）。
- ユーティリティ
  - utils/logging_setup.py: 統一ロギング設定ユーティリティ（stdout StreamHandler + 日次ローテーションの TimedRotatingFileHandler、LOG_DIR 解決、既存ハンドラのクリア等）。
  - utils/process_priority.py: psutil を利用したクロスプラットフォームのプロセス優先度設定と CPU affinity 設定関数を実装（Windows / POSIX の差分吸収）。
- その他
  - tools パッケージ初期化。
  - パッケージの __all__ 設定やエクスポートの整理。

### Changed
- .env 自動読み込みの優先度と保護
  - OS 環境変数を保護しつつ、プロジェクトルートから .env/.env.local を自動で読み込む挙動を採用（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可）。
- DB ハンドリング
  - Monitoring 用スクリプトは環境にかかわらず `Settings.sqlite_path`（本番監視 DB）を使用する設計とした一方で、Execution は `is_paper` 判定で paper 用 DB を使用して本番 DB と分離するように設計。
- ログ出力
  - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続する堅牢化。

### Fixed
- .env パーサの強化
  - 引用符付き値（シングル/ダブル）のエスケープ処理、`export KEY=...` 形式のサポート、インラインコメントの扱いなどを実装し、既存の .env 読み込みの堅牢性を向上。
- validate_config の YAML 検証
  - PyYAML がない場合にスキップし警告を出すようにして、環境依存の ImportError に対して分かりやすい挙動を提供。
- Execution / Monitoring の例外処理強化
  - monitor.check_once() 等で発生した例外をログに残して単一ポーリングで監視が停止しないよう保護。

### Notes / Known limitations / TODO
- position_sizing.calc_position_sizes:
  - price の欠損（0.0）がある場合の扱いに TODO コメントあり（将来的に前日終値や取得原価でフォールバックする想定）。
  - 単元株（lot_size）を現状は全銘柄共通で 100 前提としているが、将来的には銘柄毎の lot_size をサポートする予定。
- research/factor_research.py:
  - ファクター計算モジュールは設計・一部実装の段階。完全実装は今後のリリースで継続予定。
- Paper Trading と本番 DB の分離は設計上考慮済みだが、運用時は .env の設定（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）を再確認してください。
- process_priority / cpu_affinity の設定は環境（権限・OS）に依存し、失敗した場合はログ警告を出してスキップする仕様です。

### Removed
- なし

### Security
- なし

---

今後のリリースでは以下のような改善を予定しています（例）:
- research モジュールの完全実装（各ファクターの SQL/数値処理）。
- strategy / execution のユニットテスト拡充と CI 統合。
- 単元銘柄別 lot_size のサポート、価格フォールバックロジックの導入。
- モニタリング・アラート（LINE 連携等）の強化。

フィードバック・バグ報告や提案があればお知らせください。