# CHANGELOG

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。新しいリリースは上部に追記してください。

## [Unreleased]

### 注意 / 既知の制約
- risk_adjustment.apply_sector_cap の価格欠損時の扱い（price が 0.0 の場合にエクスポージャーが過少見積りされる）に関する TODO が残っています。将来的に前日終値や取得原価でのフォールバック実装を検討してください。
- position_sizing の将来的拡張として、銘柄ごとの単元（lot_size）を stocks マスタ等から受け取る設計変更がコメントに示されています。
- research/factor_research.calc_momentum がファイル途中で未完結の箇所が存在している（実装継続が必要）ことがコード中に見られます。

---

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本アーキテクチャと実行スクリプトを追加
  - run_execution.py: ExecutionEngine 起動用スクリプト（スレッド実行 / 停止フラグ検知 / PID ファイル管理）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL 環境変数で間隔指定）。
- 設定管理周り
  - config.py: .env 自動読み込み（.env / .env.local、OS 環境変数優先）、.env パースロジック、Settings クラス（各種環境変数のラッパー）。
  - config_setup.py: 対話式 .env 作成・更新ウィザード（.env の読み書き・入力プロンプト、シークレットマスク表示）。
  - validate_config.py: 起動前の設定検証 CLI（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検査、DB パス・config/*.yaml の存在確認、--strict モード）。
- 実行・発注関連
  - execution/*: BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせた ExecutionEngine 起動フロー（paper_trading 時には paper 用 SQLite を使用して本番 DB と分離）。
  - 実行時の安全ガード: data/stop_requested.flag、データベース分離（paper_trading 用 DB）、kill flag 設定オプション（KILL_FLAG_CLEAR_ON_START）。
- 監視（Monitoring）
  - monitoring.monitoring_db.init_monitoring_db を用いた監視テーブル初期化。
  - run_monitoring が sqlite3 と duckdb の接続を初期化して SystemMonitor に渡す実装。
- ポートフォリオ構築（Portfolio）
  - portfolio/portfolio_builder.py: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア配分（calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元丸め、aggregate cap によるスケールダウンと小数端数処理（lot 単位での再割当ロジック）。
  - portfolio パッケージのエクスポート実装（__init__）。
- 研究用モジュール（Research）
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子（モメンタム、MA200乖離、ATR、流動性等の計算設計と定数定義。calc_momentum 実装開始）。
- ユーティリティ
  - utils/logging_setup.py: 共通ロギング設定ユーティリティ（stdout StreamHandler + 日次ローテーション FileHandler、ログディレクトリ自動作成、LOG_LEVEL/LOG_DIR の解決順）。
  - utils/process_priority.py: Windows/Linux/macOS 向けにプロセス優先度（nice / HIGH_PRIORITY_CLASS）と CPU affinity 設定ラッパー（set_process_priority, set_cpu_affinity）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト（期間指定可、稼働率 / 注文成功率 / 送信率 / レイテンシ（avg/max/P95）を算出し PASS/FAIL 判定）。
- パッケージメタ
  - __init__.py: パッケージ名、初回バージョン __version__ = "0.1.0"。

### Changed
- （初回リリースのため特記事項なし）

### Fixed
- .env パーサにおいて以下の堅牢化を実施
  - export プレフィックス対応
  - シングル・ダブルクォート内のバックスラッシュエスケープ処理対応
  - クォートなしの行でのインラインコメント（#）の取り扱い（直前がスペース/タブのときのみコメントと扱う）
- logging_setup: ログディレクトリ作成失敗時にファイル出力をスキップして stdout のみで継続するフォールバックを実装（起動時の堅牢性向上）。

### Security
- 秘匿情報（J-Quants トークン、kabu API パスワード等）は Settings 経由で明示的に取得する設計とし、config_setup でシークレットはマスク表示。`.env` の Git コミット防止コメントを README に含める旨を .env 書き出しテンプレートに記載。

---

セマンティックバージョニング（0.x）は開発初期段階のため、互換性の保証は限定的です。将来的に public API（関数署名・CLI 挙動・設定キー等）を確定した際にメジャーリリースポリシーを明示します。